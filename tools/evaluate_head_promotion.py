#!/usr/bin/env python3
"""Calibrate bounded head swaps using fixed weights and actual displayed scores."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from phrase_relation_features import features
from pilot_final_hard_negatives import records
from train_phrase_model import ROOT

KINDS={'SV':'subject','SR':'subject','SVO':'subject','NV':'negation','NVO':'negation',
       'VO':'object','VH':'object','CN':'classifier','CH':'classifier','AV':'question','VQ':'question'}
NUMERALS=set('〇零一二三四五六七八九十百千萬億兩幾第壹貳參肆伍陸柒捌玖拾佰仟廿卅卌')

def numerals(text):return ''.join(c for c in text if c in NUMERALS)

def evidence(context,text,weights,lexicon):
    fs=features(context,text,lexicon);positive=set();negative=set();kinds=set()
    for key in fs:
        parts=key.split('|');weight=weights.get(key,0);kind=KINDS.get(parts[0])
        if weight>0 and kind:positive.add(key);kinds.add(kind)
        unknown=(parts[0]=='G' and 'O' in parts[1] or parts[0]=='B' and 'O' in parts[1:]
                 or parts[0]=='Q' and 'O' in parts[2])
        if weight<-.1 and not unknown:negative.add(key)
    return sum(n*weights.get(k,0) for k,n in fs.items()),positive,negative,kinds

def trusted(candidate,reference,min_lift):
    raw,pos,neg,kinds=candidate;ref,rpos,rneg,rkinds=reference
    return (raw-ref>=min_lift and len(kinds)>=2 and bool(pos-rpos)
            and (bool(rneg-neg) or len(kinds-{'negation'})>len(rkinds-{'negation'})))

def simulate(rows,weights,lexicon,margin,lift,cache,headstrength=0,orders=None):
    groups=defaultdict(list);changes=[]
    for r in rows:
        values=r['values'][:20];order=list(values)
        def get(text):
            key=r['context'],text
            if key not in cache:cache[key]=evidence(*key,weights,lexicon)
            return cache[key]
        if len(values)>1:
            head=values[0];ref=get(head)
            score=lambda v:r['adjusted'][v]+headstrength*max(-2,min(2,get(v)[0]-ref[0]))
            eligible=[v for v in values[1:20] if numerals(v)==numerals(head) and score(v)>=r['adjusted'][head]+margin
                      and trusted(get(v),ref,lift)]
            if eligible:
                best=max(eligible,key=score)
                at=order.index(best)
                order.pop(at);order.insert(0,best)
        before=values.index(r['gold'])+1 if r['gold'] in values else 0
        rank=order.index(r['gold'])+1 if r['gold'] in order else 0
        groups[r['source']].append(rank)
        if orders is not None:orders.append(order)
        if order!=values:changes.append(dict(source=r['source'],code=r['code'],target=r['gold'],before=before,after=rank,old_head=values[0],new_head=order[0]))
    return {s:dict(cases=len(rs),top1=sum(r==1 for r in rs),top5=sum(0<r<=5 for r in rs),
                  top20=sum(r>0 for r in rs),mrr=sum(1/r for r in rs if r)/len(rs)) for s,rs in groups.items()},changes

def evaluate(scored,output,weights_path=None,headstrength=0):
    rows=list(records(scored));weights=json.loads((weights_path or ROOT/'tools/data/search_alignment/candidate-weights.json').read_text())
    lexicon=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text());cache={}
    before,_=simulate(rows,weights,lexicon,float('inf'),float('inf'),cache,headstrength)
    trials={};changes={}
    for margin in [.5,1]:
        for lift in [.5,1]:
            key=f'margin{margin:g}/lift{lift:g}'
            trials[key],changes[key]=simulate(rows,weights,lexicon,margin,lift,cache,headstrength)
    eligible=[s for s,t in trials.items() if all(t[g][m]>=before[g][m] for g in before for m in ['top1','top5','top20'])
              and sum(v['top1'] for v in t.values())>sum(v['top1'] for v in before.values())]
    selected=max(eligible,key=lambda s:(sum(v['top1']/v['cases'] for v in trials[s].values()),
                                      sum(v['mrr'] for v in trials[s].values()),s)) if eligible else None
    report=dict(before=before,trials=trials,changes=changes,eligible=eligible,selected=selected,
                calibration_only=True,weights_unchanged=weights_path is None,headstrength=headstrength,
                policy='Promote only an existing displayed challenger; keep old head second. Two positive relation kinds, new positive evidence and repair/more non-negation structure, positive raw lift and actual adjusted margin. Native personal guards required.')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scored',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--weights',type=Path);p.add_argument('--headstrength',type=float,default=0)
    a=p.parse_args();evaluate(a.scored,a.output,a.weights,a.headstrength)
