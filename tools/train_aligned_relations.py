#!/usr/bin/env python3
"""Fit actual clipped tail score differences at the displayed top-five boundary."""
import argparse
import base64
from collections import Counter,defaultdict
import gzip
import json
import math
from pathlib import Path
import struct
from phrase_relation_features import features,stored,encode
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT
from train_phrase_relations import check_inputs

DATA=ROOT/'tools/data/search_alignment'

def encode_aligned(lexicon,weights,strength):
    payload=gzip.decompress(base64.b64decode(encode(lexicon,weights,strength)))
    return base64.encodebytes(gzip.compress(struct.pack('>I',0x50525232)+payload[4:],mtime=0))

def clipped(value,limit=2):return max(-limit,min(limit,value))

def actual_margin(offset,gold,rival,reference,strength=1,limit=2):
    return offset+strength*(clipped(gold-reference,limit)-clipped(rival-reference,limit))

def margin_derivatives(gold,rival,reference,strength=1,limit=2):
    left=strength if abs(gold-reference)<limit else 0
    right=strength if abs(rival-reference)<limit else 0
    return left,-right,right-left

def family(source):
    return source.rsplit(':',1)[0] if source.startswith(('train:hk:','train:ud:')) else source

def train(scored,output):
    check_inputs();protocol=json.loads((DATA/'protocol.json').read_text());p=protocol['stage2_training_parameters']
    rows=list(records(scored));allowed=[tuple(s.split('\t')) for s in (ROOT/'tools/data/phrase_relations/train.tsv').read_text().splitlines()]
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in rows]!=allowed:
        raise ValueError('Non-training or incomplete observation')
    lexicon=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text());cache={};pairs=[];counts=Counter()
    def vector(context,text):
        key=context,text
        if key not in cache:cache[key]=features(context,text,lexicon)
        return cache[key]
    support=defaultdict(set);target_pairs=Counter();family_targets=defaultdict(set)
    for r in rows:
        counts['observed']+=1;gold=r['gold'];values=r['values']
        if gold not in values:counts['missing_from_pool']+=1;continue
        rank=values.index(gold)+1
        if rank==1:counts['first_protected_by_runtime']+=1;continue
        if rank>20:counts['outside_retained_display_pool']+=1;continue
        counts['later_in_pool']+=1
        indices=[4,3,2] if rank>5 else [5,6]
        for index in indices:
            if index>=len(values):continue
            rival=values[index];reference=values[0]
            if rival==gold:continue
            offset=r['adjusted'][gold]-r['adjusted'][rival]
            if abs(offset)>6:counts['outside_maximum_bounded_gap']+=1;continue
            vs=[vector(r['context'],t) for t in (gold,rival,reference)]
            if vs[0]==vs[1]:counts['indistinguishable_features']+=1;continue
            source=family(r['source']);identity=(source,r['context'],r['code'],gold)
            target_pairs[identity]+=1;family_targets[source].add(identity)
            for key in set().union(*vs):
                if len({v.get(key,0) for v in vs})>1:support[key].add(source)
            pairs.append((identity,rival,reference,offset,vs))
            counts['cutoff_blocker_pairs' if rank>5 else 'top5_protection_pairs']+=1
    keys=sorted(sorted((k for k,v in support.items() if len(v)>=p['minimum_source_family_support']),
        key=lambda k:(-len(support[k]),k))[:p['feature_cap']])
    if not keys:raise ValueError('No supported cutoff evidence')
    indices={k:i for i,k in enumerate(keys)};examples=[];groups=[];mass=defaultdict(float)
    def group(source):
        if source.startswith(('train:hk:','train:ud:')):return 'HK'
        if source.startswith('train:tatoeba:'):return 'Tatoeba'
        if source.startswith(('train:daily:','train:authored:')):return 'authored'
        raise ValueError('Unexpected training source')
    for identity,_,_,offset,vs in pairs:
        vectors=[sorted((indices[k],n) for k,n in v.items() if k in indices) for v in vs]
        if vectors[0]==vectors[1]:continue
        weight=1/target_pairs[identity]/len(family_targets[identity[0]])
        g=group(identity[0]);mass[g]+=weight;groups.append(g);examples.append((vectors,offset,weight))
    desired={'HK':.65,'Tatoeba':.2,'authored':.15}
    if any(mass[g]<=0 for g in desired):raise ValueError('Empty supported corpus group')
    examples=[(vs,offset,weight*desired[g]/mass[g]) for g,(vs,offset,weight) in zip(groups,examples)]
    weights=[0.0]*len(keys);accumulated=[0.0]*len(keys);losses=[];saturated=[]
    for epoch in range(p['epochs']):
        gradient=[p['l2']*w for w in weights];loss=0;saturation=0
        for vectors,offset,weight in examples:
            raw=[sum(weights[i]*n for i,n in v) for v in vectors]
            margin=actual_margin(offset,*raw,p['training_strength'],p['score_limit'])
            loss+=weight*(max(0,-margin)+math.log1p(math.exp(-abs(margin))))
            probability=math.exp(-margin)/(1+math.exp(-margin)) if margin>=0 else 1/(1+math.exp(margin))
            derivatives=margin_derivatives(*raw,p['training_strength'],p['score_limit'])
            saturation+=sum(d==0 for d in derivatives[:2])
            for vector,derivative in zip(vectors,derivatives):
                if derivative==0:continue
                scale=-weight*probability*derivative
                for i,n in vector:gradient[i]+=scale*n
        losses.append(loss+p['l2']*sum(w*w for w in weights)/2);saturated.append(saturation)
        for i,g in enumerate(gradient):
            accumulated[i]+=g*g
            weights[i]=max(-p['weight_cap'],min(p['weight_cap'],weights[i]-p['rate']*g/math.sqrt(accumulated[i]+1e-8)))
    fitted=stored({k:w for k,w in zip(keys,weights) if abs(w)>=1e-4})
    output.mkdir(parents=True,exist_ok=True)
    (output/'weights.json').write_text(json.dumps(fitted,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'pairs.tsv').write_text(''.join('\t'.join((*identity,rival,reference,float(offset).hex()))+'\n'
        for identity,rival,reference,offset,_ in pairs))
    (output/'relation_ranker.b64').write_bytes(encode_aligned(lexicon,fitted,1))
    report=dict(protocol_sha256=digest(DATA/'protocol.json'),scored_sha256=digest(scored),training_cases=len(rows),counts=dict(counts),
        pairs=len(pairs),supported_examples=len(examples),source_families=len(family_targets),features=len(fitted),
        initial_actual_clipped_objective=losses[0],final_actual_clipped_objective=losses[-1],final_saturated_sides=saturated[-1],
        source_mix=desired,parameters=p,weights_sha256=digest(output/'weights.json'),pairs_sha256=digest(output/'pairs.tsv'),
        bytes=(output/'relation_ranker.b64').stat().st_size,first_choice='Legacy final first pinned; gold first rows are not fake ranking losses',
        limits='Clipped pairwise surrogate at actual cutoff, not a guarantee of top5 improvement. No evaluation rows/POS or private learning. Independent/native verification required.')
    (output/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
    return fitted

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scored',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();train(a.scored,a.output)
