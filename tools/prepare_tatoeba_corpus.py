#!/usr/bin/env python3
"""Freeze licensed Tatoeba-only sentences from the pinned Jyut Dictionary release.

The database also contains differently licensed dictionaries. Never export all
Yue rows: only sentences linked to the named Tatoeba source may enter this corpus.
No network, private messages, automatic translations, or synthetic sentences.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from train_language_model import chunks, corpus
from train_phrase_model import ROOT, ASSETS, reverse_codes

DB_SHA256 = 'e03a9259bb2ca8b58a6a2b4324a4e473490b00334491c16f340a1f097b007718'
ZIP_SHA256 = '74649c089f4a31b44c32c9aa1632f31a4f5d769e980baf9a86fdb1518272409e'
RELEASE = 'https://github.com/aaronhktan/jyut-dict/releases/tag/v4.25.0623-release'
# A conservative style filter, not a language identifier or quality guarantee.
CANTONESE = set('佢哋唔冇嘅咗喺嗰呢咁嚟咩啲嘢睇攞俾畀嘥瞓嘞喎㗎噉搵鍾咦嘈啱')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def surface(text):
    # Used only for deduplication; training keeps punctuation and Latin boundaries.
    return ''.join(c.casefold() for c in text if c.isalnum())


def read_source(connection):
    row = connection.execute("SELECT source_id,version,legal,link FROM sources "
                             "WHERE sourcename='Tatoeba—Cantonese-English'").fetchall()
    if len(row) != 1 or row[0][1] != '2023-04-08' or 'CC BY 2.0 FR' not in row[0][2]:
        raise ValueError('Unrecognized Tatoeba source attribution')
    records = {}
    for ident, text, translation in connection.execute(
            'SELECT c.chinese_sentence_id,c.traditional,l.fk_non_chinese_sentence_id '
            'FROM chinese_sentences c JOIN sentence_links l '
            'ON l.fk_chinese_sentence_id=c.chinese_sentence_id '
            "WHERE c.language='yue' AND l.fk_source_id=? ORDER BY c.chinese_sentence_id",
            (row[0][0],)):
        record = records.setdefault(ident, {'id': str(ident), 'text': normalize(text), 'links': set()})
        record['links'].add(str(translation))
    return list(records.values())


def group_records(records):
    """Connected components: shared translations, exact chunks, one-edit variants.

    Deletion signatures deliberately overgroup some short minimal pairs. Group
    before sampling and keep every member in one split. No random row split.
    """
    parents = list(range(len(records)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    def union(a, b):
        a, b = root(a), root(b)
        parents[max(a, b)] = min(a, b)

    seen = {}
    for i, record in enumerate(records):
        keys = {'translation:' + t for t in record['links']}
        texts = {surface(record['text'])} | {s for s in chunks(record['text']) if len(s) >= 6}
        for text in texts:
            keys.add('text:' + text)
            if 6 <= len(text) <= 64:
                # Equal deletion signatures cover substitutions as well as insertions.
                keys.add('edit:' + text)
                keys.update('edit:' + text[:at] + text[at + 1:] for at in range(len(text)))
        for key in sorted(keys):
            if key in seen:
                union(i, seen[key])
            else:
                seen[key] = i
    members = defaultdict(list)
    for i, record in enumerate(records):
        members[root(i)].append(record['id'])
    groups = {r: hashlib.sha256(('tatoeba-family-v1:' + ','.join(sorted(ids))).encode()).hexdigest()
              for r, ids in members.items()}
    return [dict(record, group=groups[root(i)]) for i, record in enumerate(records)]


def split_for(group):
    bucket = int(group[:8], 16) % 10
    return 'heldout' if bucket == 0 else 'validation' if bucket == 1 else 'train'


def overlap_index(texts):
    index = defaultdict(set)
    for text in texts:
        if len(text) >= 6:
            for at in range(len(text) - 5):
                index[text[at:at + 6]].add(text)
    return index


def overlaps(text, index):
    candidates = set()
    for at in range(len(text) - 5):
        candidates.update(index.get(text[at:at + 6], ()))
    return any(text in prior or prior in text for prior in candidates)


def prepare(database, hkcancor, output):
    if digest(database) != DB_SHA256:
        raise ValueError('Jyut Dictionary database checksum mismatch')
    old = json.loads((ASSETS / 'MODEL_REPORT.json').read_text())
    if digest(hkcancor) != old['source_sha256']['hkcancor_zip']:
        raise ValueError('HKCanCor checksum mismatch')
    protected_paths = sorted(set((ROOT / 'tools/data').rglob('*.tsv')) |
                             set((ROOT / 'tools').glob('*cases.tsv')) |
                             {ROOT / 'tools/lm_heldout_cases.tsv'})
    protected_paths = [p for p in protected_paths if p.exists() and output not in p.parents
                       and 'tatoeba_corpus' not in p.parts]
    protected = {text for _, text in corpus(hkcancor)}
    for path in protected_paths:
        for line in path.read_text().splitlines():
            fields = line.split('\t')
            if len(fields) >= 3:
                protected.update(chunks(fields[0] + fields[2]))
                protected.update(chunks(fields[2]))
    index = overlap_index(protected)
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        source = read_source(conn)
    # Group before filtering, so removing a bridge sentence cannot split its family.
    grouped = group_records(source)
    reverse = reverse_codes()
    rejected = Counter()
    pools = {s: [] for s in ('train', 'validation', 'heldout')}
    seen_texts = set()
    for record in grouped:
        text = record['text']
        parts = chunks(text)
        if not 6 <= sum(map(len, parts)) <= 64 or not any(c in CANTONESE for c in text):
            rejected['length_or_no_colloquial_marker'] += 1
            continue
        if re.search(r'https?://|www\.|@|\[|\]|<|>|\ufffd', text):
            rejected['markup_or_identifier'] += 1
            continue
        if any(overlaps(part, index) for part in parts):
            rejected['existing_corpus_or_regression_overlap'] += 1
            continue
        if surface(text) in seen_texts:
            rejected['duplicate_surface'] += 1
            continue
        seen_texts.add(surface(text))
        record['links'] = sorted(record['links'])
        pools[split_for(record['group'])].append(record)
    output.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for split, rows in pools.items():
        rows.sort(key=lambda r: (r['group'], r['id']))
        path = output / (split + '.jsonl')
        path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows))
        # At most one reachable complete Han segment per family, no synthetic context.
        by_group = {}
        for row in rows:
            for text in chunks(row['text']):
                if 6 <= len(text) <= 16 and all(c in reverse for c in text):
                    code = ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)
                    item = (hashlib.sha256((row['id'] + ':' + text).encode()).hexdigest(), row['id'], code, text)
                    if row['group'] not in by_group or item < by_group[row['group']]:
                        by_group[row['group']] = item
        cases = sorted(by_group.values())[:200]
        case_path = output / (split + '.tsv')
        case_path.write_text(''.join('\t' + code + '\t' + text + '\n' for _, _, code, text in cases))
        metadata[split] = {'rows': len(rows), 'groups': len({r['group'] for r in rows}),
                           'sha256': digest(path), 'cases': len(cases), 'cases_sha256': digest(case_path),
                           'case_record_ids': [r[1] for r in cases]}
    manifest = {
        'schema': 1, 'source': 'Tatoeba Cantonese via Jyut Dictionary',
        'release': RELEASE, 'zip_sha256': ZIP_SHA256, 'database_sha256': DB_SHA256,
        'snapshot': '2023-04-08', 'license': 'CC-BY-2.0-FR',
        'license_url': 'https://creativecommons.org/licenses/by/2.0/fr/',
        'credit': 'Tatoeba contributors; redistributed by Aaron H. K. Tan / Jyut Dictionary',
        'baseline_revision': 'f6034031c4215a06d11ebec30fcdf43499f28182',
        'source_rows': len(source), 'rejected': dict(rejected), 'splits': metadata,
        'protected_files': {str(p.relative_to(ROOT)): digest(p) for p in protected_paths},
        'hkcancor_sha256': digest(hkcancor),
        'selection': 'NFC/whitespace only; 6..64 Han and a colloquial marker; preserve Latin/punctuation. '
                     'Exclude substring overlaps >=6 with prior corpus/cases. Group shared translations, '
                     'identical chunks and deletion-signature variants before hash 80/10/10 split. '
                     'Cases: <=200 SHA-sorted groups/split; one Han chunk 6..16 per group.',
        'limitations': 'Community examples, not HK chat frequency. Snapshot date is not sentence creation date. '
                      'Authors and original speaker groups unavailable; record IDs belong to redistributed DB. '
                      'Original simplified text may have been converted to traditional by distributor. '
                      'Heuristics do not eliminate every paraphrase or prove grammatical quality. '
                      'Mixed English text is retained, but evaluated Han chunks are not whole mixed sentences.'
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def load_training(directory):
    """Reject edited files, duplicate text and family leakage before counting."""
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('database_sha256') != DB_SHA256:
        raise ValueError('Unrecognized corpus manifest')
    owners, training = {}, []
    for split in ('train', 'validation', 'heldout'):
        path = directory / (split + '.jsonl')
        if digest(path) != manifest['splits'][split]['sha256']:
            raise ValueError('Corpus split checksum mismatch: ' + split)
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if split_for(row['group']) != split:
                raise ValueError('Family assigned to incorrect split')
            keys = ['group:' + row['group']] + ['text:' + s for s in chunks(row['text']) if len(s) >= 6]
            for key in keys:
                if key in owners and owners[key] != split:
                    raise ValueError('Corpus leakage between splits')
                owners[key] = split
            if split == 'train':
                training.append(row)
    return training, manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('hkcancor', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.database, args.hkcancor, args.output), ensure_ascii=False, indent=2))
