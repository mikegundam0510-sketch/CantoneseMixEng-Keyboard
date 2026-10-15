#!/usr/bin/env python3
"""Assess the four frozen structured trials; never open the reserved500 here."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
from evaluate_joint_ranking import assess
from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_phrase_model import ROOT
from train_structured_ranking import RESEARCH,read_reconstructed

def report(work,output):
    _,protocol=read_reconstructed();previous=ROOT/'tools/reports/joint-ranking-2026-10-15'
    cases=previous/'calibration800.tsv';before=previous/'baseline800.tsv'
    output.mkdir(parents=True,exist_ok=True);results=[]
    for config in protocol['trial_grid']:
        l2=config['l2'];strength=config['strength'];name=f'{round(l2*1000):03}-{strength:g}'
        original=work/f'cal-{name}.tsv';saved=output/f'cal-{name}.tsv'
        shutil.copyfile(original,saved)
        result=assess(cases,before,saved,output/f'cal-{name}.json')
        results.append(dict(config,name=name,qualified=result['qualified'],selection_key=result['selection_key'],
            before=result['before'],after=result['after'],new100=result['new100'],old700=result['old700'],
            gate=result['calibration_gate'],output_sha256=digest(saved)))
    def key(r):return (*r['selection_key'],-r['strength'],r['l2'])
    passed=[r for r in results if r['qualified']]
    selection=dict(protocol_sha256=digest(RESEARCH/'protocol.json'),
        cases_sha256=digest(cases),baseline_output_sha256=digest(before),results=results,
        qualified=[r['name'] for r in passed],selected=max(passed,key=key)['name'] if passed else None,
        best_research=max(results,key=key)['name'],reserve500_opened=False,
        decision='Continue only selected arm to guards and then frozen independent test.' if passed else
            'Reject all four arms. Preserve production app and unopened reserve500. No extra grid expansion.')
    (RESEARCH/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n')
    punctuation=Counter();omitted=Counter()
    for s in (RESEARCH/'audit.tsv').read_text().splitlines():
        f=s.split('\t')
        if f[13]=='false':punctuation.update(set(c for c in f[3] if not han(c)))
        omitted.update({segment.rsplit(':',2)[1] for segment in f[12].split('|') if segment.endswith(':false')})
    diagnosis=dict(non_han_targets_by_character=punctuation.most_common(),
        omitted_segments_by_target=omitted.most_common(),
        limits='Omitted segments are from one diagnostic best path; frequency is not a count of all possible failure causes. Historical TRAIN labels, not user typing telemetry.')
    (output/'data-diagnosis.json').write_text(json.dumps(diagnosis,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'qualified':selection['qualified'],'selected':selection['selected'],'best_research':selection['best_research']}))
    return selection

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();report(a.work,a.output)
