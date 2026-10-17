#!/usr/bin/env python3
"""One ordinary parent/candidate comparison after the visible-reranking guards."""
import argparse
import json
from pathlib import Path

from native_phrase_relations import run as baseline_run
from prepare_sentence_pretrain import write
from prepare_tatoeba_corpus import digest
from report_prefix_retrieval import compare
from run_visible_rerank import BASELINE, DATA, check, preserve, run
from train_phrase_model import ROOT

CASES = ROOT / 'tools/data/context_search/heldout.tsv'
RESULTS = ROOT / 'tools/reports/visible-rerank-2026-10-17'


def qualification():
    check()
    q = json.loads((DATA / 'qualification.json').read_text())
    if q['status'] != 'All pre-independent guards passed' or q['selected'] not in ('language', 'adapted'):
        raise ValueError('Candidate has not qualified')
    for name, wanted in {**q['source_sha256'], **q['evidence_sha256']}.items():
        if digest(ROOT / name) != wanted:
            raise ValueError('Frozen qualification changed: ' + name)
    if digest(CASES) != q['independent500_sha256'] or digest(Path(__file__)) != q['reserve_runner_sha256']:
        raise ValueError('Reserve cases/runner changed')
    return q


def evaluate(work, arm):
    q = qualification()
    for role, files in q['native_file_sha256'].items():
        stage = work / ('baseline' if role == 'baseline' else q['selected'])
        for name, wanted in files.items():
            if digest(stage / name) != wanted:
                raise ValueError('Frozen native file changed: ' + role + '/' + name)
    before = RESULTS / 'independent500-baseline.tsv'
    if arm == 'candidate':
        started = json.loads((DATA / 'reserve-started-baseline.json').read_text())
        if started['qualification_sha256'] != digest(DATA / 'qualification.json'):
            raise ValueError('Baseline was not run under this qualification')
        preserve(CASES, before, before)  # Require complete, ordered parent output.
    marker = DATA / ('reserve-started-' + arm + '.json')
    with marker.open('x') as stream:
        json.dump(dict(qualification_sha256=digest(DATA / 'qualification.json'),
                       cases_sha256=digest(CASES), arm=arm,
                       policy='One pass only; no unrecorded repeats or post-test tuning.'), stream, indent=2)
        stream.write('\n')
    if arm == 'baseline':
        baseline_run(work / 'baseline', CASES, before)
    else:
        run(work, q['selected'], CASES, before, RESULTS / 'independent500-candidate.tsv')


def report():
    q = qualification()
    before = RESULTS / 'independent500-baseline.tsv'
    after = RESULTS / 'independent500-candidate.tsv'
    value = compare(CASES, before, after)
    if value['before']['cases'] != 500:
        raise ValueError('Expected500 independent cases')
    value['baseline_revision'] = BASELINE
    value['selected'] = q['selected']
    value['coverage'] = preserve(CASES, before, after)
    value['independent_gate'] = dict(
        counts_nondecreasing=all(value['after'][k] >= value['before'][k] for k in ('top1', 'top5', 'top20')),
        first_or_top5_net_gain=any(value['after'][k] > value['before'][k] for k in ('top1', 'top5')))
    value['qualified'] = all(value['independent_gate'].values())
    value['substantial_gain'] = value['qualified'] and value['after']['top5'] - value['before']['top5'] >= 25
    value['qualification_sha256'] = digest(DATA / 'qualification.json')
    value['decision'] = ('Adopt exact validated reranker; no APK or1.0 claim' if value['qualified'] else
                         'Reject selected reranker; retain production; no reserve-based tuning')
    write(RESULTS / 'independent500.json', value)
    write(DATA / 'decision.json', {k: value[k] for k in (
        'baseline_revision', 'selected', 'before', 'after', 'coverage', 'independent_gate',
        'qualified', 'substantial_gain', 'qualification_sha256', 'decision')})
    print(json.dumps({k: value[k] for k in ('before', 'after', 'independent_gate', 'qualified', 'substantial_gain', 'decision')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    command = modes.add_parser('run')
    command.add_argument('work', type=Path)
    command.add_argument('arm', choices=('baseline', 'candidate'))
    modes.add_parser('report')
    args = parser.parse_args()
    if args.mode == 'run':
        evaluate(args.work, args.arm)
    else:
        report()
