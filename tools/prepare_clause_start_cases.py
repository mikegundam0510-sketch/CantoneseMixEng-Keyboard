#!/usr/bin/env python3
"""Freeze authored clause/context probes and previously unused public-corpus families.

Authored probes share constructions but separate verb/object families. They are
regression/generalization tests, not independent measurements of HK chat usage.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from prepare_tatoeba_corpus import digest, load_training
from train_language_model import chunks
from train_phrase_model import ROOT, reverse_codes

DATA = ROOT / 'tools/data/clause_start'
PUBLIC = ROOT / 'tools/data/tatoeba_corpus'
FAMILIES = {
    'validation': [('洗', '衫'), ('煮', '飯'), ('買', '餸'), ('寄', '包裹'),
                   ('改', '密碼'), ('開', '燈'), ('關', '門'), ('帶', '鎖匙')],
    'heldout': [('借', '書'), ('還', '車'), ('搬', '屋'), ('整理', '文件'),
                ('付', '款'), ('取消', '預約'), ('簽', '合約'), ('換', '電池')],
}


def write_cases(path, rows, reverse):
    output = []
    for source, context, text in rows:
        if not all(c in reverse for c in text):
            raise ValueError('Unreachable case: ' + text)
        code = ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)
        if len(code) > 48 or len(context) > 12:
            raise ValueError('Case exceeds decoder bounds')
        output.append(context + '\t' + code + '\t' + text + '\n')
    path.write_text(''.join(output))
    return {'cases': len(rows), 'sha256': digest(path), 'sources': [r[0] for r in rows]}


def prepare(output=DATA):
    _, public_manifest = load_training(PUBLIC)
    reverse = reverse_codes()
    output.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for split, families in FAMILIES.items():
        rows = []
        for verb, obj in families:
            stem = verb + '咗' + obj
            family = split + ':' + verb + ':' + obj
            for context, text in [('', '你' + stem + '未'), ('', '你哋' + stem + '未'),
                                  ('', '係我' + stem), ('我唔記得', '係' + stem + '未'),
                                  ('你話', '係佢' + stem), ('我想問', '你' + stem + '未'),
                                  ('', '你啱啱' + stem + '未'), ('你今日', stem + '未')]:
                rows.append((family, context, text))
        identities = ['你係老師', '佢係同事', '我係學生', '你哋係朋友',
                      '我係香港人', '佢係醫生'] if split == 'validation' else [
                      '你係司機', '佢係護士', '我係工程師', '你哋係同學',
                      '我係負責人', '佢係警察']
        for text in identities:
            rows.append((split + ':identity:' + text, '', text))
        metadata[split] = write_cases(output / (split + '.tsv'), rows, reverse)
    # Exclude entire families represented by the 200 public cases decoded earlier.
    records = [json.loads(line) for line in (PUBLIC / 'heldout.jsonl').read_text().splitlines()]
    old_ids = set(public_manifest['splits']['heldout']['case_record_ids'])
    excluded_groups = {r['group'] for r in records if r['id'] in old_ids}
    groups = defaultdict(list)
    for row in records:
        if row['group'] in excluded_groups:
            continue
        for text in chunks(row['text']):
            if 6 <= len(text) <= 16 and all(c in reverse for c in text):
                groups[row['group']].append((row['id'], text))
    rows = []
    for group in sorted(groups, key=lambda g: hashlib.sha256(('clause-start-v1:' + g).encode()).hexdigest())[:100]:
        ident, text = min(groups[group], key=lambda r: hashlib.sha256((r[0] + r[1]).encode()).hexdigest())
        rows.append((group + ':' + ident, '', text))
    metadata['prospective_public'] = write_cases(output / 'prospective_public.tsv', rows, reverse)
    manifest = {'baseline_revision': 'e4387bfef96be601b264feb5617e15e0ad0fea81',
                'public_manifest_sha256': digest(PUBLIC / 'manifest.json'),
                'excluded_previous_public_groups': sorted(excluded_groups),
                'sets': metadata,
                'limits': 'Authored construction families are correlated; identities are protective regressions. '
                          'Prospective public sample excludes all previously decoded heldout families, '
                          'but authors are unavailable and external dictionaries may contain its words.'}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
