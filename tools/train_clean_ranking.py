#!/usr/bin/env python3
"""Fit only frozen, code-admitted clean TRAIN observations and shadow pairs."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
from clean_ranking_observations import cases
from prepare_clean_ranking import DATA
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family
from train_candidate_ranker import matches
from train_joint_ranking import read_pairs,fit_pairs
from train_phrase_model import ROOT,reverse_codes

def reconstructed(shadow,data=DATA):
    allowed=set(cases(data));manifest=json.loads((shadow/'observation.json').read_text())
    for name,sha in manifest['output_sha256'].items():
        if digest(shadow/name)!=sha:raise ValueError('Shadow observation changed')
    audit={tuple(f[:4]):f for s in (shadow/'audit.tsv').read_text().splitlines() if (f:=s.split('\t'))}
    if not set(audit)<=allowed:raise ValueError('Non-TRAIN audit target')
    reverse=reverse_codes();seen=set();checkpoints=defaultdict(set);rivals=Counter();finals=Counter();pairs=[]
    for line in (shadow/'pairs.tsv').read_text().splitlines():
        f=line.split('\t')
        if len(f)!=10 or tuple(f[:4]) not in audit or tuple(f[:4]) not in allowed:raise ValueError('Non-TRAIN reconstructed pair')
        source,context,code,gold,stage,position,positive,negative,offset,origin=f
        pos=int(position);margin=float.fromhex(offset);key=tuple(f[:8])
        if key in seen or not math.isfinite(margin) or positive==negative or audit[tuple(f[:4])][5]!='true':raise ValueError('Invalid shadow comparison')
        seen.add(key)
        if stage=='prefix':
            if not 0<pos<len(code) or not gold.startswith(positive) or not matches(code[pos:],gold[len(positive):],reverse):raise ValueError('Inexact continuation')
            checkpoints[tuple(f[:4])].add((pos,positive));rivals[tuple(f[:7])]+=1
        elif stage!='final' or pos!=len(code) or positive!=gold:raise ValueError('Invalid shadow stage')
        else:finals[tuple(f[:4])]+=1
        if origin not in ('generated_pruned','reconstructed') or not matches(code[:pos],positive,reverse) or not matches(code[:pos],negative,reverse):raise ValueError('Inexact shadow path')
        pairs.append((stage,family(source),context,code[:pos],positive,negative,margin))
    if any(len(v)>2 for v in checkpoints.values()) or any(v>2 for v in rivals.values()) or any(v>3 for v in finals.values()):raise ValueError('Unbounded reconstructed comparisons')
    return pairs

def train(pools,prefix,shadow,output,l2,data=DATA):
    protocol=json.loads((data/'protocol.json').read_text())
    for name,sha in protocol['source_sha256'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Frozen clean source changed: '+name)
    pairs,counts,categories,actual=read_pairs(pools,prefix,data)
    extra=reconstructed(shadow,data)
    counts['reconstructed_prefix_pairs']=sum(r[0]=='prefix' for r in extra);counts['reconstructed_final_pairs']=sum(r[0]=='final' for r in extra)
    metadata=dict(shadow_sha256=digest(shadow/'pairs.tsv'),
        limits='Clean TRAIN span comparisons and supervised shadow paths only. No inference gold injection; no new vocabulary/glyph generation or evaluation recoding. Ordinary decoding decides adoption.')
    return fit_pairs(pairs+extra,counts,categories,protocol,output,pools,prefix,data,l2,metadata)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pools','prefix','shadow','output'):p.add_argument(name,type=Path)
    p.add_argument('--l2',choices=(.003,.015),type=float,default=.015)
    a=p.parse_args();train(a.pools,a.prefix,a.shadow,a.output,a.l2)
