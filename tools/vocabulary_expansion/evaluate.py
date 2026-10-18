"""Ordinary expanded generation with the unchanged native tail scoring policy."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from shared import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write,verify
from expanded_model import load,Codec,decode
from report_prefix_retrieval import compare

CASES=ROOT/'tools/data/context_search/calibration1450.tsv'
UNSUPPLEMENTED=ROOT/'tools/reports/pinned-head-2026-10-17/calibration1450.tsv'
PARENT=ROOT/'tools/reports/tail-supplement-2026-10-18/native-calibration1450.tsv'

def native():
    stage=WORK/'native'
    if stage.exists():raise ValueError('Preserve existing native stage')
    stage.mkdir()
    blob=subprocess.check_output(['git','archive',BASELINE,'app/src/main/java','app/src/main/assets'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:archive.extractall(stage,filter='data')
    sources=[ROOT/'tools/tail_supplement/NativeEvaluation.java',ROOT/'tools/code_generator/NativeCodeCheck.java']
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-d',str(stage/'classes')]+list(map(str,sources)),check=True)
    result=subprocess.check_output(['java','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.NativeCodeCheck',
        str(stage/'app/src/main/assets'),str(WORK/'code-facts.tsv'),str(WORK/'legal-cases.tsv')],text=True)
    (REPORTS/'native-code-facts.txt').write_text(result);print(result.strip())

def freeze():
    verify();directory=DATA/'models'
    paths=[directory/'expanded.npz',directory/'report.json',DATA/'codes.json',DATA/'vocabulary.json']
    paths += sorted((WORK/'native/classes').rglob('*.class'))
    write(DATA/'inference-freeze.json',dict(sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        rule='Before ordinary predictions. Exactly the expanded provider; same original unsupplemented native pool and final2 policy. Compare to deployed d7dec75, not pre-supplement parent.'))

def check():
    verify()
    for name,wanted in json.loads((DATA/'inference-freeze.json').read_text())['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Frozen expanded inference changed: '+name)

def generate(part):
    check();v,chars=load(DATA/'models/expanded.npz')
    for a in v.values():a.setflags(write=False)
    codec=Codec(chars,json.loads((DATA/'codes.json').read_text()))
    rows=CASES.read_text().splitlines();pending=WORK/f'generated-{part}.pending.tsv';output=WORK/f'generated-{part}.tsv'
    if pending.exists() or output.exists():raise ValueError('Preserve ordinary predictions')
    with pending.open('x') as out:
        for n in range(part,len(rows),4):
            f=rows[n].split('\t');predicted=decode(v,codec,f[2],f[1],beam=24)
            for text,score in predicted:
                if codec.align(f[2],text) is None:raise ValueError('Inexact generated string')
            out.write('\t'.join(f[:3]+['|'.join(t for t,s in predicted)])+'\n')
            if ((n-part)//4+1)%100==0:print('expanded',part,'generated',(n-part)//4+1,flush=True)
    pending.rename(output)

def report():
    check();cases=CASES.read_text().splitlines();native=UNSUPPLEMENTED.read_text().splitlines();parent=PARENT.read_text().splitlines()
    rows=[None]*len(cases)
    for part in range(4):
        shard=(WORK/f'generated-{part}.tsv').read_text().splitlines()
        if len(shard)!=len(cases[part::4]):raise ValueError('Partial ordinary predictions')
        rows[part::4]=shard
    path=WORK/'inputs.tsv';allprops=WORK/'generated-code-check.tsv'
    with path.open('x') as out,allprops.open('x') as props:
        for case,old,new in zip(cases,native,rows):
            f,b,g=case.split('\t'),old.split('\t'),new.split('\t')
            if f!=b[:4] or f[:3]!=g[:3]:raise ValueError('Cached input identity differs')
            out.write('\t'.join(f[:3]+[b[5],g[3]])+'\n')
            for t in g[3].split('|') if g[3] else []:props.write('\t'.join((f[0],f[2],t))+'\n')
    stage=WORK/'native'
    result=subprocess.check_output(['java','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.NativeCodeCheck',
        str(stage/'app/src/main/assets'),str(WORK/'code-facts.tsv'),str(allprops)],text=True)
    (REPORTS/'all-generated-native-code.txt').write_text(result)
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.NativeEvaluation',
        str(stage/'app/src/main/assets'),str(path),str(WORK/'predictions.tsv'),str(REPORTS/'scores.tsv')],check=True)
    predictions=(WORK/'predictions.tsv').read_text().splitlines();output=REPORTS/'calibration1450.tsv'
    if len(predictions)!=len(cases):raise ValueError('Partial native output')
    with output.open('x') as out:
        for case,prediction,old in zip(cases,predictions,parent):
            f,p,b=case.split('\t'),prediction.split('\t'),old.split('\t')
            if f[:3]!=p[:3]:raise ValueError('Prediction identity differs')
            values=p[3].split('|') if p[3] else [];oldvalues=b[5].split('|') if b[5] else []
            n=min(18,len(oldvalues))
            if values[:n]!=oldvalues[:n]:raise ValueError('Deployed first18 changed')
            rank=values.index(f[3])+1 if f[3] in values else 0
            out.write(case+'\t'+str(rank)+'\t'+p[3]+'\n')
    r=compare(CASES,PARENT,output);r['baseline_revision']=BASELINE
    groups=r['per_set'];new=[g for name,g in groups.items() if name=='context-search:validation'];old=[g for name,g in groups.items() if name!='context-search:validation']
    r['gates']=dict(first18_identical=True,first_top5_unchanged=all(r['after'][k]==r['before'][k] for k in ('top1','top5')),
        aggregate_top20_gain=r['after']['top20']>r['before']['top20'],each_set_nondecreasing=r['no_per_set_count_loss'],
        new150_nondecreasing=sum(g['after']['top20'] for g in new)>=sum(g['before']['top20'] for g in new),
        old1300_nondecreasing=sum(g['after']['top20'] for g in old)>=sum(g['before']['top20'] for g in old))
    r['qualified']=all(r['gates'].values());r['known_not_independent']=True
    write(REPORTS/'calibration1450.json',r)
    oldchars=load(ROOT/'tools/data/code_generator/models/teacher.npz')[1];oldcodec=Codec(oldchars,json.loads((ROOT/'tools/data/code_generator/codes.json').read_text()))
    values,chars=load(DATA/'models/expanded.npz');codec=Codec(chars,json.loads((DATA/'codes.json').read_text()))
    support=dict(cases=len(cases),old_unsupported=sum(oldcodec.align(f[2],f[3]) is None for f in map(lambda s:s.split('\t'),cases)),
        expanded_unsupported=sum(codec.align(f[2],f[3]) is None for f in map(lambda s:s.split('\t'),cases)),
        scope='Static character/code coverage after TRAIN-only vocabulary freeze; not candidate hit rates or model selection.')
    write(REPORTS/'static-support.json',support)
    write(DATA/'selection.json',dict(selected='expanded' if r['qualified'] else None,
        before=r['before'],after=r['after'],paired=r['paired'],gates=r['gates'],reserve_decoded=False,
        decision='Proceed to dynamic-size Java port and unchanged regression/learning/Android/latency guards' if r['qualified']
        else 'Reject expanded provider for production; preserve d7dec75 and the unused new500. No outcome tuning.'))
    print(json.dumps({k:r[k] for k in ('before','after','paired','gates','qualified')}));print(json.dumps(support))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['native','freeze','generate','report']);p.add_argument('--part',type=int,choices=range(4));a=p.parse_args()
    if a.mode=='generate':
        if a.part is None:p.error('--part required')
        generate(a.part)
    else:{'native':native,'freeze':freeze,'report':report}[a.mode]()
