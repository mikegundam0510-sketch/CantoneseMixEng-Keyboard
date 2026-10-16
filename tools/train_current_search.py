#!/usr/bin/env python3
"""Fit bounded shared endpoint evidence from current-parent TRAIN observations."""
import argparse
import base64
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import struct

import numpy as np
import scipy
from scipy.sparse import csr_matrix
from scipy.special import expit

from clean_ranking_observations import cases
from observe_current_search import BASELINE, DATA
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_aligned_relations import family
from train_candidate_ranker import encode, matches
from train_clean_ranking import reconstructed
from train_phrase_model import ROOT, reverse_codes


def features(context, text, maximum=5):
    history = ''
    for c in context:
        history = (history+c)[-(maximum-1):] if han(c) else ''
    result = Counter()
    for c in text:
        if not han(c):
            history = ''
            continue
        window = history+c
        for length in range(2, min(maximum, len(window))+1):
            result[window[-length:]] += 1
        history = window[-(maximum-1):]
    return result


def encoded(weights, strength, maximum=5):
    if maximum not in (3, 5) or any(not 2 <= len(k) <= maximum or abs(v) > .25 for k,v in weights.items()):
        raise ValueError('Invalid current-search feature bounds')
    blob, nodes, edges = encode(weights, strength, word_relations=True)
    raw = bytearray(gzip.decompress(base64.b64decode(blob)))
    # Existing bounded Han-trie WRK1 loader; this model is character evidence.
    struct.pack_into('>I', raw, 4, maximum)
    return base64.encodebytes(gzip.compress(raw, mtime=0)), nodes, edges


def collect(pools, shadow, output_dir=DATA):
    protocol = json.loads((DATA/'protocol.json').read_text())
    if digest(ROOT/'tools/data/clean_ranking/train.tsv') != protocol['training_sha256']:
        raise ValueError('Training data changed')
    note = json.loads((pools/'observation.json').read_text())
    if note['baseline_revision'] != BASELINE or note['reused'] != 0:
        raise ValueError('Current-parent fresh observations required')
    for name, value in note['output_sha256'].items():
        if digest(pools/name) != value: raise ValueError('Observation changed')
    allowed = cases(); observed = list(records(pools/'pools.tsv'))
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in observed] != allowed:
        raise ValueError('Complete ordered TRAIN observations required')
    reverse = reverse_codes(); pairs = []; counts = Counter(); categories = []
    for r in observed:
        gold=r['gold']; values=r['values']; rank=values.index(gold)+1 if gold in values else 0
        kind='missing' if not rank else 'first' if rank==1 else 'top5' if rank<=5 else 'top20' if rank<=20 else 'outside20'
        counts[kind]+=1
        categories.append('\t'.join((r['source'],r['context'],r['code'],gold,kind,str(rank))))
        if not rank: continue
        ordered = sorted((v for v in values if v!=gold), key=lambda v:(
            min(r['raw'][gold]-r['raw'][v],r['adjusted'][gold]-r['adjusted'][v]),v))
        rivals=[]
        for rival in ([values[0]]+ordered):
            if rival!=gold and rival not in rivals: rivals.append(rival)
            if len(rivals)==3: break
        for rival in rivals:
            offset=min(r['raw'][gold]-r['raw'][rival],r['adjusted'][gold]-r['adjusted'][rival])
            pairs.append(('final',family(r['source']),r['context'],r['code'],gold,rival,offset,'ordinary'))
    valid=set(allowed); checkpoints=defaultdict(set); rival_counts=Counter(); seen=set(); lost=set()
    for line in (pools/'prefix.tsv').read_text().splitlines():
        row=line.split('\t')
        if len(row)!=10 or tuple(row[:4]) not in valid: raise ValueError('Non-TRAIN prefix')
        source,context,code,gold,position,positive,negative,offset,origin,rank=row
        at=int(position); margin=float.fromhex(offset)
        if not 0<at<len(code) or int(rank)<1 or origin not in ('lost','survived') or not gold.startswith(positive):
            raise ValueError('Invalid checkpoint')
        if not matches(code[at:],gold[len(positive):],reverse): raise ValueError('Inexact continuation')
        key=tuple(row[:7])
        if key in seen: raise ValueError('Duplicate checkpoint rival')
        seen.add(key); checkpoints[tuple(row[:4])].add((at,positive));rival_counts[tuple(row[:6])]+=1
        if origin=='lost': lost.add(tuple(row[:4]))
        pairs.append(('prefix',family(source),context,code[:at],positive,negative,margin,origin))
    if any(len(v)>2 for v in checkpoints.values()) or any(v>3 for v in rival_counts.values()):
        raise ValueError('Unbounded checkpoint mining')
    if json.loads((shadow/'observation.json').read_text()).get('parent_revision')!=BASELINE:
        raise ValueError('Current-parent shadow observations required')
    extra=reconstructed(shadow)
    pairs.extend((*r,'shadow') for r in extra)
    unique={}
    for row in pairs:
        stage,fam,context,code,positive,negative,margin,origin=row
        if positive==negative or not math.isfinite(margin) or not all(matches(code,t,reverse) for t in (positive,negative)):
            raise ValueError('Invalid actual rival')
        key=row[:6]
        if key not in unique or margin<unique[key][6]: unique[key]=row
    pairs=list(unique.values())
    output_dir.mkdir(parents=True,exist_ok=True)
    output=output_dir/'pairs.jsonl.gz'
    if output.exists(): raise ValueError('Preserve collected pairs')
    output.write_bytes(gzip.compress(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in pairs).encode(),mtime=0))
    (output_dir/'categories.tsv').write_text('\n'.join(categories)+'\n')
    manifest=dict(parent_revision=BASELINE,training_sha256=protocol['training_sha256'],cases=len(allowed),categories=dict(counts),
        pairs=len(pairs),stage_counts=dict(Counter(r[0] for r in pairs)),origin_counts=dict(Counter(r[7] for r in pairs)),
        targets_with_observed_lost_prefix=len(lost),pairs_sha256=digest(output),
        observations=note,shadow=json.loads((shadow/'observation.json').read_text()),
        limitation='Training observation counts are not independent accuracy. Raw prefix gaps omit bounded lookahead; shadow finals approximate pre-PRR3 score. Ordinary candidate inference decides adoption.')
    (output_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest),flush=True)


def check():
    freeze=json.loads((DATA/'freeze.json').read_text())
    for name,value in freeze['sha256'].items():
        if digest(ROOT/name)!=value: raise ValueError('Frozen input/source changed: '+name)


def fit(output, maximum=5):
    check()
    if output.exists(): raise ValueError('Preserve existing fitted models')
    p=json.loads((DATA/'protocol.json').read_text())['training']
    p['maximum_feature_length']=maximum
    rows=[json.loads(s) for s in gzip.decompress((DATA/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
    support=defaultdict(set); raw=[]; rivals=Counter(); family_cases=defaultdict(set); cache={}
    def vector(context,text):
        key=(context,text)
        if key not in cache: cache[key]=features(context,text,maximum)
        return cache[key]
    for stage,fam,context,code,positive,negative,offset,origin in rows:
        a,b=vector(context,positive),vector(context,negative)
        delta={k:a[k]-b[k] for k in a.keys()|b.keys() if a[k]!=b[k]}
        ident=(stage,fam,context,code,positive)
        for k in delta: support[k].add(fam)
        rivals[ident]+=1;family_cases[stage,fam].add(ident);raw.append((ident,delta,offset))
    keys=sorted(sorted((k for k in support if len(support[k])>=p['minimum_family_support']),
        key=lambda k:(-len(support[k]),k))[:p['feature_cap']])
    indices={k:i for i,k in enumerate(keys)}; ri=[];ci=[];v=[];offsets=[];mass=Counter();metadata=[]
    for ident,delta,offset in raw:
        values=sorted((indices[k],n) for k,n in delta.items() if k in indices)
        if not values: continue
        stage,fam=ident[:2]
        domain='HK' if fam.startswith(('train:hk:','train:ud:')) else 'Tatoeba' if fam.startswith('train:tatoeba:') else 'authored'
        weight=1/rivals[ident]/len(family_cases[stage,fam]);mass[stage,domain]+=weight
        for i,n in values:ri.append(len(offsets));ci.append(i);v.append(n)
        offsets.append(offset);metadata.append((stage,domain,weight))
    matrix=csr_matrix((v,(ri,ci)),shape=(len(offsets),len(keys)),dtype=np.float64)
    offset=np.asarray(offsets); sample=np.asarray([w*p['stage_mix'][s]*p['source_mix'][d]/mass[s,d] for s,d,w in metadata])
    if not np.isclose(sample.sum(),1) or len(mass)!=6:raise ValueError('Missing TRAIN source/stage')
    weights=np.zeros(len(keys));accum=np.zeros(len(keys));losses=[]
    for epoch in range(p['epochs']):
        margin=offset+matrix@weights
        loss=float(sample@np.logaddexp(0,-margin)+p['l2']*.5*(weights@weights));losses.append(loss)
        gradient=p['l2']*weights-matrix.T@(sample*expit(-margin))
        accum+=gradient*gradient
        weights=np.clip(weights-p['rate']*gradient/np.sqrt(accum+1e-8),-p['weight_cap'],p['weight_cap'])
    fitted={k:struct.unpack('>f',struct.pack('>f',w))[0] for k,w in zip(keys,weights) if abs(w)>=1e-4}
    stored=np.asarray([fitted.get(k,0) for k in keys])
    final_objective=float(sample@np.logaddexp(0,-offset-matrix@stored)+p['l2']*.5*(stored@stored))
    output.mkdir(parents=True)
    (output/'weights.json').write_text(json.dumps(fitted,ensure_ascii=False,sort_keys=True)+'\n')
    models={}
    for strength in ((.5,) if maximum==3 else (.5,1)):
        blob,nodes,edges=encoded(fitted,strength,maximum);name=f'search-{strength:g}.b64'
        (output/name).write_bytes(blob);models[name]=digest(output/name)
    report=dict(parent_revision=BASELINE,numpy=np.__version__,scipy=scipy.__version__,maximum_feature_length=maximum,feature_lengths=dict(Counter(map(len,fitted))),
        features=len(fitted),supported_pairs=len(offsets),source_families=len({r[1] for r in rows}),nodes=nodes,
        array_bytes=12*nodes+8*edges+4*65536,parameters=p,initial_objective=losses[0],final_objective=final_objective,
        objectives=losses,models=models,weights_sha256=digest(output/'weights.json'),freeze_sha256=digest(DATA/'freeze.json'),
        limitation='TRAIN loss only, not keyboard accuracy; short model is diagnostic. At most4 endpoints of0.25 each, below1.5 clipping; split-token score is exact.')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('collect');a.add_argument('pools',type=Path);a.add_argument('shadow',type=Path);a.add_argument('--output',type=Path,default=DATA)
    a=s.add_parser('fit');a.add_argument('output',type=Path);a.add_argument('--maximum',type=int,choices=(3,5),default=5)
    a=p.parse_args()
    if a.mode=='collect':collect(a.pools,a.shadow,a.output)
    else:fit(a.output,a.maximum)
