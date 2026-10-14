#!/usr/bin/env python3
"""Simulate the exact PRR2 bounded tail policy on actual native eligible pools."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from phrase_relation_features import features
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_aligned_relations import DATA,clipped
from train_phrase_model import ROOT

def simulate(rows,weights,lexicon,strength,cache=None):
    cache={} if cache is None else cache;groups=defaultdict(list);orders=[];changes=[]
    for r in rows:
        values=r['values'];order=list(values)
        if len(values)>1:
            raw={}
            for value in values[:20]:
                key=r['context'],value
                if key not in cache:cache[key]=sum(n*weights.get(k,0) for k,n in features(*key,lexicon).items())
                raw[value]=cache[key]
            first=values[0];reference=raw[first]
            scores={v:r['adjusted'][v]+strength*clipped(raw[v]-reference) for v in values[:20]}
            order=[first]+sorted(values[1:20],key=lambda v:-scores[v])+values[20:]
        before=values.index(r['gold'])+1 if r['gold'] in values else 0
        rank=order.index(r['gold'])+1 if r['gold'] in order else 0
        groups[r['source']].append(rank);orders.append(order[:20])
        if min(before,21)!=min(rank,21):changes.append(dict(source=r['source'],code=r['code'],target=r['gold'],before=before,after=rank))
    metrics={k:dict(cases=len(rs),top1=sum(r==1 for r in rs),top5=sum(0<r<=5 for r in rs),
        top20=sum(0<r<=20 for r in rs),mrr=sum(1/r for r in rs if 0<r<=20)/len(rs)) for k,rs in groups.items()}
    return metrics,changes,orders

def evaluate(scored,model,output):
    protocol=json.loads((DATA/'protocol.json').read_text());training=json.loads((model/'training-report.json').read_text())
    if training['protocol_sha256']!=digest(DATA/'protocol.json') or training['weights_sha256']!=digest(model/'weights.json'):
        raise ValueError('Frozen model changed')
    weights=json.loads((model/'weights.json').read_text());lexicon=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text())
    rows=list(records(scored));cache={};before,_,_=simulate(rows,weights,lexicon,0,cache)
    trials={};changes={}
    for strength in [.25,.5,1,1.5]:
        trials[str(strength)],changes[str(strength)],_=simulate(rows,weights,lexicon,strength,cache)
    eligible=[s for s,t in trials.items() if all(t[k][m]>=before[k][m] for k in before for m in ['top1','top5','top20'])]
    selected=max(eligible,key=lambda s:(sum(v['top5']/v['cases'] for v in trials[s].values()),
        sum(v['mrr'] for v in trials[s].values()),-float(s))) if eligible else None
    if selected and not any(trials[selected][k]['top5']>before[k]['top5'] for k in before):selected=None
    result=dict(before=before,trials=trials,eligible=eligible,selected=selected,changes=changes,calibration_only=True,
        protocol_sha256=digest(DATA/'protocol.json'),scored_sha256=digest(scored),weights_sha256=digest(model/'weights.json'),
        rule='Per-set no-first/top5/top20 loss; useful top5 gain; equal-set top5 thenMRR, lower strength ties. Native/learning/latency and fresh500 required.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='changes'},ensure_ascii=False));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['scored','model','output']:p.add_argument(name,type=Path)
    a=p.parse_args();evaluate(a.scored,a.model,a.output)
