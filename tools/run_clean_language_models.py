#!/usr/bin/env python3
"""Stage three frozen primary-model ablations and assess ordinary native lists."""
import argparse
import json
from pathlib import Path
import shutil

from evaluate_joint_ranking import assess
from native_phrase_relations import build, run
from prepare_tatoeba_corpus import digest
from train_clean_language_models import DATA, write_json
from train_phrase_model import ROOT

BASELINE='b5b084fa043724f38913a8042b47ffcd551330e8'
CAL=ROOT/'tools/reports/joint-ranking-2026-10-15/calibration800.tsv'
BEFORE=ROOT/'tools/reports/joint-ranking-2026-10-15/baseline800.tsv'
ARMS=('character','word','combined')


def check_protocol():
    p=json.loads((DATA/'protocol.json').read_text())
    if digest(DATA/'manifest.json')!=p['manifest_sha256']: raise ValueError('Training manifest changed')
    for name,value in p['source_sha256'].items():
        if digest(ROOT/name)!=value: raise ValueError('Frozen source changed: '+name)
    for name,value in p['evaluation_sha256'].items():
        if digest(ROOT/name)!=value: raise ValueError('Evaluation cases/output changed: '+name)
    return p


def prepare(work, models):
    check_protocol()
    if work.exists(): raise ValueError('Use a fresh native archive directory')
    work.mkdir(parents=True)
    base=work/'baseline';build(base,BASELINE,original=True)
    # Ordinary cached baseline outputs must match newly compiled plain inference.
    inputs=CAL.read_text().splitlines();expected=BEFORE.read_text().splitlines()
    indices=list(range(0,len(inputs),40))
    sample=work/'baseline-parity-cases.tsv';sample.write_text(''.join(inputs[i]+'\n' for i in indices))
    result=work/'baseline-parity.tsv';run(base,sample,result)
    if result.read_text().splitlines()!=[expected[i] for i in indices]: raise ValueError('Baseline cache parity failed')
    report=json.loads((models/'report.json').read_text())
    if report['protocol_sha256']!=digest(DATA/'protocol.json'): raise ValueError('Model protocol mismatch')
    mapping={'character':('language_model.b64',),'word':('phrase_model.b64',),'combined':('language_model.b64','phrase_model.b64')}
    hashes={}
    for arm,names in mapping.items():
        stage=work/arm;shutil.copytree(base,stage)
        for name in names:
            if digest(models/name)!=report['models'][name]: raise ValueError('Model bytes changed')
            shutil.copyfile(models/name,stage/'app/src/main/assets'/name)
        assets=stage/'app/src/main/assets'
        hashes[arm]={name:digest(assets/name) for name in ('language_model.b64','phrase_model.b64')}
    write_json(work/'staging.json',dict(protocol_sha256=digest(DATA/'protocol.json'),
        baseline_revision=BASELINE,baseline_parity_cases=len(indices),models=hashes))


def evaluate(work,arm,output):
    check_protocol()
    stage=json.loads((work/'staging.json').read_text())
    for name,value in stage['models'][arm].items():
        if digest(work/arm/'app/src/main/assets'/name)!=value: raise ValueError('Staged model changed')
    run(work/arm,CAL,output)


def report(work,results,output):
    check_protocol();scores={}
    for arm in ARMS:
        scores[arm]=assess(CAL,BEFORE,results/(arm+'.tsv'),results/(arm+'.json'))
    eligible=[a for a in ARMS if scores[a]['qualified']]
    selected=max(eligible,key=lambda a:(scores[a]['selection_key'],-ARMS.index(a))) if eligible else None
    value=dict(protocol_sha256=digest(DATA/'protocol.json'),models=json.loads((work/'staging.json').read_text())['models'],
        trials={a:{k:scores[a][k] for k in ('before','after','new100','old700','calibration_gate','selection_key','qualified')} for a in ARMS},
        selected=selected,independent500_decoded=False,
        decision='Proceed to frozen guards before reserve500' if selected else 'Reject all three; production assets unchanged; do not decode reserve500')
    write_json(output,value)
    print(json.dumps(dict(selected=selected,decision=value['decision'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    s=sub.add_parser('prepare');s.add_argument('work',type=Path);s.add_argument('models',type=Path)
    s=sub.add_parser('run');s.add_argument('work',type=Path);s.add_argument('arm',choices=ARMS);s.add_argument('output',type=Path)
    s=sub.add_parser('report');s.add_argument('work',type=Path);s.add_argument('results',type=Path);s.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work,a.models)
    elif a.mode=='run':evaluate(a.work,a.arm,a.output)
    else:report(a.work,a.results,a.output)
