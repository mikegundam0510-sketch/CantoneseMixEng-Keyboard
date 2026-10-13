#!/usr/bin/env python3
"""Calibrate previously inspected regressions, before opening the next reserve."""
import argparse
import json
from pathlib import Path

from evaluate_sentence_ranker import evaluate
from select_sentence_search import decode, DATA
from sentence_features import long_features
from train_sentence_ranker import correction
from prepare_tatoeba_corpus import digest


def evaluate_grid(weights_path,base_asset,base_scored,trial_scored,output):
    old,base,schema=decode(base_asset);weights=json.loads(weights_path.read_text())
    before=evaluate(old,base_scored,base,output/'before',role_schema=schema)
    cached={}
    for line in trial_scored.read_text().splitlines():
        f=line.split('\t')
        for text in f[5].split('|'):
            key=(f[1],text)
            if not text or key in cached:continue
            local=correction(old,*key,base,schema)
            longer=sum(min(2,count)*weights.get(k,0) for k,count in long_features(*key).items())
            cached[key]=(local,max(-1.5,min(1.5,longer)))
    grid=json.loads((DATA/'protocol.json').read_text())['strength_grid']
    trials={s:evaluate(weights,trial_scored,base,output/'trials',role_schema=3,long_strength=s,
        corrections={k:v[0]+max(0,s*v[1]-.1) for k,v in cached.items()}) for s in [0]+grid}
    required=('old600','natural200','authored120','daily32','completion16','handover')
    eligible=[s for s in grid if all(trials[s][n][k]>=before[n][k]
               for n in required if n in before for k in ('top1','top5'))]
    report={'before':before,'trials':trials,'eligible_strengths':eligible,
        'trial_scored_sha256':digest(trial_scored),'protocol_sha256':digest(DATA/'protocol.json'),
        'use':'Previously inspected guards are now calibration/regression data; selection must precede the unused reserve2 outcomes.'}
    output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Eligible regression strengths:',eligible)
    for s in trials:print(s,{n:tuple(trials[s][n][k] for k in ('top1','top5','top20')) for n in required if n in before})
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('weights','base_asset','base_scored','trial_scored','output'):p.add_argument(n,type=Path)
    a=p.parse_args();evaluate_grid(a.weights,a.base_asset,a.base_scored,a.trial_scored,a.output)
