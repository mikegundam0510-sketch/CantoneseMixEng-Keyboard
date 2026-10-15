#!/usr/bin/env python3
"""Train shadow-path comparisons; gold reconstruction never runs at inference."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from observe_structured_training import gap_cases
from prepare_joint_ranking import DATA
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family
from train_candidate_ranker import matches
from train_joint_ranking import read_pairs,fit_pairs
from train_phrase_model import ROOT,reverse_codes

RESEARCH=ROOT/'tools/data/structured_ranking'

def merge(work,pools,prefix,output,gap_only=False):
    expected=gap_cases(pools,prefix,only_uncovered=gap_only);allowed=set(expected);audits={};visible={};pairs=[]
    baseline={tuple(s.split('\t')[:4]):s for s in (pools.parent/'visible.tsv').read_text().splitlines()}
    for i in range(3):
        folder=work/f'observed-{i}'
        for name,target in (('audit.tsv',audits),('visible.tsv',visible)):
            for line in (folder/name).read_text().splitlines():
                row=line.split('\t');ident=tuple(row[:4])
                if ident not in allowed or ident in target:raise ValueError('Partial/duplicate/non-TRAIN trace')
                target[ident]=line
        pairs.extend((folder/'pairs.tsv').read_text().splitlines())
    if set(audits)!=allowed or set(visible)!=allowed:raise ValueError('Incomplete gap trace')
    if any(visible[key]!=baseline[key] for key in expected):raise ValueError('Observer changed ordinary inference')
    order={row:i for i,row in enumerate(expected)};pairs.sort(key=lambda s:order[tuple(s.split('\t')[:4])])
    output.mkdir(parents=True,exist_ok=True)
    (output/'cases.tsv').write_text(''.join('\t'.join(row)+'\n' for row in expected))
    for name,rows in (('audit.tsv',audits),('visible.tsv',visible)):(output/name).write_text(''.join(rows[key]+'\n' for key in expected))
    (output/'reconstructed-pairs.tsv').write_text(''.join(s+'\n' for s in pairs))
    counts=Counter()
    for line in audits.values():
        f=line.split('\t')
        if len(f)!=14:raise ValueError('Incomplete audit')
        selected,potential,completed,generated=f[4:8]
        counts['all']+=1
        counts['no_legal_han_path' if f[13]=='false' else 'outside_static_option_caps' if potential=='false' else 'selected_option_gap' if selected=='false'
               else 'completed_confidence_filtered' if completed=='true' else 'final_pool_cap' if generated=='true'
               else 'prefix_search_loss']+=1
        if int(f[8]):counts['observed_pruned_gold_prefix']+=1
    metadata=dict(counts=counts,ordinary_inference_parity=len(expected),pairs=len(pairs),
        input_sha256={'pools':digest(pools),'prefix':digest(prefix)},
        output_sha256={name:digest(output/name) for name in ('cases.tsv','audit.tsv','visible.tsv','reconstructed-pairs.tsv')},
        limits='TRAIN-only shadow reconstruction, not recovered inference or held-out accuracy. Static option eligibility is an upper bound; selected-option gaps can also follow an earlier pruning loss.')
    (output/'observation.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n');print(json.dumps(metadata))

def read_reconstructed(folder=RESEARCH):
    protocol=json.loads((folder/'protocol.json').read_text());manifest=json.loads((folder/'observation.json').read_text())
    if digest(DATA/'train.tsv')!=protocol['training_sha256']:raise ValueError('Frozen TRAIN changed')
    for name,sha in protocol['source_sha256'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Frozen structured source changed: '+name)
    for name,sha in manifest['output_sha256'].items():
        if digest(folder/name)!=sha:raise ValueError('Frozen structured trace changed')
    allowed={tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()}
    cases={tuple(s.split('\t')) for s in (folder/'cases.tsv').read_text().splitlines()}
    if not cases<=allowed or len(cases)!=1821:raise ValueError('Expected complete TRAIN-only missing targets')
    audits={tuple(f[:4]):f for s in (folder/'audit.tsv').read_text().splitlines() if (f:=s.split('\t'))}
    reverse=reverse_codes();seen=set();checkpoints=defaultdict(set);rivals=Counter();finals=Counter();pairs=[]
    for line in (folder/'reconstructed-pairs.tsv').read_text().splitlines():
        f=line.split('\t')
        if len(f)!=10 or tuple(f[:4]) not in cases:raise ValueError('Non-training shadow pair')
        source,context,code,gold,stage,position,positive,negative,offset,provenance=f
        at=int(position);margin=float.fromhex(offset);ident=tuple(f[:8])
        if ident in seen or not math.isfinite(margin) or positive==negative or audits[tuple(f[:4])][5]!='true':
            raise ValueError('Invalid/ineligible reconstructed pair')
        seen.add(ident)
        if stage=='prefix':
            if not 0<at<len(code) or not gold.startswith(positive) or not matches(code[at:],gold[len(positive):],reverse):
                raise ValueError('Invalid shadow prefix continuation')
            checkpoints[tuple(f[:4])].add((at,positive));rivals[tuple(f[:7])]+=1
        elif stage!='final' or at!=len(code) or positive!=gold:raise ValueError('Invalid shadow final pair')
        else:finals[tuple(f[:4])]+=1
        if provenance not in ('reconstructed','generated_pruned') or not matches(code[:at],positive,reverse) or not matches(code[:at],negative,reverse):
            raise ValueError('Inexact shadow pair')
        pairs.append((stage,family(source),context,code[:at],positive,negative,margin))
    if any(len(v)>2 for v in checkpoints.values()) or any(v>2 for v in rivals.values()) or any(v>3 for v in finals.values()):
        raise ValueError('Unbounded shadow comparisons')
    return pairs,protocol

def train(pools,prefix,output,l2,folder=RESEARCH):
    extra,protocol=read_reconstructed(folder)
    if not extra:raise ValueError('No learnable reconstructed comparisons; do not rerun identical old fits')
    pairs,counts,categories,_=read_pairs(pools,prefix)
    observation=json.loads((folder/'observation.json').read_text())
    if observation['input_sha256']!={'pools':digest(pools),'prefix':digest(prefix)}:raise ValueError('Baseline observations changed')
    counts['reconstructed_prefix_pairs']=sum(p[0]=='prefix' for p in extra)
    counts['reconstructed_final_pairs']=sum(p[0]=='final' for p in extra)
    metadata=dict(protocol_sha256=digest(folder/'protocol.json'),reconstruction_sha256=digest(folder/'reconstructed-pairs.tsv'),
        limits='Gold paths reconstructed only from licensed TRAIN labels with original transition scoring. No inference gold insertion; ordinary answer-free native decoding alone determines accuracy. Beyond-static-cap targets supply diagnosis only.')
    return fit_pairs(pairs+extra,counts,categories,protocol,output,pools,prefix,DATA,l2,metadata)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('merge','train'))
    p.add_argument('--work',type=Path);p.add_argument('--pools',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--gap-only',action='store_true')
    p.add_argument('--l2',type=float,choices=(.003,.015),default=.015);a=p.parse_args()
    if a.mode=='merge':merge(a.work,a.pools,a.prefix,a.output,a.gap_only)
    else:train(a.pools,a.prefix,a.output,a.l2)
