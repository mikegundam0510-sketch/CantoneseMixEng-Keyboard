#!/usr/bin/env python3
"""Freeze public-corpus splits, then extract baseline exact-code competitors.

No validation or held-out sentence contributes a positive or a negative. The
existing natural set is now diagnostic data; a new deterministic sample is kept
out of model selection. Authored families remain in their original splits.
"""
import argparse
import hashlib
import json
from pathlib import Path

from train_phrase_model import ASSETS, ROOT, reverse_codes, scenarios, segmented_corpus

BASELINE = 'ba77b772d751b15ec702bc7e5479122b70822d64'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(corpus, output):
    report = json.loads((ASSETS / 'MODEL_REPORT.json').read_text())
    if digest(corpus) != report['source_sha256']['hkcancor_zip']:
        raise ValueError('Corpus checksum mismatch')
    reverse = reverse_codes()
    authored = scenarios()
    authored_texts = {s: {''.join(w) for _, w in rows} for s, rows in authored.items()}
    excluded = set((ROOT / 'tools/data/hk_chat_cases/prior_targets.txt').read_text().splitlines())
    for path in (ROOT / 'tools/data/hk_chat_cases').glob('*.tsv'):
        for line in path.read_text().splitlines():
            fields = line.split('\t')
            if len(fields) >= 3:
                excluded.add(fields[2])
    excluded = {s for s in excluded if len(s) >= 4}
    held = set(report['heldout_conversation_files'])
    validation = set(report['validation_conversation_files'])
    pools = {s: {} for s in ('train', 'validation', 'heldout')}
    # A text is assigned only once even when a conversation repeats it.
    all_rows = sorted(segmented_corpus(corpus))
    split_texts = {s: {''.join(w) for f, w in all_rows
                      if (f in held if s == 'heldout' else f in validation)}
                   for s in ('validation', 'heldout')}
    for name, words in all_rows:
        text = ''.join(words)
        split = 'heldout' if name in held else 'validation' if name in validation else 'train'
        if not 6 <= len(text) <= 16 or not all(c in reverse for c in text):
            continue
        if split == 'train' and text in split_texts['validation'] | split_texts['heldout']:
            continue
        if split == 'validation' and text in split_texts['heldout']:
            continue
        if any(text in authored_texts[s] for s in authored_texts if s != split):
            continue
        if split != 'train' and any(old in text or text in old for old in excluded):
            continue
        code = ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)
        if len(code) <= 48:
            pools[split].setdefault(text, (name, '', code, text))
    output.mkdir(parents=True, exist_ok=True)
    sizes = {'train': 1500, 'validation': 200, 'heldout': 200}
    metadata = {}
    for split in sizes:
        rows = sorted(pools[split].values(), key=lambda r: hashlib.sha256(
            ('contrastive-v1:' + r[0] + r[3]).encode()).hexdigest())[:sizes[split]]
        natural = list(rows)
        # Use separate authored heldout file, so natural results remain interpretable.
        if split == 'train':
            for family, words in authored[split]:
                text = ''.join(words)
                code = ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)
                rows.append((family, '', code, text))
        path = output / (split + '.tsv')
        path.write_text(''.join('\t'.join(row[1:]) + '\n' for row in rows))
        metadata[split] = {'cases': len(rows), 'natural_cases': len(natural),
                           'case_sha256': digest(path), 'sources': [r[0] for r in rows]}
    manifest = {
        'baseline_revision': BASELINE,
        'selection': 'Full Han utterance chunks 6..16 chars, exact canonical Quick code; '
                     'SHA256(contrastive-v1:+filename+text), first1500/200/200; '
                     'new validation/heldout exclude prior target substring in either direction',
        'source_sha256': {'hkcancor_zip': digest(corpus),
                          'authored_scenarios': digest(ROOT / 'tools/data/hk_chat_scenarios.json')},
        'allowed_sources': sorted({f for f, _ in all_rows if f not in held | validation}) +
                           sorted({f for f, _ in authored['train']}),
        'excluded_sources': sorted(held | validation) + sorted({f for s in ('validation', 'heldout')
                                                              for f, _ in authored[s]}),
        'splits': metadata,
        'limitation': 'Public historical speech, not modern real-user chats. Conversation files '
                      'were used before; new utterances only. Authored variants are correlated '
                      'and are not measured use frequencies.',
        'release_gate': json.loads((ROOT / 'tools/data/hk_chat_cases/release_gate.json').read_text())
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def pairs(output, evaluation):
    manifest = json.loads((output / 'manifest.json').read_text())
    if manifest.get('baseline_revision') != BASELINE:
        raise ValueError('Unexpected baseline decoder revision')
    expected_sources = {
        'hkcancor_zip': json.loads((ASSETS / 'MODEL_REPORT.json').read_text())['source_sha256']['hkcancor_zip'],
        'authored_scenarios': digest(ROOT / 'tools/data/hk_chat_scenarios.json')}
    if manifest.get('source_sha256') != expected_sources:
        raise ValueError('Frozen training source checksum mismatch')
    if manifest['splits']['train']['case_sha256'] != digest(output / 'train.tsv'):
        raise ValueError('Frozen training case checksum mismatch')
    allowed = set(manifest['allowed_sources'])
    excluded = set(manifest['excluded_sources'])
    if not allowed or allowed & excluded:
        raise ValueError('Overlapping training/excluded source lists')
    lines = evaluation.read_text().splitlines()
    cases = (output / 'train.tsv').read_text().splitlines()
    sources = manifest['splits']['train']['sources']
    if len(lines) != len(cases) or len(sources) != len(cases):
        raise ValueError('Evaluation does not match frozen training cases')
    result = []
    reachable = 0
    for source, case, line in zip(sources, cases, lines):
        fields = line.split('\t')
        if len(fields) != 5 or '\t'.join(fields[:3]) != case or source not in allowed or source in excluded:
            raise ValueError('Mismatched training row/source')
        context, code, positive = fields[:3]
        reachable += int(fields[3]) > 0
        candidates = [s for s in fields[4].split('|') if s]
        rank = int(fields[3])
        # Train mostly against real errors, with one easier competitor to retain
        # calibration when the baseline already chose the correct sentence.
        negatives = candidates[:min(10, rank - 1)] if rank else candidates[:10]
        if rank and rank < len(candidates):
            negatives.append(candidates[rank])
        result.extend('\t'.join((source, context, code, positive, negative)) for negative in negatives)
    path = output / 'pairs.tsv'
    path.write_text('\n'.join(result) + '\n')
    manifest['pairs_sha256'] = digest(path)
    manifest['training_evaluation_sha256'] = digest(evaluation)
    manifest['training_pairs'] = len(result)
    manifest['reachable_training_positives'] = reachable
    manifest['negative_selection'] = ('Up to ten incorrect displayed baseline candidates above gold '
                                      '(first ten if gold absent), plus one below gold for calibration. '
                                      'An unreachable exact-code gold is retained as a teacher positive; '
                                      'ranking alone cannot make it searchable.')
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path)
    args = parser.parse_args()
    report = pairs(args.output, args.evaluation) if args.evaluation else prepare(args.corpus, args.output)
    print(json.dumps({s: r['cases'] for s, r in report['splits'].items()} |
                     {'training_pairs': report.get('training_pairs')}, sort_keys=True))
