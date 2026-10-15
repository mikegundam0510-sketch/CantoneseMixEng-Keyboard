#!/usr/bin/env python3
"""Train an optional tail-only residual on actual licensed training pools."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
from evaluate_head_promotion import simulate
from phrase_relation_features import features,stored,encode
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family
from train_head_promotion import gate_margin
from train_phrase_model import ROOT
from train_phrase_relations import check_inputs

DATA=ROOT/'tools/data/completion_scoring'

def train(scored,output,l2):
    check_inputs();protocol=json.loads((DATA/'protocol.json').read_text())['trained_tail_model']
    if digest(scored)!='7176a2d9c0e8ae4addbb99484e4a3214e7c4abeaa1891264fc3cbd9faad8e6af':
        raise ValueError('Pinned actual native training observer required')
    source=ROOT/'tools/data/phrase_relations/train.tsv';rows=list(records(scored))
    expected=[tuple(s.split('\t')) for s in source.read_text().splitlines()]
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in rows]!=expected:
        raise ValueError('Complete licensed training rows required')
    lex=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text())
    head=json.loads((ROOT/'tools/data/search_recovery/head-weights.json').read_text())
    orders=[];simulate(rows,head,lex,.5,.5,{},1.5,orders)
    pairs=[];support=defaultdict(set);target_pairs=Counter();family_targets=defaultdict(set);counts=Counter();cache={}
    for r,first20 in zip(rows,orders):
        values=first20+r['values'][20:];gold=r['gold'];counts['observed']+=1
        if gold not in values:counts['gold_missing']+=1;continue
        rank=values.index(gold)+1
        if rank<=5 or rank>36 or len(values)<=20:counts['not_tail_target']+=1;continue
        if rank>20:
            examples=[(gold,values[19],1)];counts['recovery_targets']+=1
        else:
            outside=[v for v in values[20:36] if v!=gold]
            outside.sort(key=lambda v:-r['adjusted'][v]);examples=[(v,gold,-1) for v in outside[:4]]
            counts['protection_targets']+=1
        for candidate,boundary,label in examples:
            gain=r['adjusted'][candidate]-r['adjusted'][boundary]
            if gain+3<.5:counts['unreachable_score']+=1;continue
            vectors=[]
            for text in (candidate,boundary):
                key=r['context'],text
                if key not in cache:cache[key]=features(*key,lex)
                vectors.append(cache[key])
            delta={k:vectors[0].get(k,0)-vectors[1].get(k,0) for k in vectors[0].keys()|vectors[1].keys()}
            delta={k:n for k,n in delta.items() if n}
            if not delta:counts['indistinguishable']+=1;continue
            fam=family(r['source']);ident=(fam,r['context'],r['code'],gold)
            for key in delta:support[key].add(fam)
            target_pairs[ident]+=1;family_targets[fam].add(ident)
            pairs.append((ident,candidate,boundary,gain,label,delta))
    keys=sorted(sorted((k for k,s in support.items() if len(s)>=2),key=lambda k:(-len(support[k]),k))[:6000])
    indices={k:i for i,k in enumerate(keys)};examples=[];mass=Counter()
    def group(source):
        if source.startswith(('train:hk:','train:ud:')):return 'HK'
        if source.startswith('train:tatoeba:'):return 'Tatoeba'
        if source.startswith(('train:authored:','train:daily:')):return 'authored'
        raise ValueError('Unexpected training source')
    for ident,_,_,gain,label,delta in pairs:
        vector=sorted((indices[k],n) for k,n in delta.items() if k in indices)
        if not vector:continue
        weight=1/target_pairs[ident]/len(family_targets[ident[0]]);g=group(ident[0]);mass[g,label]+=weight
        examples.append((vector,gain,label,weight,g))
    desired={'HK':.65,'Tatoeba':.2,'authored':.15}
    if any(mass[g,label]<=0 for g in desired for label in (-1,1)):raise ValueError('Missing source/label group')
    examples=[(v,gain,label,w*.5*desired[g]/mass[g,label]) for v,gain,label,w,g in examples]
    weights=[0.0]*len(keys);accum=[0.0]*len(keys);losses=[]
    for _ in range(80):
        gradient=[l2*w for w in weights];loss=0
        for vector,gain,label,weight in examples:
            diff=sum(weights[i]*n for i,n in vector);margin,derivative=gate_margin(diff,gain,label)
            loss+=weight*(max(0,-margin)+math.log1p(math.exp(-abs(margin))))
            probability=math.exp(-margin)/(1+math.exp(-margin)) if margin>=0 else 1/(1+math.exp(margin))
            scale=-weight*probability*derivative
            for i,n in vector:gradient[i]+=scale*n
        losses.append(loss+l2*sum(w*w for w in weights)/2)
        for i,g in enumerate(gradient):
            accum[i]+=g*g;weights[i]=max(-1.5,min(1.5,weights[i]-.3*g/math.sqrt(accum[i]+1e-8)))
    fitted=stored({k:w for k,w in zip(keys,weights) if abs(w)>=1e-4});output.mkdir(parents=True,exist_ok=True)
    (output/'tail-weights.json').write_text(json.dumps(fitted,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'tail_ranker.b64').write_bytes(encode(lex,fitted,1.5))
    (output/'tail-pairs.tsv').write_text(''.join('\t'.join((*ident,c,b,float(g).hex(),str(label)))+'\n' for ident,c,b,g,label,_ in pairs))
    report=dict(training_cases=len(rows),counts=dict(counts),pairs=len(pairs),supported_examples=len(examples),
        source_families=len(family_targets),features=len(fitted),parameters=protocol['parameters']|{'l2':l2},
        initial_gate_objective=losses[0],final_gate_objective=losses[-1],training_sha256=digest(source),
        scored_sha256=digest(scored),weights_sha256=digest(output/'tail-weights.json'),model_sha256=digest(output/'tail_ranker.b64'),
        pairs_sha256=digest(output/'tail-pairs.tsv'),protocol_sha256=digest(DATA/'protocol.json'),
        limitation='Training-only stacked baseline head; gold never inserted. Class/source-balanced bounded score/lift surrogate; lexical evidence gate verified at inference. No evaluation or phone data trains the model.')
    (output/'tail-training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scored',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--l2',type=float,choices=(.005,.015),required=True);a=p.parse_args();train(a.scored,a.output,a.l2)
