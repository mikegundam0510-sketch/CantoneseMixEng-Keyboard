"""Ordinary code-conditioned generation and fixed fusion, without target access."""
import argparse,json,time
import numpy as np
from common import ROOT,DATA,WORK,REPORTS,frozen,digest,write
from model import load,Codec,decode,batch,forward
from report_prefix_retrieval import compare


def hybrid(v,codec,code,context,parent,generated):
    if not parent:return [t for t,s in generated]
    slots={0:parent[0]};supported=[]
    for i,text in enumerate(parent[1:],1):
        if codec.align(code,text) is None:slots[i]=text
    pool=list(dict.fromkeys(parent+[t for t,s in generated]))
    scored=[t for t in pool if t not in slots.values() and codec.align(code,t) is not None]
    if scored:
        rows=[dict(context=context,code=code,text=t) for t in scored];values,_=forward(v,batch(rows,codec),codec)
        order=sorted(range(len(scored)),key=lambda i:(-float(values[i]),i));supported=[scored[i] for i in order]
    result=[];at=0;limit=min(20,len(slots)+len(supported))
    for i in range(max(limit,max(slots)+1)):
        if i in slots:result.append(slots[i])
        elif at<len(supported):result.append(supported[at]);at+=1
    return result[:20]


def run(arm,part):
    frozen();freeze=json.loads((DATA/'inference-freeze.json').read_text())
    for name,wanted in freeze['sha256'].items():
        if digest(ROOT/name)!=wanted:raise ValueError('Frozen inference changed: '+name)
    v,characters=load(DATA/'models'/(arm+'.npz'));codec=Codec(characters,json.loads((DATA/'codes.json').read_text()))
    cases=(ROOT/'tools/data/context_search/calibration1450.tsv').read_text().splitlines()
    parent=(ROOT/'tools/reports/pinned-head-2026-10-17/calibration1450.tsv').read_text().splitlines()
    outputs={k:WORK/f'{arm}-{k}-{part}.pending.tsv' for k in ('generated','hybrid')}
    if any(p.exists() or p.with_suffix('.tsv').with_name(p.name.replace('.pending','')).exists() for p in outputs.values()):raise ValueError('Preserve existing outputs')
    streams={k:p.open('x') for k,p in outputs.items()};started=time.perf_counter()
    try:
        for n in range(part,len(cases),4):
            fields=cases[n].split('\t');reference=parent[n].split('\t');assert fields==reference[:4]
            source,context,code,target=fields
            # Only context/code enter prediction. Targets are consulted after
            # both ordinary candidate lists are fixed.
            generated=decode(v,codec,code,context,beam=24)
            old=reference[5].split('|') if reference[5] else []
            fused=hybrid(v,codec,code,context,old,generated)
            for kind,values in [('generated',[t for t,s in generated]),('hybrid',fused)]:
                assert len(values)<=20 and len(values)==len(set(values))
                for text in values:
                    if kind=='generated':assert codec.align(code,text) is not None
                if kind=='hybrid' and old:assert values[0]==old[0]
                rank=values.index(target)+1 if target in values else 0
                streams[kind].write(cases[n]+'\t'+str(rank)+'\t'+'|'.join(values)+'\n')
            if ((n-part)//4+1)%50==0:print(arm,part,'decoded',(n-part)//4+1,flush=True)
    finally:
        for s in streams.values():s.close()
    for p in outputs.values():p.rename(p.with_name(p.name.replace('.pending','')))
    print(arm,part,'complete_seconds',time.perf_counter()-started,flush=True)


def report():
    frozen();inputs=(ROOT/'tools/data/context_search/calibration1450.tsv').read_text().splitlines();scores={}
    before=ROOT/'tools/reports/pinned-head-2026-10-17/calibration1450.tsv'
    for arm in ('teacher','contrast'):
        for kind in ('generated','hybrid'):
            rows=[None]*len(inputs)
            for part in range(4):
                shard=(WORK/f'{arm}-{kind}-{part}.tsv').read_text().splitlines();assert len(shard)==len(inputs[part::4])
                for at,line in enumerate(shard):assert '\t'.join(line.split('\t')[:4])==inputs[part+4*at];rows[part+4*at]=line
            out=REPORTS/f'{arm}-{kind}.tsv';out.write_text(''.join(r+'\n' for r in rows))
            r=compare(ROOT/'tools/data/context_search/calibration1450.tsv',before,out)
            if kind=='hybrid':
                r['gates']=dict(aggregate_coverage_gain=r['after']['top20']>r['before']['top20'],
                    new_and_old_counts_nondecreasing=all(all(g['after'][k]>=g['before'][k] for k in ('top1','top5','top20')) for name,g in r['per_set'].items() if name=='context-search:validation') and all(r['after'][k]>=r['before'][k] for k in ('top1','top5','top20')),
                    per_set_first_top5_loss_within_one_pp=all(all(g['before'][k]-g['after'][k]<=g['before']['cases']*.01+1e-9 for k in ('top1','top5')) for g in r['per_set'].values()))
                # Separate old1300 aggregate, without counting new150 gains.
                old=[g for name,g in r['per_set'].items() if name!='context-search:validation']
                r['gates']['old1300_counts_nondecreasing']=all(sum(g['after'][k] for g in old)>=sum(g['before'][k] for g in old) for k in ('top1','top5','top20'))
                r['qualified']=all(r['gates'].values());scores[arm]=r
            else:r['diagnostic_only']=True;r['not_app_accuracy']=True
            write(REPORTS/f'{arm}-{kind}.json',r)
    eligible=[a for a,r in scores.items() if r['qualified']]
    selected=max(eligible,key=lambda a:(scores[a]['after']['top20'],scores[a]['after']['top5'],scores[a]['after']['mrr'],a=='teacher')) if eligible else None
    value=dict(selected=selected,reserve500_decoded=False,trials={a:{k:r[k] for k in ('before','after','gates','qualified')} for a,r in scores.items()},
        decision='Proceed to Java port/parity, regression, learning, Android and latency guards' if selected else 'Reject both hybrid arms; retain production; preserve independent500')
    write(DATA/'selection.json',value);print(json.dumps(value))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True);a=sub.add_parser('run');a.add_argument('arm',choices=['teacher','contrast']);a.add_argument('part',type=int,choices=range(4));sub.add_parser('report');a=p.parse_args()
    if a.mode=='run':run(a.arm,a.part)
    else:report()
