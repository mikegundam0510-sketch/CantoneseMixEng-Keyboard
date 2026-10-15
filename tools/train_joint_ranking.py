#!/usr/bin/env python3
"""Fit shared additive search/final evidence on exact observed training rivals."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import struct
from pilot_final_hard_negatives import records
from prepare_joint_ranking import DATA
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family
from train_candidate_ranker import features,matches,encode
from train_phrase_model import reverse_codes

def read_pairs(pools,prefix,data=DATA):
    manifest=json.loads((data/'manifest.json').read_text());protocol=json.loads((data/'protocol.json').read_text())
    if digest(data/'train.tsv')!=manifest['file_sha256']['train.tsv']:raise ValueError('Frozen training changed')
    allowed=[tuple(s.split('\t')) for s in (data/'train.tsv').read_text().splitlines()]
    observed=list(records(pools))
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in observed]!=allowed:
        raise ValueError('Complete ordered training-only native pools required')
    valid=set(allowed);reverse=reverse_codes();pairs=[];counts=Counter();categories=[]
    for r in observed:
        gold=r['gold'];values=r['values'];rank=values.index(gold)+1 if gold in values else 0
        kind=('missing_from_pool' if not rank else 'outside20' if rank>20 else 'later_top20' if rank>5
              else 'later_top5' if rank>1 else 'correct_first');counts[kind]+=1
        categories.append('\t'.join((r['source'],r['context'],r['code'],gold,kind,str(rank))))
        if not rank:continue
        rivals=[]
        for index in (0,1,4,19):
            if index<len(values) and values[index]!=gold and values[index] not in rivals:rivals.append(values[index])
        rivals=rivals[:protocol['training']['maximum_final_rivals']]
        for rival in rivals:
            # The current decoder can protect its raw winner. Fit the harder
            # of raw-entry and final-score comparisons with the same residual.
            offset=min(r['raw'][gold]-r['raw'][rival],r['adjusted'][gold]-r['adjusted'][rival])
            if not matches(r['code'],gold,reverse) or not matches(r['code'],rival,reverse):raise ValueError('Inexact final pair')
            pairs.append(('final',family(r['source']),r['context'],r['code'],gold,rival,offset))
    prefix_seen=set();checkpoints=defaultdict(set);checkpoint_rivals=Counter()
    for line in prefix.read_text().splitlines():
        row=line.split('\t')
        if len(row)!=10 or tuple(row[:4]) not in valid:raise ValueError('Non-training prefix observation')
        source,context,code,gold,position,positive,negative,offset,hints,rank=row
        at=int(position);margin=float.fromhex(offset)
        if not 0<at<len(code) or int(rank)<2 or not gold.startswith(positive) or positive==negative or not math.isfinite(margin):
            raise ValueError('Invalid prefix checkpoint')
        if not all((matches(code[:at],positive,reverse),matches(code[:at],negative,reverse),
                    matches(code[at:],gold[len(positive):],reverse))):raise ValueError('Inexact prefix pair')
        ident=tuple(row[:7])
        if ident in prefix_seen:raise ValueError('Duplicate prefix comparison')
        prefix_seen.add(ident)
        checkpoints[tuple(row[:4])].add((at,positive));checkpoint_rivals[tuple(row[:6])]+=1
        pairs.append(('prefix',family(source),context,code[:at],positive,negative,margin))
    if any(len(v)>protocol['training']['maximum_prefix_checkpoints'] for v in checkpoints.values()) or any(
            n>protocol['training']['maximum_prefix_rivals'] for n in checkpoint_rivals.values()):
        raise ValueError('Unbounded prefix observation')
    counts['final_pairs']=sum(p[0]=='final' for p in pairs);counts['prefix_pairs']=len(prefix_seen)
    return pairs,counts,categories,protocol

def train(pools,prefix,output,data=DATA,l2=.015):
    pairs,counts,categories,protocol=read_pairs(pools,prefix,data)
    return fit_pairs(pairs,counts,categories,protocol,output,pools,prefix,data,l2)

def fit_pairs(pairs,counts,categories,protocol,output,pools,prefix,data=DATA,l2=.015,metadata=None):
    """Shared optimizer; callers must validate their own training-only observations."""
    p=dict(protocol['training']);cache={}
    if l2 not in p['l2']:raise ValueError('Unregistered regularization')
    p['l2']=l2
    support=defaultdict(set);raw=[];per_target=Counter();per_family=defaultdict(set)
    def vector(context,text):
        key=context,text
        if key not in cache:cache[key]=features(context,text)
        return cache[key]
    for stage,fam,context,code,positive,negative,offset in pairs:
        a,b=vector(context,positive),vector(context,negative)
        delta={k:a.get(k,0)-b.get(k,0) for k in a.keys()|b.keys() if a.get(k,0)!=b.get(k,0)}
        ident=(stage,fam,context,code,positive)
        for key in delta:support[key].add(fam)
        per_target[ident]+=1;per_family[stage,fam].add(ident);raw.append((ident,delta,offset))
    keys=sorted(sorted((k for k,s in support.items() if len(s)>=p['minimum_family_support']),
                       key=lambda k:(-len(support[k]),k))[:p['feature_cap']])
    if not keys:raise ValueError('No independently supported shared features')
    index={key:i for i,key in enumerate(keys)};examples=[];mass=Counter()
    def group(fam):
        if fam.startswith(('train:hk:','train:ud:')):return 'HK'
        if fam.startswith('train:tatoeba:'):return 'Tatoeba'
        if fam.startswith(('train:authored:','train:daily:')):return 'authored'
        raise ValueError('Unknown training source')
    for ident,delta,offset in raw:
        stage,fam=ident[:2];v=sorted((index[k],n) for k,n in delta.items() if k in index)
        if not v:continue
        weight=1/per_target[ident]/len(per_family[stage,fam]);domain=group(fam)
        mass[stage,domain]+=weight;examples.append((v,offset,weight,stage,domain))
    for stage in p['stage_mix']:
        for domain in p['source_mix']:
            if mass[stage,domain]<=0:raise ValueError('Missing shared-training source/stage')
    examples=[(v,offset,w*p['stage_mix'][stage]*p['source_mix'][domain]/mass[stage,domain])
              for v,offset,w,stage,domain in examples]
    weights=[0.0]*len(keys);accum=[0.0]*len(keys);losses=[]
    for epoch in range(p['epochs']):
        gradient=[p['l2']*w for w in weights];loss=0
        for vector,offset,weight in examples:
            margin=offset+sum(weights[i]*n for i,n in vector)
            loss+=weight*(max(0,-margin)+math.log1p(math.exp(-abs(margin))))
            probability=math.exp(-margin)/(1+math.exp(-margin)) if margin>=0 else 1/(1+math.exp(margin))
            for i,n in vector:gradient[i]-=weight*probability*n
        losses.append(loss+p['l2']*sum(w*w for w in weights)/2)
        for i,g in enumerate(gradient):
            accum[i]+=g*g;weights[i]=max(-p['weight_cap'],min(p['weight_cap'],weights[i]-p['rate']*g/math.sqrt(accum[i]+1e-8)))
    fitted={k:struct.unpack('>f',struct.pack('>f',w))[0] for k,w in zip(keys,weights) if abs(w)>=1e-4}
    output.mkdir(parents=True,exist_ok=True)
    (output/'weights.json').write_text(json.dumps(fitted,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'pairs.tsv').write_text(''.join('\t'.join((*r[:6],float(r[6]).hex()))+'\n' for r in pairs))
    (output/'categories.tsv').write_text('\n'.join(categories)+'\n')
    for strength in (.25,.5,1):(output/f'joint-{strength:g}.b64').write_bytes(encode(fitted,strength)[0])
    report=dict(training_cases=sum(counts[k] for k in ('missing_from_pool','outside20','later_top20','later_top5','correct_first')),
        counts=dict(counts),pairs=len(pairs),supported_examples=len(examples),source_families=len({r[1] for r in pairs}),
        features=len(fitted),stage_mix=p['stage_mix'],source_mix=p['source_mix'],parameters=p,
        initial_objective=losses[0],final_objective=losses[-1],
        training_sha256=digest(data/'train.tsv'),protocol_sha256=digest(data/'protocol.json'),
        pools_sha256=digest(pools),prefix_sha256=digest(prefix),weights_sha256=digest(output/'weights.json'),
        pairs_sha256=digest(output/'pairs.tsv'),categories_sha256=digest(output/'categories.tsv'),
        model_sha256={str(s):digest(output/f'joint-{s:g}.b64') for s in (.25,.5,1)},
        limits='Shared decomposable score, not a calibrated sentence probability or a guarantee of end-to-end improvement. Baseline pruning offsets include lookahead. Actual native search/guards are required. Missing golds are not inserted; no evaluation/phone data train weights.')
    if metadata:report.update(metadata)
    (output/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))
    return fitted

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pools','prefix','output'):p.add_argument(name,type=Path)
    p.add_argument('--l2',type=float,choices=(.003,.015),default=.015)
    a=p.parse_args();train(a.pools,a.prefix,a.output,l2=a.l2)
