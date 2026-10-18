"""Separately declared compatibility repair after the original trial failed.

Retain that rejected trial. The checkpoint/vocabulary do not change. The sole
new rule uses the exact legacy provider whenever native count<18, because old
generated slots then fall within the protected deployed prefix. Known cached
legacy lists are reusable only on identical inputs and the pinned parent.
"""
import argparse
import json
from pathlib import Path
import subprocess
from shared import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write,verify
from expanded_model import load,Codec,decode
from report_prefix_retrieval import compare

KNOWN=[('calibration1450',ROOT/'tools/data/context_search/calibration1450.tsv',
    ROOT/'tools/reports/pinned-head-2026-10-17/calibration1450.tsv',
    ROOT/'tools/reports/tail-supplement-2026-10-18/native-calibration1450.tsv'),
    ('guard3893',ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv',
    ROOT/'tools/reports/pinned-head-2026-10-17/guard3893.tsv',
    ROOT/'tools/reports/tail-supplement-2026-10-18/native-guard3893.tsv')]

def seal():
    verify()
    if not json.loads((DATA/'selection.json').read_text())['original_fixed_trial_rejected']:
        raise ValueError('Preserve and reject the original trial first')
    paths=[Path(__file__),DATA/'selection.json',DATA/'models/expanded.npz',DATA/'models/report.json',DATA/'codes.json']
    paths += [p for row in KNOWN for p in row[1:]]
    paths += [WORK/'predictions.tsv',ROOT/'tools/data/code_generator/models/teacher.npz',ROOT/'tools/data/code_generator/codes.json']
    p=dict(parent_revision=BASELINE,reason='Original frozen trial gained1/no losses but changed one deployed first18 prefix on a native16 list. Reject and retain it. This is a new structural compatibility experiment, not a rewritten original result.',
        policy='Native count<18: exact legacy provider and old complete display. Otherwise same245-new-row provider and original final2/native-scoring policy. Threshold18 is the protected prefix length, not searched or target-dependent. No extra model fitting/vocab/score change.',
        implementation='Old rows/shared arrays are bit-identical. Java legacy view filters new lexical edges and maps new-context letters to originalUNK; use same arrays, no second weight copy. Before native qualification verify ordered legacy outputs/score parity against parent teacher.',
        calibration='Known1450 original first18 exact; no first/top5 count change; aggregate top20 gain; every set nondecreasing. Known3893 first18 exact; all aggregate+each-set first/top5/top20 nondecrease. Stop on failed gate.',
        later='Numerically faithful Java dynamic-size bounded loader with explicit original-character mask; full ordinary Java lists; Single32, optional/personal/mixed, exact wired Android unit/Lint, quiet30warm11sixcode ratios<=1.2. Freeze exact implementation and evidence, then new500 once each parent/candidate. No first/top5/top20 count loss and positive top20 gain. No post-independent tuning.',
        reserve='Same newly isolated unused500; never decoded by rejected trial or compatibility selection. Prior two500 sets remain observed. No APK/version/signing/learning/layout change.',
        sha256={str(p.relative_to(ROOT)):sha(p) for p in paths})
    write(DATA/'compat-protocol.json',p);write(DATA/'compat-seal.json',dict(protocol_sha256=sha(DATA/'compat-protocol.json'),before_compatibility_predictions=True))

def check():
    verify();p=json.loads((DATA/'compat-protocol.json').read_text())
    if sha(DATA/'compat-protocol.json')!=json.loads((DATA/'compat-seal.json').read_text())['protocol_sha256']:raise ValueError('Compatibility protocol changed')
    for name,wanted in p['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Compatibility source/input changed: '+name)

def combine(name,predictions):
    spec=next(r for r in KNOWN if r[0]==name);_,cases,native,parent=spec
    inputs,old,baseline=[p.read_text().splitlines() for p in (cases,native,parent)]
    if not len(inputs)==len(old)==len(baseline)==len(predictions):raise ValueError('Partial compatibility output')
    output=REPORTS/('compat-'+name+'.tsv');fallback=0
    with output.open('x') as out:
        for case,nat,par,pred in zip(inputs,old,baseline,predictions):
            f,n,b,p=[s.split('\t') for s in (case,nat,par,pred)]
            if f!=n[:4] or f!=b[:4] or f[:3]!=p[:3]:raise ValueError('Compatibility input identity differs')
            nativevalues=n[5].split('|') if n[5] else []
            # Decision uses native list length only, never target/rank labels.
            use_legacy=len(nativevalues)<18;fallback+=use_legacy
            joined=b[5] if use_legacy else p[3];values=joined.split('|') if joined else []
            oldvalues=b[5].split('|') if b[5] else [];at=min(18,len(oldvalues))
            if values[:at]!=oldvalues[:at]:raise ValueError('Compatibility did not retain deployed first18')
            rank=values.index(f[3])+1 if f[3] in values else 0
            out.write(case+'\t'+str(rank)+'\t'+joined+'\n')
    r=compare(cases,parent,output);r['baseline_revision']=BASELINE
    r['gates']=dict(deployed_first18_identical=True,aggregate_counts_nondecreasing=all(r['after'][k]>=r['before'][k] for k in ('top1','top5','top20')),
        each_set_counts_nondecreasing=r['no_per_set_count_loss'])
    if name=='calibration1450':r['gates']['aggregate_top20_gain']=r['after']['top20']>r['before']['top20']
    r['qualified']=all(r['gates'].values());r['legacy_fallback_cases']=fallback;r['known_not_independent']=True
    write(REPORTS/('compat-'+name+'.json'),r)
    print(name,json.dumps({k:r[k] for k in ('before','after','paired','gates','legacy_fallback_cases','qualified')}))
    return r

def calibration():
    check();r=combine('calibration1450',(WORK/'predictions.tsv').read_text().splitlines())
    write(DATA/'compat-selection.json',dict(qualified=r['qualified'],selected='compatible-expanded' if r['qualified'] else None,reserve_decoded=False))

def generate(part):
    check()
    if not json.loads((DATA/'compat-selection.json').read_text())['qualified']:raise ValueError('Compatibility calibration failed')
    _,cases,native,parent=KNOWN[1]
    inputs,old=[p.read_text().splitlines() for p in (cases,native)]
    v,chars=load(DATA/'models/expanded.npz');codec=Codec(chars,json.loads((DATA/'codes.json').read_text()))
    for a in v.values():a.setflags(write=False)
    path=WORK/f'guard-generated-{part}.tsv';pending=WORK/f'guard-generated-{part}.pending.tsv'
    if path.exists() or pending.exists():raise ValueError('Preserve completed/partial guard generation')
    with pending.open('x') as out:
        for n in range(part,len(inputs),4):
            f,b=inputs[n].split('\t'),old[n].split('\t')
            nativecount=len(b[5].split('|')) if b[5] else 0
            values=decode(v,codec,f[2],f[1]) if nativecount>=18 else []
            out.write('\t'.join(f[:3]+[b[5],'|'.join(t for t,s in values)])+'\n')
            if ((n-part)//4+1)%100==0:print('compat guard',part,'generated',(n-part)//4+1,flush=True)
    pending.rename(path)

def guard():
    check();inputs=KNOWN[1][1].read_text().splitlines();rows=[None]*len(inputs)
    for part in range(4):
        shard=(WORK/f'guard-generated-{part}.tsv').read_text().splitlines()
        if len(shard)!=len(inputs[part::4]):raise ValueError('Partial guard generation')
        rows[part::4]=shard
    path=WORK/'guard-inputs.tsv'
    with path.open('x') as out:out.write(''.join(s+'\n' for s in rows))
    stage=WORK/'native';out=WORK/'guard-predictions.tsv'
    if out.exists():raise ValueError('Preserve existing guard predictions')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.NativeEvaluation',
        str(stage/'app/src/main/assets'),str(path),str(out),str(REPORTS/'guard-scores.tsv')],check=True)
    r=combine('guard3893',out.read_text().splitlines())
    write(DATA/'compat-guard-decision.json',dict(qualified=r['qualified'],reserve_decoded=False,
        decision='Proceed to exact Java compatibility implementation and remaining fixed guards' if r['qualified'] else 'Reject compatibility experiment; preserve deployed d7dec75 and unused new500.'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['seal','calibration','generate','guard']);p.add_argument('--part',type=int,choices=range(4));a=p.parse_args()
    if a.mode=='generate':
        if a.part is None:p.error('--part required')
        generate(a.part)
    else:{'seal':seal,'calibration':calibration,'guard':guard}[a.mode]()
