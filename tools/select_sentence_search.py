#!/usr/bin/env python3
"""Select longer-relation correction and completed-pool coverage on validation.

Baseline is the previous serialized sentence model on its original displayed
pool. Trial inputs are bounded confidence-eligible completed candidates, before
the display cutoff. Heldout outcomes are never used in this selection.
"""
import argparse
import base64
import gzip
import json
from pathlib import Path
import struct

from evaluate_sentence_ranker import evaluate
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT
from train_sentence_ranker import encode, encode_additive, correction
from sentence_features import long_features

DATA = ROOT / 'tools/data/sentence_search'


def decode(path):
    data = memoryview(gzip.decompress(base64.b64decode(path.read_bytes())))
    magic, count, schema, strength, limit = struct.unpack_from('>IIIff', data)
    if magic != 0x53524b32 or limit != 3: raise ValueError('Incorrect baseline model')
    at=20; weights={}
    for _ in range(count):
        size=struct.unpack_from('>H',data,at)[0];at+=2
        key=bytes(data[at:at+size]).decode();at+=size
        weights[key]=struct.unpack_from('>f',data,at)[0];at+=4
    if at!=len(data): raise ValueError('Trailing data')
    return weights,strength,schema


def select(weights_path, baseline_asset, baseline_scored, trial_scored, output, additive=False, regression=None):
    protocol=json.loads((DATA/'protocol.json').read_text())
    old,strength,schema=decode(baseline_asset)
    before=evaluate(old,baseline_scored,strength,output/'before',role_schema=schema)
    weights=json.loads(weights_path.read_text())
    # Also isolate coverage from feature/data changes.
    coverage=evaluate(old,trial_scored,strength,output/'coverage-only',role_schema=schema)
    cached={}
    for line in trial_scored.read_text().splitlines():
        f=line.split('\t')
        for value in f[5].split('|'):
            key=(f[1],value)
            if not value or key in cached:continue
            if additive:
                local=correction(old,*key,strength,schema)
                longer=sum(min(2,count)*weights.get(k,0) for k,count in long_features(*key).items())
                cached[key]=(local,max(-1.5,min(1.5,longer)))
            else:cached[key]=(0,correction(weights,*key,1,3))
    trials={s:evaluate(weights,trial_scored,strength if additive else s,output/'validation',role_schema=3,
            long_strength=s if additive else None,
            corrections={k:v[0]+(max(0,s*v[1]-.1) if additive else s*v[1]) for k,v in cached.items()}) for s in protocol['strength_grid']}
    expected={'authored60','natural200','public200','new100'}
    if set(before)!=expected or any(set(t)!=expected for t in trials.values()):
        raise ValueError('Wrong validation cases')
    eligible=[s for s in trials if all(trials[s][n][k]>=before[n][k]
              for n in before for k in ('top1','top5','top20'))]
    validation_eligible=list(eligible)
    if regression is not None:
        allowed=json.loads(regression.read_text())['eligible_strengths']
        eligible=[s for s in eligible if s in allowed]
    selected=max(eligible,key=lambda s:(sum(t['mrr'] for t in trials[s].values()),-s)) if eligible else None
    report={'baseline':before,'coverage_only':coverage,'trials':trials,
            'eligible_strengths':eligible,'selected_strength':selected,'role_schema':3,
            'validation_eligible_strengths':validation_eligible,
            'regression_calibration_sha256':digest(regression) if regression is not None else None,
            'additive':additive,'baseline_strength':strength,
            'weights_sha256':digest(weights_path),'baseline_asset_sha256':digest(baseline_asset),
            'baseline_scored_sha256':digest(baseline_scored),'trial_scored_sha256':digest(trial_scored),
            'protocol_sha256':digest(DATA/'protocol.json'),
            'selection':'Written before viewing the reserved heldout100 outcomes. Existing evaluations are development/regression evidence.'}
    output.mkdir(parents=True,exist_ok=True)
    (output/'selection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if selected is not None:
        (output/'sentence_ranker.b64').write_bytes(encode_additive(weights,strength,selected) if additive else encode(weights,selected,3))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('weights','baseline_asset','baseline_scored','trial_scored','output'):p.add_argument(name,type=Path)
    p.add_argument('--additive',action='store_true')
    p.add_argument('--regression',type=Path)
    a=p.parse_args();r=select(a.weights,a.baseline_asset,a.baseline_scored,a.trial_scored,a.output,a.additive,a.regression)
    print(json.dumps(r,ensure_ascii=False,indent=2))
