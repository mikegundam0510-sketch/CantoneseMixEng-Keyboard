#!/usr/bin/env python3
"""Compare a fixed clause-prior grid and freeze a choice before guard evaluation.

No model is trained/installed here. The previous Tatoeba weight-2 trial is pinned
by its published work report. Provide the unchanged bundled baseline assets.
"""
import argparse
import json
from pathlib import Path
import subprocess

from evaluate_tatoeba_experiment import metrics
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

DATA = ROOT / 'tools/data/clause_start'


def choose(results):
    protocol = json.loads((DATA / 'protocol.json').read_text())
    scores = {}
    for model in ('bundled', 'trial'):
        scores[model] = {}
        for strength in [0] + protocol['strength_grid']:
            scores[model][strength] = {name: metrics(results / f'validation-{model}-{name}-{strength:g}.tsv')
                                      for name in ('authored', 'natural')}
    eligible = [s for s in protocol['strength_grid'] if all(
        scores[m][s][n][metric] >= scores[m][0][n][metric]
        for m in scores for n in ('authored', 'natural') for metric in ('top1', 'top5'))]
    selected = max(eligible, key=lambda s: (sum(scores[m][s][n]['mrr']
                   for m in scores for n in ('authored', 'natural')), -s)) if eligible else 0
    return {'scores': scores, 'eligible_strengths': eligible, 'selected_strength': selected}


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = output / 'results'
    results.mkdir(exist_ok=True)
    classes = output / 'classes'
    trial_report = json.loads((ROOT / 'tools/reports/tatoeba-corpus-work-2026-10-11.json').read_text())
    if digest(args.bundled / 'language_model.b64') != trial_report['bundled_model_sha256']:
        raise ValueError('Unchanged bundled baseline model required')
    if digest(args.trial / 'language_model.b64') != trial_report['experimental_models']['2']['sha256']:
        raise ValueError('Pinned previous Tatoeba trial model required')
    manifest = json.loads((DATA / 'manifest.json').read_text())
    for name, item in manifest['sets'].items():
        if digest(DATA / (name + '.tsv')) != item['sha256']:
            raise ValueError('Frozen clause cases changed')
    subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(ROOT / 'app/src/main/java'),
                    '-d', str(classes), str(ROOT / 'tools/RankingEvaluation.java')], check=True)
    assets = {'bundled': args.bundled, 'trial': args.trial}

    def evaluate(model, strength, name, cases):
        path = results / f'{name}-{model}-{strength:g}.tsv'
        subprocess.run(['java', '-Xmx1g', '-cp', str(classes),
                        'hk.cantonesemixeng.keyboard.RankingEvaluation', str(assets[model]),
                        str(cases), str(path), 'full', str(strength)], check=True)
        return metrics(path)

    protocol = json.loads((DATA / 'protocol.json').read_text())
    for model in assets:
        for strength in [0] + protocol['strength_grid']:
            for name, path in [('authored', DATA / 'validation.tsv'),
                               ('natural', ROOT / 'tools/data/candidate_ranking/validation.tsv')]:
                # Reproduce the filenames accepted by choose().
                evaluate(model, strength, 'validation-' + name, path)
                source = results / f'validation-{name}-{model}-{strength:g}.tsv'
                source.rename(results / f'validation-{model}-{name}-{strength:g}.tsv')
    decision = choose(results)
    (output / 'selection.json').write_text(json.dumps(decision, indent=2) + '\n')
    strength = decision['selected_strength']
    sets = {'authored70': DATA / 'heldout.tsv', 'prospective100': DATA / 'prospective_public.tsv',
            'old600': ROOT / 'tools/data/word_ranking/old600.tsv',
            'natural200': ROOT / 'tools/data/candidate_ranking/heldout.tsv',
            'authored120': ROOT / 'tools/data/hk_chat_cases/heldout.tsv',
            'daily32': ROOT / 'tools/hk_daily_context_cases.tsv',
            'completion16': ROOT / 'tools/hk_completion_cases.tsv',
            'tatoeba200': ROOT / 'tools/data/tatoeba_corpus/heldout.tsv'}
    guards = {model: {s: {name: evaluate(model, s, name, path) for name, path in sets.items()}
                      for s in dict.fromkeys((0, strength))} for model in assets}
    report = dict(decision, guards=guards, manifest_sha256=digest(DATA / 'manifest.json'),
                  protocol_sha256=digest(DATA / 'protocol.json'),
                  note='No assets are copied into the app; existing sets are diagnostic regressions.')
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundled', type=Path)
    parser.add_argument('trial', type=Path)
    parser.add_argument('output', type=Path)
    run(parser.parse_args())
