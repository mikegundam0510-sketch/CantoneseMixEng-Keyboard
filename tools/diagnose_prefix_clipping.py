#!/usr/bin/env python3
"""Training-only clipping audit and temporary native pair-difference experiment.

The800 already-opened examples are old regression data. This pilot uses known
calibration cases only; it does not establish unseen accuracy or ship a model.
"""
import argparse
import json
from pathlib import Path
import subprocess
from evaluate_daily_prefix import build,run,read_results
from prefix_features import features,encode
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

DATA=ROOT/'tools/data/daily_prefix'

def audit():
    weights=json.loads((DATA/'weights.json').read_text())
    report=dict(pairs=0,both_scores_clip=0,learned_difference_erased=0,
        positive_difference_over1_lost_at_quarter=0)
    for line in (DATA/'pairs.tsv').read_text().splitlines():
        f=line.split('\t');hints=f[8].split('|') if f[8] else []
        scores=[sum(weights.get(k,0)*v for k,v in features(f[1],text,hints).items()) for text in f[5:7]]
        p,q=scores;clip=lambda x:max(-2,min(2,x))
        report['pairs']+=1;report['both_scores_clip']+=abs(p)>2 and abs(q)>2
        report['learned_difference_erased']+=abs(clip(p)-clip(q))<1e-12 and abs(p-q)>.25
        report['positive_difference_over1_lost_at_quarter']+=p-q>1 and clip(p)-clip(q)<=1
    return report

def pilot(cases,before_path,output):
    selection=json.loads((DATA/'selection.json').read_text())
    for name,checksum in selection['runtime_source_sha256'].items():
        if digest(ROOT/f'app/src/main/java/hk/cantonesemixeng/keyboard/{name}.java')!=checksum:raise ValueError('Baseline source changed')
    output.mkdir(parents=True,exist_ok=True)
    protocol={'purpose':'Compare raw same-code difference before clipping, rather than difference of individually clipped scores.',
        'training_audit':audit(),'weights_sha256':digest(DATA/'weights.json'),'cases_sha256':digest(cases),
        'baseline_selection_sha256':digest(DATA/'selection.json'),'strength':.25,
        'range':'New pair correction remains bounded to+-0.5 at quarter strength; former difference can span+-1. No raw/final score, beam or personal-learning change.',
        'evaluation':'Previously inspected660 calibration cases only. Original800 is now regression material, not a fresh independent test.',
        'decision':'Do not change shipped source on this pilot alone. A promising safe result needs a new untouched source-family reserve and original regression/latency checks.'}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    before=read_results(cases,before_path);build(output/'trial',True)
    java=output/'trial/app/src/main/java/hk/cantonesemixeng/keyboard/PrefixRanker.java'
    source=java.read_text()
    start=source.index('    public double correction(');end=source.index('    /** Cheap positive endpoint',start)
    source=source[:start]+'''    double rawScore(String context,String text,List<String> hints) {
        double total=0;
        for(Map.Entry<String,Integer> e:features(context,text,hints).entrySet())total+=weights.getOrDefault(e.getKey(),0f)*e.getValue();
        return total;
    }
    public double correction(String context,String text,List<String> hints) {
        return strength*Math.max(-limit,Math.min(limit,rawScore(context,text,hints)));
    }
    double difference(String context,String text,List<String> hints,double reference) {
        if(strength==0)return 0;
        return strength*Math.max(-limit,Math.min(limit,rawScore(context,text,hints)-reference));
    }
'''+source[end:];java.write_text(source)
    quick=java.with_name('QuickDecoder.java');source=quick.read_text()
    substitutions={'double reference=prefixRanker.correction(context,boundary.text,hints);':'double reference=prefixRanker.rawScore(context,boundary.text,hints);',
        'double evidence=prefixRanker.correction(context,p.text,hints)-reference;':'double evidence=prefixRanker.difference(context,p.text,hints,reference);'}
    for old,new in substitutions.items():
        if source.count(old)!=1:raise ValueError('Experiment hook changed')
        source=source.replace(old,new)
    quick.write_text(source)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(output/'trial/app/src/main/java'),'-d',str(output/'trial/classes'),str(output/'trial/tools/RankingEvaluation.java')],check=True)
    weights=json.loads((DATA/'weights.json').read_text());(output/'trial/app/src/main/assets/prefix_ranker.b64').write_bytes(encode(weights,.25))
    after=run(output/'trial',cases,output/'trial.tsv')
    failures=[name for name in before if any(after[name][k]<before[name][k] for k in ('top1','top5'))]
    report={'protocol':protocol,'before':before,'after':after,'calibration_failures':failures,
        'production_source_changed':False,'source_sha256':{p.name:digest(p) for p in (java,quick)},
        'candidate_input_codes_checked_by_native_decoder':True}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cases',type=Path);p.add_argument('before',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();pilot(a.cases,a.before,a.output)
