#!/usr/bin/env python3
"""Fit an independent, bounded longer-relation correction over the prior model."""
import argparse
import json
from collections import Counter
from pathlib import Path

from prepare_tatoeba_corpus import digest
from select_sentence_search import decode, DATA
from sentence_features import long_features
from train_candidate_ranker import learn
from train_sentence_ranker import read_pairs, stored_weights, correction, encode_additive


def train(scored, baseline_asset, corpus, output):
    pairs,report=read_pairs(scored,corpus,DATA)
    old,strength,schema=decode(baseline_asset)
    adjusted=[]
    for source,context,code,gold,negative,margin in pairs:
        margin+=correction(old,context,gold,strength,schema)-correction(old,context,negative,strength,schema)
        adjusted.append((source,context,code,gold,negative,margin))
    p=json.loads((DATA/'protocol.json').read_text())['long_parameters']
    extractor=lambda c,t:Counter({k:min(2,v) for k,v in long_features(c,t).items()})
    weights,metrics=learn(adjusted,epochs=p['epochs'],rate=p['rate'],l2=p['l2'],
        min_count=p['minimum_independent_support'],maximum_features=p['maximum_features'],feature_extractor=extractor)
    weights=stored_weights(weights)
    if any(k in old for k in weights):raise AssertionError('Long/short feature channels overlap')
    merged={**old,**weights}
    output.mkdir(parents=True,exist_ok=True)
    (output/'weights.json').write_text(json.dumps(merged,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'sentence_ranker.b64').write_bytes(encode_additive(merged,strength,1))
    report.update({'algorithm':'Pairwise long-relation residual over unchanged previous short correction',
        'baseline_asset_sha256':digest(baseline_asset),'baseline_strength':strength,
        'baseline_feature_count':len(old),'long_feature_count':len(weights),'feature_count':len(merged),
        'training':metrics,'role_schema':3,'long_correction_limit':1.5,
        'baseline_revision':json.loads((DATA/'protocol.json').read_text())['baseline_revision'],
        'limitations':'Training objective approximates clipping. Long units have1..2 characters, shared action/marker roles and distance buckets through12 positions. They are statistical evidence, not a semantic parser. Earlier beam losses remain possible.'})
    (output/'SENTENCE_RANKER_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
    return merged,report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('scored','baseline_asset','corpus','output'):p.add_argument(name,type=Path)
    a=p.parse_args();train(a.scored,a.baseline_asset,a.corpus,a.output)
