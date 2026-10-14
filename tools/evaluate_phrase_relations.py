#!/usr/bin/env python3
"""Calibrate frozen phrase evidence on native pools; do not invent missing gold."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from phrase_relation_features import features,correction
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_phrase_relations import DATA,check_inputs

KINDS={k:g for g,ks in {'subject':('SV','SR','SVO'),'negation':('NV','NVO'),
    'object':('VO','VH'),'classifier':('CN','CH'),'question':('AV','VQ')}.items() for k in ks}

def simulate(scored,weights,strength,lexicon,cache=None):
    cache={} if cache is None else cache;groups=defaultdict(list);changes=[];orders=[]
    for r in records(scored):
        values=r['values'];original=values[0] if values else '';base_rank=values.index(r['gold'])+1 if r['gold'] in values else 0
        if len(values)>1:
            evidence={};trusted={}
            for value in values:
                key=r['context'],value
                if key not in cache:
                    fs=features(*key,lexicon);total=sum(n*weights.get(k,0) for k,n in fs.items())
                    kinds={KINDS[k.split('|',1)[0]] for k in fs if k.split('|',1)[0] in KINDS and weights.get(k,0)>0}
                    positive={k for k in fs if k.split('|',1)[0] in KINDS and weights.get(k,0)>0}
                    def unknown(k):
                        p=k.split('|');return p[0]=='G' and 'O' in p[1] or p[0]=='B' and 'O' in p[1:] or p[0]=='Q' and 'O' in p[2]
                    negative={k for k in fs if weights.get(k,0)<-.1 and not unknown(k)}
                    cache[key]=(total,len(kinds)>=2,positive,negative,kinds-{'negation'})
                evidence[value]=cache[key]
            reference=evidence[original]
            lifts={v:max(0,strength*max(-2,min(2,evidence[v][0]-reference[0]))-.1)
                if evidence[v][1] and evidence[v][2]-reference[2] else 0 for v in values}
            scores={v:r['adjusted'][v]+lifts[v] for v in values}
            best=max(values,key=lambda v:scores[v]);pin=True
            if best!=original and scores[best]>=scores[original]+.25 and lifts[best]>=.5 and (
                    reference[3]-evidence[best][3] or len(evidence[best][4])>len(reference[4])):pin=False
            order=sorted(values,key=lambda v:(0 if pin and v==original else 1,-scores[v]))
        else:order=values
        rank=order.index(r['gold'])+1 if r['gold'] in order else 0
        groups[r['source'].split(':',1)[-1]].append(rank)
        orders.append(order[:20])
        if rank!=base_rank:changes.append(dict(source=r['source'],code=r['code'],gold=r['gold'],before=base_rank,after=rank))
    metrics={name:dict(cases=len(rs),top1=sum(r==1 for r in rs),top5=sum(0<r<=5 for r in rs),
        top20=sum(0<r<=20 for r in rs),mrr=sum(1/r for r in rs if 0<r<=20)/len(rs)) for name,rs in groups.items()}
    return metrics,changes,orders

def calibrate(scored,model,output):
    _,protocol=check_inputs();training=json.loads((model/'training-report.json').read_text())
    if training['protocol_sha256']!=digest(DATA/'protocol.json') or training['weights_sha256']!=digest(model/'weights.json'):
        raise ValueError('Frozen model changed')
    weights=json.loads((model/'weights.json').read_text());lexicon=json.loads((DATA/'lexicon.json').read_text())
    cache={};before,_,_=simulate(scored,weights,0,lexicon,cache);trials={};changes={}
    for s in protocol['strength_grid']:
        trials[str(s)],changes[str(s)],_=simulate(scored,weights,s,lexicon,cache)
        print('calibrated='+str(s),flush=True)
    eligible=[s for s,t in trials.items() if all(t[n][m]>=before[n][m] for n in before for m in ('top1','top5','top20'))]
    selected=max(eligible,key=lambda s:(sum(v['mrr'] for v in trials[s].values()),-float(s))) if eligible else None
    if selected and sum(v['mrr'] for v in trials[selected].values())<=sum(v['mrr'] for v in before.values()):selected=None
    report=dict(baseline=before,trials=trials,eligible_strengths=eligible,selected_for_native_and_regression=selected,
        case_changes=changes,calibration_only=True,protocol_sha256=digest(DATA/'protocol.json'),
        policy_sha256=digest(DATA/'policy-protocol.json'),
        scored_sha256=digest(scored),weights_sha256=digest(model/'weights.json'),
        limit='Candidate pools frozen; full native inference and regression guards required before selection/independent test. No private counts in this offline simulation.')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='case_changes'},ensure_ascii=False));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scored',type=Path);p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();calibrate(a.scored,a.model,a.output)
