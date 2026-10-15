#!/usr/bin/env python3
"""Merge ordinary selected-model shards and apply the frozen3893 guard."""
import argparse
import json
from pathlib import Path

from report_prefix_retrieval import compare
from run_clean_language_models import BASELINE, check_protocol
from train_clean_language_models import write_json


def report(shards,output):
    check_protocol()
    cases=Path('.native/joint-ranking-20261015/guard-cases3893.tsv')
    baseline=Path('.native/joint-ranking-20261015/baseline3893.tsv')
    inputs=cases.read_text().splitlines()
    rows=[None]*len(inputs)
    for part in range(4):
        expected=inputs[part::4]
        if (shards/f'cases-{part}.tsv').read_text().splitlines()!=expected:
            raise ValueError('Shard input changed')
        values=(shards/f'output-{part}.tsv').read_text().splitlines()
        if len(values)!=len(expected):raise ValueError('Partial guard output')
        for at,line in enumerate(values):rows[part+4*at]=line
    if any(r is None for r in rows):raise ValueError('Incomplete guard merge')
    output.mkdir(parents=True,exist_ok=True)
    merged=output/'guard3893.tsv';merged.write_text(''.join(r+'\n' for r in rows))
    result=compare(cases,baseline,merged);result['baseline_revision']=BASELINE
    result['guard_gate']=dict(
        aggregate_counts_nondecreasing=all(result['after'][k]>=result['before'][k] for k in ('top1','top5','top20')),
        per_set_first_top5_loss_within_one_percentage_point=all(
            all(g['before'][k]-g['after'][k]<=g['before']['cases']*.01+1e-9 for k in ('top1','top5'))
            for g in result['per_set'].values()))
    result['qualified']=all(result['guard_gate'].values())
    write_json(output/'guard3893.json',result)
    print(json.dumps({k:result[k] for k in ('before','after','guard_gate','qualified')}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('shards',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();report(a.shards,a.output)
