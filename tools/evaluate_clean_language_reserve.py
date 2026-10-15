#!/usr/bin/env python3
"""One ordinary baseline/candidate reserve pass after frozen qualification."""
import argparse
import json
from pathlib import Path

from native_phrase_relations import run
from prepare_tatoeba_corpus import digest
from report_prefix_retrieval import compare
from run_clean_language_models import check_protocol, BASELINE
from train_clean_language_models import DATA, write_json
from train_phrase_model import ROOT

CASES=ROOT/'tools/data/joint_ranking/heldout.tsv'
RESULTS=ROOT/'tools/reports/clean-language-models-2026-10-16'


def qualification():
    check_protocol()
    q=json.loads((DATA/'qualification.json').read_text())
    for name,value in {**q['source_sha256'],**q['evidence_sha256']}.items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen qualification changed: '+name)
    if q['selected']!='character' or digest(CASES)!=q['independent500_sha256']:
        raise ValueError('Selected model/cases changed')
    if digest(Path(__file__))!=q['reserve_runner_sha256']:
        raise ValueError('Reserve runner changed')
    return q


def evaluate(work,arm):
    q=qualification()
    stage=work/('baseline' if arm=='baseline' else 'character')
    for name,value in q['native_file_sha256'][arm].items():
        if digest(stage/name)!=value:raise ValueError('Frozen native file changed: '+name)
    marker=DATA/('reserve-started-'+arm+'.json')
    with marker.open('x') as stream:
        json.dump(dict(qualification_sha256=digest(DATA/'qualification.json'),
            source_model_freeze=True,cases_sha256=digest(CASES),arm=arm,
            policy='One pass only. This marker prevents an unrecorded repeat.'),stream,indent=2)
        stream.write('\n')
    run(stage,CASES,RESULTS/('independent500-'+arm+'.tsv'))


def report():
    qualification()
    value=compare(CASES,RESULTS/'independent500-baseline.tsv',RESULTS/'independent500-candidate.tsv')
    value['baseline_revision']=BASELINE
    value['independent_gate']=dict(
        counts_nondecreasing=all(value['after'][k]>=value['before'][k] for k in ('top1','top5','top20')),
        first_or_top5_net_gain=any(value['after'][k]>value['before'][k] for k in ('top1','top5')))
    value['qualified']=all(value['independent_gate'].values())
    value['qualification_sha256']=digest(DATA/'qualification.json')
    value['decision']='Adopt selected character model only; no APK or1.0 claim' if value['qualified'] else 'Reject selected model; retain production; no further reserve-based tuning'
    write_json(RESULTS/'independent500.json',value)
    write_json(DATA/'decision.json',{k:value[k] for k in ('baseline_revision','before','after','independent_gate','qualified','qualification_sha256','decision')})
    print(json.dumps({k:value[k] for k in ('before','after','independent_gate','qualified','decision')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    s=sub.add_parser('run');s.add_argument('work',type=Path);s.add_argument('arm',choices=('baseline','candidate'))
    sub.add_parser('report');a=p.parse_args()
    if a.mode=='run':evaluate(a.work,a.arm)
    else:report()
