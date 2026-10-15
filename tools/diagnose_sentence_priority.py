#!/usr/bin/env python3
"""Observe actual final-pool scores and quantify first-choice pinning on known cases.

Archive-only observer; no production change, training or fresh-test claim.
"""
import argparse
import base64
from collections import defaultdict
import gzip
import io
import json
from pathlib import Path
import struct
import subprocess
import tarfile
import tempfile
import shutil
from train_phrase_model import ROOT
from prepare_tatoeba_corpus import digest
from sentence_features import features

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class PriorityObserve {
 static Path assets;
 static Reader a(String n)throws Exception{return Files.newBufferedReader(assets.resolve(n));}
 public static void main(String[] args)throws Exception {
  assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
  QuickDecoder q=new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),
   OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
   PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),a("hk_chat_phrases.tsv"),
   CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
   CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))),
   SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))),
   PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))));
  int count=0;
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    if(line.isEmpty()||line.startsWith("#"))continue;String[] f=line.split("\t",-1);
    if(f.length!=4)throw new IllegalArgumentException("Named calibration rows required");
    QuickDecoder.observedRaw.clear();QuickDecoder.observedAdjusted.clear();QuickDecoder.observedOriginal="";
    List<String> values=q.decode(f[2],(c,w)->0,f[1]);List<String> raw=new ArrayList<>(),adj=new ArrayList<>(),sup=new ArrayList<>();
    // One-candidate pools skip final reranking in production; observe their
    // actual raw score, with no invented correction or extra candidate.
    if(values.size()==1 && QuickDecoder.observedAdjusted.isEmpty()) {
     QuickDecoder.observedOriginal=values.get(0);
     QuickDecoder.observedAdjusted.put(values.get(0),QuickDecoder.observedRaw.get(values.get(0)));
    }
    for(String text:values) {
     if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError(text);
     raw.add(Double.toHexString(QuickDecoder.observedRaw.get(text)));
     adj.add(Double.toHexString(QuickDecoder.observedAdjusted.get(text)));
     sup.add(Double.toHexString(q.observedSupport(f[1],text)));
    }
    out.write(line+"\t"+QuickDecoder.observedOriginal+"\t"+(values.indexOf(f[3])+1)+"\t"+String.join("|",values)+"\t"+String.join("|",raw)+"\t"+String.join("|",adj)+"\t"+String.join("|",sup)+"\n");
    if(++count%100==0)System.out.println("observed="+count);
   }
  }
 }
}
'''

def observe(cases,output,revision='a65f43d',working_tree=False,include_relation=False,relation_asset=None):
    archive=subprocess.check_output(['git','archive',revision,'app/src/main/java','app/src/main/assets'],cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='priority-observe-') as directory:
        work=Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as data:data.extractall(work,filter='data')
        if working_tree:
            names=subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'app/src/main/java','app/src/main/assets'],cwd=ROOT,text=True).splitlines()
            for name in names:shutil.copyfile(ROOT/name,work/name)
        if relation_asset is not None:
            if not include_relation:raise ValueError('An explicit relation asset requires include_relation')
            shutil.copyfile(relation_asset,work/'app/src/main/assets/relation_ranker.b64')
        java=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java';text=java.read_text()
        hooks={
            '    private static final int BEAM = 48;':'''    static final Map<String,Double> observedRaw=new HashMap<>(),observedAdjusted=new HashMap<>();
    static String observedOriginal="";
    double observedSupport(String context,String text){return structuralSupport(context,text);}
    private static final int BEAM = 48;''',
            '        List<Path> completed = pruneFinal(lattice.get(code.length()));':'        List<Path> completed = pruneFinal(lattice.get(code.length()));\n        for(Path path:completed)observedRaw.merge(path.text,path.score,Math::max);',
            '            String original = result.get(0);':'            observedAdjusted.putAll(scores);\n            String original = result.get(0);observedOriginal=original;',
            '        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));':'        // Observe the same pool before its display20 cutoff.'}
        for old,new in hooks.items():
            if text.count(old)!=1:raise ValueError('Observer structure changed')
            text=text.replace(old,new)
        driver_text=DRIVER
        if include_relation:
            needle='PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))));'
            replacement='PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))),PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))));'
            if driver_text.count(needle)!=1:raise ValueError('Relation observer constructor changed')
            driver_text=driver_text.replace(needle,replacement)
            needle='            result.sort(order);'
            if text.count(needle)!=1:raise ValueError('Relation observer score hook changed')
            text=text.replace(needle,needle+'\n            observedAdjusted.clear();observedAdjusted.putAll(scores);')
        java.write_text(text);driver=work/'PriorityObserve.java';driver.write_text(driver_text)
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(driver)],check=True)
        output.parent.mkdir(parents=True,exist_ok=True);complete=output.with_suffix('.pending.tsv').resolve()
        subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.PriorityObserve',str(work/'app/src/main/assets'),str(cases.resolve()),str(complete)],check=True)
        complete.replace(output)

def summarize(scored,expected,output):
    rows=[];groups=defaultdict(list);pins=defaultdict(int)
    old=expected.read_text().splitlines()
    for index,line in enumerate(scored.read_text().splitlines()):
        f=line.split('\t');source,context,code,gold,original=f[:5];values=f[6].split('|') if f[6] else []
        raw=[float.fromhex(s) for s in f[7].split('|')] if values else []
        adjusted=[float.fromhex(s) for s in f[8].split('|')] if values else []
        support=[float.fromhex(s) for s in f[9].split('|')] if values else []
        before=old[index].split('\t')
        if before[:4]!=f[:4] or before[5]!='|'.join(values[:20]):raise AssertionError('Observer changed actual candidate ordering')
        score=dict(zip(values,adjusted));evidence=dict(zip(values,support));name=source.split(':',1)[-1]
        unpinned=sorted(values,key=lambda v:-score[v]);rank=values.index(gold)+1 if gold in values else 0
        pin=bool(original and evidence[original]>0);pins[name]+=pin
        record={'source':source,'context':context,'code':code,'gold':gold,'rank':rank,'original':original,'pin':pin,
            'unpinned_rank':unpinned.index(gold)+1 if gold in unpinned else 0,'supports':evidence,'adjusted':score,'values':values}
        rows.append(record);groups[name].append(record)
    if len(rows)!=len(old):raise ValueError('Partial observer')
    def metrics(ranks):return dict(top1=sum(r==1 for r in ranks),top5=sum(0<r<=5 for r in ranks),top20=sum(0<r<=20 for r in ranks))
    baseline={n:metrics([r['rank'] for r in rs]) for n,rs in groups.items()}
    # Diagnosis only: unrestricted unpin can identify both saved and blocked first choices.
    unpinned={n:metrics([r['unpinned_rank'] for r in rs]) for n,rs in groups.items()}
    trials={}
    for support_margin in (.25,.5,1):
        for score_margin in (.25,.5,1):
            chosen={}
            for name,rs in groups.items():
                ranks=[]
                for r in rs:
                    values=r['values'];original=r['original'];head=original
                    if r['pin']:
                        eligible=[v for v in values if r['supports'][v]>=r['supports'][original]+support_margin
                            and r['adjusted'][v]>=r['adjusted'][original]+score_margin]
                        if eligible:head=max(eligible,key=lambda v:r['adjusted'][v])
                        rest=sorted((v for v in values if v!=head),key=lambda v:(v!=original,-r['adjusted'][v]))
                        order=[head]+rest
                    else:order=sorted(values,key=lambda v:-r['adjusted'][v])
                    ranks.append(order.index(r['gold'])+1 if r['gold'] in order else 0)
                chosen[name]=metrics(ranks)
            trials[f'support{support_margin:g}/score{score_margin:g}']=chosen
    report={'cases':len(rows),'verified_native_top20_lists':len(rows),'calibration_only':True,'baseline':baseline,'pinned_counts':dict(pins),
        'unrestricted_unpin':unpinned,'conservative_override_trials':trials,
        'first_choice_pin_blocks_gold':[dict(source=r['source'],gold=r['gold'],original=r['original']) for r in rows if r['pin'] and r['rank']!=1 and r['unpinned_rank']==1],
        'first_choice_pin_saves_gold':[dict(source=r['source'],gold=r['gold']) for r in rows if r['pin'] and r['rank']==1 and r['unpinned_rank']!=1],
        'scored_sha256':digest(scored),'production_change':False,'limits':'Previously inspected calibration data; no new accuracy claim. Gold labels only audit outcomes, never choose runtime candidates.'}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('first_choice_pin_blocks_gold','first_choice_pin_saves_gold')},ensure_ascii=False));return report

def relative_score_pilot(scored,output):
    """Use frozen model evidence and pools, with a bounded relative correction.

    This is a calibration simulation, not an adopted native runtime change.
    Labels audit the outcome only; every score uses the same raw winner reference.
    """
    asset=ROOT/'app/src/main/assets/sentence_ranker.b64'
    data=gzip.decompress(base64.b64decode(asset.read_bytes()))
    magic,count,schema,strength,limit,long_strength,long_limit=struct.unpack_from('>IIIffff',data)
    if magic!=0x53524b33 or schema!=3:raise ValueError('Expected frozen SRK3 asset')
    weights={};at=28
    for _ in range(count):
        size=struct.unpack_from('>H',data,at)[0];at+=2
        key=data[at:at+size].decode('utf-8');at+=size
        weights[key]=struct.unpack_from('>f',data,at)[0];at+=4
    if at!=len(data) or len(weights)!=count:raise ValueError('Invalid asset entries')
    clip=lambda value,bound:max(-bound,min(bound,value))
    groups=defaultdict(list);erased=comparisons=0;max_error=0;cache={}
    for index,line in enumerate(scored.read_text().splitlines()):
        f=line.split('\t');source,context,code,gold,original=f[:5]
        values=f[6].split('|') if f[6] else []
        raw=dict(zip(values,(float.fromhex(v) for v in f[7].split('|')))) if values else {}
        adjusted=dict(zip(values,(float.fromhex(v) for v in f[8].split('|')))) if values else {}
        support=dict(zip(values,(float.fromhex(v) for v in f[9].split('|')))) if values else {}
        short={};longer={}
        for text in values:
            key=context,text
            if key not in cache:
                fs=features(context,text,3)
                cache[key]=(sum(n*weights.get(k,0) for k,n in fs.items() if not k.startswith(('L|','J|'))),
                    sum(n*weights.get(k,0) for k,n in fs.items() if k.startswith(('L|','J|'))))
            short[text],longer[text]=cache[key]
            predicted=raw[text]+strength*clip(short[text],limit)+max(0,long_strength*clip(longer[text],long_limit)-.1) if len(values)>1 else raw[text]
            max_error=max(max_error,abs(predicted-adjusted[text]))
        if original and gold in short and gold!=original:
            comparisons+=1
            erased+=abs(clip(short[gold],limit)-clip(short[original],limit))<1e-9 and abs(short[gold]-short[original])>.25
        groups[source.split(':',1)[-1]].append(dict(gold=gold,original=original,values=values,
            raw=raw,short=short,longer=longer,pin=bool(original and support[original]>0)))
        if (index+1)%100==0:print(f'feature-scored={index+1}',flush=True)
    if max_error>1e-7:raise AssertionError(f'Python/native original score differs: {max_error}')
    def metrics(ranks):
        return dict(top1=sum(r==1 for r in ranks),top5=sum(0<r<=5 for r in ranks),
            top20=sum(0<r<=20 for r in ranks),mrr=sum(1/r for r in ranks if 0<r<=20)/len(ranks))
    baseline={n:metrics([r['values'].index(r['gold'])+1 if r['gold'] in r['values'] else 0 for r in rs]) for n,rs in groups.items()}
    trials={}
    for scale in (.25,.5,1):
        for retain_pin in (True,False):
            result={}
            for name,rs in groups.items():
                ranks=[]
                for r in rs:
                    ref=r['original']
                    scores={v:r['raw'][v]+scale*strength*clip(r['short'][v]-r['short'][ref],limit)
                        +max(0,long_strength*clip(r['longer'][v]-r['longer'][ref],long_limit)-.1)
                        for v in r['values']} if ref else {}
                    order=sorted(r['values'],key=lambda v:(0 if retain_pin and r['pin'] and v==ref else 1,-scores[v]))
                    ranks.append(order.index(r['gold'])+1 if r['gold'] in order else 0)
                result[name]=metrics(ranks)
            trials[f'scale{scale:g}/pin{retain_pin}']=result
    eligible=[k for k,t in trials.items() if all(t[n][m]>=baseline[n][m] for n in baseline for m in ('top1','top5','top20'))]
    report=dict(cases=sum(len(rs) for rs in groups.values()),calibration_only=True,baseline=baseline,
        trials=trials,eligible=eligible,native_original_max_score_error=max_error,
        gold_vs_raw_winner_comparisons=comparisons,short_difference_erased_by_individual_clipping=erased,
        model_sha256=digest(asset),scored_sha256=digest(scored),production_change=False,
        limits='Fixed existing weights and observed native pool; known calibration data only. No selection or independent gain claimed.')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cases',type=Path);p.add_argument('expected',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--reuse-observer',action='store_true',help='Reuse an existing complete observer TSV; its top20 parity is rechecked.')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);scored=a.output/'scored.tsv'
    if not a.reuse_observer:observe(a.cases,scored)
    summarize(scored,a.expected,a.output/'report.json')
    relative_score_pilot(scored,a.output/'relative-score-report.json')
