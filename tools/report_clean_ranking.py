#!/usr/bin/env python3
"""Assess the two frozen clean-data configurations; reserve500 is never decoded."""
import argparse
import json
from pathlib import Path
import shutil
from evaluate_joint_ranking import assess
from prepare_clean_ranking import DATA
from prepare_tatoeba_corpus import digest
from report_prefix_retrieval import compare
from train_phrase_model import ROOT

def report(work,output):
    protocol=json.loads((DATA/'protocol.json').read_text());manifest=json.loads((DATA/'manifest.json').read_text())
    if digest(DATA/'manifest.json')!=protocol['manifest_sha256'] or digest(DATA/'train.tsv')!=protocol['training_sha256']:
        raise ValueError('Frozen clean data changed')
    for name,sha in protocol['source_sha256'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Frozen clean implementation changed')
    previous=ROOT/'tools/reports/joint-ranking-2026-10-15';cases=previous/'calibration800.tsv';before=previous/'baseline800.tsv'
    output.mkdir(parents=True,exist_ok=True);results=[]
    for config in protocol['trial_grid']:
        l2=config['l2'];name=f'{round(l2*1000):03}';saved=output/f'cal-{name}.tsv'
        shutil.copyfile(work/f'cal-{name}.tsv',saved)
        result=assess(cases,before,saved,output/f'cal-{name}.json')
        old=ROOT/f'tools/reports/structured-training-2026-10-15/cal-{name}-0.5.tsv'
        increment=compare(cases,old,saved);increment['baseline_revision']='previous rejected structured research at identical L2/strength; calibration only'
        (output/f'increment-{name}.json').write_text(json.dumps(increment,ensure_ascii=False,indent=2)+'\n')
        results.append(dict(config,name=name,qualified=result['qualified'],selection_key=result['selection_key'],
            before=result['before'],after=result['after'],new100=result['new100'],old700=result['old700'],
            gate=result['calibration_gate'],previous_same_configuration=increment['before'],output_sha256=digest(saved)))
    def key(r):return (*r['selection_key'],r['l2'])
    passed=[r for r in results if r['qualified']]
    selection=dict(protocol_sha256=digest(DATA/'protocol.json'),cases_sha256=digest(cases),baseline_sha256=digest(before),
        results=results,qualified=[r['name'] for r in passed],selected=max(passed,key=key)['name'] if passed else None,
        best_research=max(results,key=key)['name'],reserve500_decoded=False,
        decision='Continue only the selected configuration to guards, then independent500.' if passed else
            'Reject both configurations. Preserve production and unopened reserve500. Do not expand this grid.')
    (DATA/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:selection[k] for k in ('qualified','selected','best_research')}));return selection

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();report(a.work,a.output)
