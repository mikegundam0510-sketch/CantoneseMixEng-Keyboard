#!/usr/bin/env python3
"""Train frozen weights, select on validation, then run post-selection guards.

Writes experimental models/results outside the app. Never installs a model,
changes a version, or creates an APK. Requires javac/java and Python stdlib.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_tatoeba_corpus import digest, load_training
from train_phrase_model import ROOT, ASSETS


def metrics(path):
    ranks = [int(line.split('\t')[3]) for line in path.read_text().splitlines()]
    return {'cases': len(ranks), 'top1': sum(r == 1 for r in ranks),
            'top5': sum(0 < r <= 5 for r in ranks), 'top20': sum(r > 0 for r in ranks),
            'mrr': sum(1 / r for r in ranks if r > 0) / len(ranks)}


def run(args):
    data = ROOT / 'tools/data/tatoeba_corpus'
    _, manifest = load_training(data)
    for split in ('validation', 'heldout'):
        if digest(data / (split + '.tsv')) != manifest['splits'][split]['cases_sha256']:
            raise ValueError('Evaluation cases changed')
    protocol = json.loads((data / 'protocol.json').read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    classes = output / 'classes'
    subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(ROOT / 'app/src/main/java'),
                    '-d', str(classes), str(ROOT / 'tools/RankingEvaluation.java')], check=True)
    base_command = [sys.executable, str(ROOT / 'tools/train_language_model.py'), str(args.corpus),
                    str(args.cantonese), '--training-assets', str(args.training_assets)]
    original = output / 'reproduced-original'
    with (output / 'reproduction.log').open('w') as log:
        subprocess.run(base_command + ['--output', str(original)], stdout=log, check=True)
    if digest(original / 'language_model.b64') != digest(ASSETS / 'language_model.b64'):
        raise ValueError('Original bundled model not reproduced; do not confound changes')
    assets = {0: ASSETS}
    for weight in protocol['additional_family_weights']:
        model = output / f'model-{weight}'
        with (output / f'train-{weight}.log').open('w') as log:
            subprocess.run(base_command + ['--output', str(model), '--extra-corpus', str(data),
                                          '--extra-weight', str(weight)], stdout=log, check=True)
        stage = output / f'assets-{weight}'
        stage.mkdir(exist_ok=True)
        for source in ASSETS.iterdir():
            if source.is_file():
                target = stage / source.name
                if not target.exists():
                    target.symlink_to(source.resolve())
        # Replacing a local symlink does not modify the app's files.
        target = stage / 'language_model.b64'
        target.unlink()
        shutil.copy2(model / 'language_model.b64', target)
        assets[weight] = stage

    def evaluate(weight, name, cases):
        result = output / f'{name}-{weight}.tsv'
        subprocess.run(['java', '-Xmx1g', '-cp', str(classes),
                        'hk.cantonesemixeng.keyboard.RankingEvaluation', str(assets[weight]),
                        str(cases), str(result)], check=True)
        return metrics(result)

    selection_sets = {
        'tatoeba': data / 'validation.tsv',
        'natural': ROOT / 'tools/data/candidate_ranking/validation.tsv',
        'authored': ROOT / 'tools/data/hk_chat_cases/validation.tsv',
    }
    scores = {w: {name: evaluate(w, 'validation-' + name, path)
                  for name, path in selection_sets.items()} for w in assets}
    eligible = [w for w in assets if all(scores[w][name][metric] >= scores[0][name][metric]
                for name in selection_sets for metric in ('top1', 'top5'))]
    selected = max(eligible, key=lambda w: (sum(r['mrr'] for r in scores[w].values()), -w))
    decision = {'validation': scores, 'eligible_weights': eligible, 'selected_weight': selected}
    # Persist decision BEFORE looking at heldout or guard outcomes.
    (output / 'selection.json').write_text(json.dumps(decision, indent=2) + '\n')
    guard_sets = {
        'tatoeba_heldout': data / 'heldout.tsv',
        'natural200': ROOT / 'tools/data/candidate_ranking/heldout.tsv',
        'authored120': ROOT / 'tools/data/hk_chat_cases/heldout.tsv',
        'old600': ROOT / 'tools/data/word_ranking/old600.tsv',
        'daily32': ROOT / 'tools/hk_daily_context_cases.tsv',
        'completion16': ROOT / 'tools/hk_completion_cases.tsv',
    }
    guards = {w: {name: evaluate(w, name, path) for name, path in guard_sets.items()}
              for w in dict.fromkeys((0, selected))}
    failures = [name + ':' + metric for name in guard_sets if name != 'authored120'
                for metric in ('top1', 'top5') if guards[selected][name][metric] < guards[0][name][metric]]
    report = dict(decision, baseline_revision=manifest['baseline_revision'],
                  corpus_manifest_sha256=digest(data / 'manifest.json'),
                  protocol_sha256=digest(data / 'protocol.json'), guards=guards,
                  guard_failures=failures, eligible_for_adoption=selected != 0 and not failures,
                  bundled_model_sha256=digest(ASSETS / 'language_model.b64'),
                  experimental_models={w: {'sha256': digest(assets[w] / 'language_model.b64'),
                    'report': json.loads((output / f'model-{w}/MODEL_REPORT.json').read_text())}
                    for w in assets if w},
                  note='No experimental model is copied into app assets. No APK, release or real-device test.')
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'selected_weight': selected, 'guard_failures': failures,
                      'eligible_for_adoption': report['eligible_for_adoption']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('cantonese', type=Path)
    parser.add_argument('training_assets', type=Path)
    parser.add_argument('output', type=Path)
    run(parser.parse_args())
