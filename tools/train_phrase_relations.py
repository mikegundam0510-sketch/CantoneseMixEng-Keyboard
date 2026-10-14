#!/usr/bin/env python3
"""Mine reachable current errors and fit bounded phrase-role relationships."""
import argparse
from collections import Counter
import json
from pathlib import Path
from phrase_relation_features import features,stored,encode
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import learn,matches
from train_phrase_model import ROOT,reverse_codes

DATA=ROOT/'tools/data/phrase_relations'

def check_inputs():
    manifest=json.loads((DATA/'manifest.json').read_text());protocol=json.loads((DATA/'protocol.json').read_text())
    if digest(DATA/'manifest.json')!=protocol['manifest_sha256']:raise ValueError('Frozen manifest changed')
    if digest(ROOT/'tools/phrase_relation_features.py')!=protocol['feature_sha256']:raise ValueError('Frozen features changed')
    for name,checksum in manifest['file_sha256'].items():
        if digest(DATA/name)!=checksum:raise ValueError('Frozen data changed: '+name)
    for name,checksum in protocol['model_sha256'].items():
        if digest(ROOT/'app/src/main/assets'/name)!=checksum:raise ValueError('Baseline model changed')
    return manifest,protocol

def merge(old,new,output):
    manifest,_=check_inputs();previous=list(records(old));added=list(records(new));observed=previous+added
    allowed=[tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()]
    identity=[tuple(r[k] for k in ('source','context','code','gold')) for r in observed]
    if identity!=allowed:raise ValueError('Non-training or incomplete observation')
    if len(previous)!=manifest['reused_training_cases']:raise ValueError('Wrong old observation count')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(old.read_text()+new.read_text())
    print(json.dumps(dict(rows=len(observed),sha256=digest(output))))

def train(scored,output):
    manifest,protocol=check_inputs();rows=list(records(scored))
    allowed=[tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()]
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in rows]!=allowed:
        raise ValueError('Non-training or incomplete observation')
    reverse=reverse_codes();pairs=[];counts=Counter();families=set()
    for r in rows:
        gold=r['gold'];values=r['values'];counts['observed']+=1
        if gold not in values:counts['gold_missing']+=1;continue
        rank=values.index(gold)+1;counts['gold_first' if rank==1 else 'gold_later']+=1
        # Only score gaps inside the largest bounded possible lift are fit.
        rivals=[v for v in values if v!=gold and abs(r['adjusted'][gold]-r['adjusted'][v])<=protocol['maximum_training_score_gap']
            and (rank==1 or r['adjusted'][v]>=r['adjusted'][gold])]
        rivals.sort(key=lambda v:(abs(r['adjusted'][gold]-r['adjusted'][v]),v))
        rivals=rivals[:1 if rank==1 else protocol['maximum_rivals_per_target']]
        if not rivals:counts['no_reachable_rival']+=1;continue
        source=r['source'];family=source.rsplit(':',1)[0] if source.startswith(('train:hk:','train:ud:')) else source
        if not matches(r['code'],gold,reverse):raise ValueError('Inexact gold')
        for rival in rivals:
            if not matches(r['code'],rival,reverse):raise ValueError('Inexact rival')
            pairs.append((family,r['context'],r['code'],gold,rival,r['adjusted'][gold]-r['adjusted'][rival]))
            counts['head_protection_pairs' if rank==1 else 'reachable_error_pairs']+=1;families.add(family)
    lexicon=json.loads((DATA/'lexicon.json').read_text());cache={}
    def extractor(context,text):
        key=context,text
        if key not in cache:cache[key]=features(context,text,lexicon)
        return cache[key]
    p=protocol['parameters'];weights,metrics=learn(pairs,epochs=p['epochs'],rate=p['rate'],l2=p['l2'],
        min_count=p['minimum_independent_support'],maximum_features=p['maximum_features'],
        feature_extractor=extractor,source_mix=protocol['source_mix'])
    weights=stored(weights);output.mkdir(parents=True,exist_ok=True)
    (output/'weights.json').write_text(json.dumps(weights,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'pairs.tsv').write_text(''.join('\t'.join((*r[:5],float(r[5]).hex()))+'\n' for r in pairs))
    (output/'relation_ranker.b64').write_bytes(encode(lexicon,weights,1))
    report=dict(algorithm='Actual reachable same-code score errors plus near correct heads; shared typed word-role/category relations',
        protocol_sha256=digest(DATA/'protocol.json'),manifest_sha256=digest(DATA/'manifest.json'),scored_sha256=digest(scored),
        pairs_sha256=digest(output/'pairs.tsv'),weights_sha256=digest(output/'weights.json'),lexicon_sha256=digest(DATA/'lexicon.json'),
        cases=len(rows),pairs=len(pairs),families=len(families),counts=dict(counts),training=metrics,
        encoded_bytes=(output/'relation_ranker.b64').stat().st_size,
        limits='Reachable final-pool ranking only. No dictionary examples/evaluation POS in training; no complete sentence feature; no beam or private-learning change. Training surrogate is unclipped, actual bounded native inference is separately verified.')
    (output/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
    return weights

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('merge','train'));p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--new',type=Path);a=p.parse_args()
    if a.mode=='merge':
        if not a.new:p.error('--new required')
        merge(a.input,a.new,a.output)
    else:train(a.input,a.output)
