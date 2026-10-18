"""Larger known regression gate before investing in the Java neural port."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from study import ROOT, DATA, WORK, REPORTS, sha, write, verify
sys.path.insert(0, str(ROOT / 'tools/code_generator'))
from model import load, Codec, decode
from report_prefix_retrieval import compare

CASES = ROOT / '.native/joint-ranking-20261015/guard-cases3893.tsv'
BEFORE = ROOT / 'tools/reports/pinned-head-2026-10-17/guard3893.tsv'


def check():
    verify()
    value = json.loads((DATA / 'guard-freeze.json').read_text())
    for name, wanted in value['sha256'].items():
        if sha(ROOT / name) != wanted:
            raise ValueError('Guard prediction changed: ' + name)


def prepare():
    verify()
    if not json.loads((DATA / 'selection.json').read_text())['selected']:
        raise ValueError('Calibration failed')
    paths = [Path(__file__), CASES, BEFORE, DATA / 'selection.json']
    paths += [ROOT / 'tools/code_generator' / name for name in ('model.py', 'common.py')]
    paths += [ROOT / 'tools/context_gru.py', ROOT / 'tools/sentence_language_model.py']
    frozen = json.loads((DATA / 'inference-freeze.json').read_text())
    mapping = {**frozen['sha256'], **{str(p.relative_to(ROOT)): sha(p) for p in paths}}
    write(DATA / 'guard-freeze.json', dict(
        sha256=mapping, purpose='Run the already-declared3893 regression guard before the expensive Java neural port. '
        'Same fixed policy/scorer/checkpoint. No changed gates, model fitting or independent evaluation. '
        'If regression fails, native neural port and later gates are unnecessary and remain unrun.'))


def generate(part):
    check()
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1':
        raise ValueError('Use the declared one-thread NumPy inference')
    v, characters = load(ROOT / 'tools/data/code_generator/models/teacher.npz')
    for a in v.values():
        a.setflags(write=False)
    codec = Codec(characters, json.loads((ROOT / 'tools/data/code_generator/codes.json').read_text()))
    rows = CASES.read_text().splitlines()
    pending = WORK / f'guard-generated-{part}.pending.tsv'
    output = WORK / f'guard-generated-{part}.tsv'
    if pending.exists() or output.exists():
        raise ValueError('Preserve completed/partial guard predictions')
    with pending.open('x') as out:
        for n in range(part, len(rows), 4):
            fields = rows[n].split('\t')
            # No target/rank goes into the generator or output.
            values = decode(v, codec, fields[2], fields[1], beam=24)
            out.write('\t'.join(fields[:3] + ['|'.join(t for t, score in values)]) + '\n')
            if ((n-part)//4+1) % 100 == 0:
                print('guard', part, 'generated', (n-part)//4+1, flush=True)
    pending.rename(output)


def evaluate():
    check()
    cases, old = [p.read_text().splitlines() for p in (CASES, BEFORE)]
    generated = [None] * len(cases)
    for part in range(4):
        shard = (WORK / f'guard-generated-{part}.tsv').read_text().splitlines()
        if len(shard) != len(cases[part::4]):
            raise ValueError('Partial generator output')
        generated[part::4] = shard
    inputs = WORK / 'guard-inputs.tsv'
    with inputs.open('x') as out:
        for case, parent, proposal in zip(cases, old, generated):
            c, b, g = case.split('\t'), parent.split('\t'), proposal.split('\t')
            if c != b[:4] or c[:3] != g[:3]:
                raise ValueError('Guard input identity differs')
            out.write('\t'.join(c[:3] + [b[5], g[3]]) + '\n')
    native = WORK / 'native'
    output = WORK / 'guard-predictions.tsv'
    if output.exists():
        raise ValueError('Preserve existing guard output')
    subprocess.run(['java', '-Xmx1g', '-cp', str(native / 'classes'),
                    'hk.cantonesemixeng.keyboard.NativeEvaluation', str(native / 'app/src/main/assets'),
                    str(inputs), str(output), str(REPORTS / 'guard-scores.tsv')], check=True)
    predictions = output.read_text().splitlines()
    if len(predictions) != len(cases):
        raise ValueError('Partial native guard output')
    after = REPORTS / 'guard3893.tsv'
    with after.open('x') as out:
        for case, prediction in zip(cases, predictions):
            c, p = case.split('\t'), prediction.split('\t')
            if c[:3] != p[:3]:
                raise ValueError('Native guard identity differs')
            texts = p[3].split('|') if p[3] else []
            rank = texts.index(c[3])+1 if c[3] in texts else 0
            out.write(case + '\t' + str(rank) + '\t' + p[3] + '\n')
    result = compare(CASES, BEFORE, after)
    result['baseline_revision'] = json.loads((DATA / 'protocol.json').read_text())['parent_revision']
    result['gates'] = dict(
        aggregate_first_top5_top20_nondecreasing=all(result['after'][k] >= result['before'][k] for k in ('top1','top5','top20')),
        each_set_first_top5_top20_nondecreasing=result['no_per_set_count_loss'],
        exact_first18_retained=True)
    result['qualified'] = all(result['gates'].values())
    result['known_regression_not_independent'] = True
    write(REPORTS / 'guard3893.json', result)
    print(json.dumps({k: result[k] for k in ('before','after','paired','gates','qualified')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare','generate','evaluate'])
    parser.add_argument('--part', type=int, choices=range(4))
    args = parser.parse_args()
    if args.mode == 'prepare': prepare()
    elif args.mode == 'evaluate': evaluate()
    elif args.part is None: parser.error('--part required')
    else: generate(args.part)
