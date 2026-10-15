#!/usr/bin/env python3
"""Fit the actual clipped score-and-lift gate on training-only native head pairs."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
from phrase_relation_features import features,stored
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family,clipped
from train_phrase_model import ROOT
from train_phrase_relations import check_inputs
from encode_head_promotion import encode


def gate_margin(diff,base_gain,label,strength=1.5,margin=.5,lift=.5):
    raw=diff-lift;score=base_gain+strength*clipped(diff)-margin
    derivative=1 if raw<=score else strength if abs(diff)<2 else 0
    return label*min(raw,score),label*derivative


def train(scored,output,l2=.015):
    check_inputs();rows=list(records(scored));source=ROOT/'tools/data/phrase_relations/train.tsv'
    expected=[tuple(s.split('\t')) for s in source.read_text().splitlines()]
    if [tuple(r[k] for k in ['source','context','code','gold']) for r in rows]!=expected:
        raise ValueError('Complete training-only native observation required')
    lex=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text());cache={};pairs=[];counts=Counter()
    support=defaultdict(set);target_pairs=Counter();family_targets=defaultdict(set)
    for r in rows:
        values=r['values'][:20];gold=r['gold'];counts['observed']+=1
        if gold not in values:counts['outside_display']+=1;continue
        rank=values.index(gold)+1
        if len(values)<2:counts['no_challenger']+=1;continue
        label=-1 if rank==1 else 1;head=values[0]
        for candidate in values[1:9] if rank==1 else [gold]:
            gain=r['adjusted'][candidate]-r['adjusted'][head]
            if gain+3<.5:counts['cannot_reach_score_gate']+=1;continue
            vectors=[]
            for text in (candidate,head):
                key=r['context'],text
                if key not in cache:cache[key]=features(*key,lex)
                vectors.append(cache[key])
            diff={k:vectors[0].get(k,0)-vectors[1].get(k,0) for k in set(vectors[0])|set(vectors[1])}
            diff={k:n for k,n in diff.items() if n}
            if not diff:counts['indistinguishable']+=1;continue
            fam=family(r['source']);identity=(fam,r['context'],r['code'],gold)
            for key in diff:support[key].add(fam)
            target_pairs[identity]+=1;family_targets[fam].add(identity)
            pairs.append((identity,candidate,head,gain,label,diff));counts['correct_head_protection' if label<0 else 'wrong_head_repair']+=1
    keys=sorted(sorted((k for k,s in support.items() if len(s)>=2),key=lambda k:(-len(support[k]),k))[:6000])
    indices={k:i for i,k in enumerate(keys)};examples=[];mass=Counter()
    def group(source):
        if source.startswith(('train:hk:','train:ud:')):return 'HK'
        if source.startswith('train:tatoeba:'):return 'Tatoeba'
        if source.startswith(('train:authored:','train:daily:')):return 'authored'
        raise ValueError('Unexpected training family')
    for ident,_,_,gain,label,diff in pairs:
        vector=sorted((indices[k],n) for k,n in diff.items() if k in indices)
        if not vector:continue
        weight=1/target_pairs[ident]/len(family_targets[ident[0]]);g=group(ident[0]);mass[g]+=weight
        examples.append((vector,gain,label,weight,g))
    desired={'HK':.65,'Tatoeba':.2,'authored':.15}
    if any(mass[g]<=0 for g in desired):raise ValueError('Missing source group')
    examples=[(v,gain,label,w*desired[g]/mass[g]) for v,gain,label,w,g in examples]
    weights=[0.0]*len(keys);accum=[0.0]*len(keys);losses=[]
    for epoch in range(80):
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
    (output/'head-weights.json').write_text(json.dumps(fitted,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'head-pairs.tsv').write_text(''.join('\t'.join((*i,c,h,float(g).hex(),str(label)))+'\n' for i,c,h,g,label,_ in pairs))
    base_path=ROOT/'tools/data/search_alignment/candidate-relation_ranker.b64'
    base=base_path.read_bytes()
    (output/'relation_ranker.b64').write_bytes(encode(base,.5,.5,fitted,1.5))
    report=dict(training_cases=len(rows),counts=dict(counts),pairs=len(pairs),supported_examples=len(examples),source_families=len(family_targets),
                features=len(fitted),initial_actual_gate_objective=losses[0],final_actual_gate_objective=losses[-1],
                parameters=dict(epochs=80,rate=.3,l2=l2,minimum_source_family_support=2,head_strength=1.5,limit=2,margin=.5,lift=.5,challengers=20,protection_ranks='2..9'),
                source_mix=desired,training_sha256=digest(source),scored_sha256=digest(scored),weights_sha256=digest(output/'head-weights.json'),
                pairs_sha256=digest(output/'head-pairs.tsv'),tail_asset_sha256=digest(base_path),
                limitation='Actual min(raw-lift, bounded-score-margin) surrogate; discrete structural evidence gate is verified at inference. No evaluation or personal text trains this model; original tail weights unchanged.')
    (output/'head-training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scored',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--l2',type=float,choices=[.005,.015],default=.015)
    a=p.parse_args();train(a.scored,a.output,a.l2)
