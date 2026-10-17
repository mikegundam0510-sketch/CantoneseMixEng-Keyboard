#!/usr/bin/env python3
"""Prepare private local caches of attributed text and same-code TRAIN pairs.

Common Voice asks users not to mirror its dataset. Only hashes, attribution and
preparation code are committed; the derived corpus containing its text stays in
an ignored native-work directory. No evaluation example supplies training text.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

from prepare_clean_ranking import rules, spans
from prepare_phrase_relations import gram_index, overlap
from prepare_tatoeba_corpus import digest
from train_clean_language_models import evaluation_exclusions
from train_phrase_model import ROOT
from sentence_features import han

DATA = ROOT / 'tools/data/sentence_pretrain'
CV_SHA = '645d6a544634db879cef9d38e13ce58b7cef91772ba4d2ae6f6f674dbeb02a8b'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def group(family):
    # Keep every authored scenario and every original dialogue together.
    if family.startswith('train:authored:train:'):
        return 'authored:' + family.split(':')[3]
    if family.startswith('train:daily:'):
        return 'daily:' + family.split(':')[2]
    return family


def split(family):
    if family.startswith('cv:'):
        return 'train'  # No author/conversation IDs; never pretend these are an independent test.
    return ('validation' if int(hashlib.sha256(('sentence-pretrain-v1:' + family).encode()).hexdigest()[:8], 16) % 10 == 0
            else 'train')


def prepare(cv, output):
    if output.exists():
        raise ValueError('Use a fresh cache directory')
    if digest(cv) != CV_SHA:
        raise ValueError('Common Voice pinned sentence source changed')
    mapping = rules()
    external, inputs = evaluation_exclusions(mapping)
    extra = [ROOT / 'tools/data/context_search' / (name + '.tsv') for name in ('validation', 'heldout')]
    texts = []
    for p in extra:
        inputs[str(p.relative_to(ROOT))] = digest(p)
        for line in p.read_text().splitlines():
            for field in line.split('\t'):
                texts.extend(t for _, _, t, _ in spans(field, mapping) if len(t) >= 6)
    # gram_index maps six-character anchors to complete texts.
    added = gram_index(texts)
    for length, values in added.items():
        external.setdefault(length, set()).update(values)
    base = ROOT / 'tools/data/clean_language_models/corpus.jsonl.gz'
    pairfile = ROOT / 'tools/data/current_search/pairs.jsonl.gz'
    inputs[str(base.relative_to(ROOT))] = digest(base)
    inputs[str(pairfile.relative_to(ROOT))] = digest(pairfile)
    corpus, pairs, rejected = [], [], Counter()
    seen = set()

    def add(family, domain, text, origin):
        family = group(family)
        if not 2 <= len(text) <= 48 or not all(han(c) for c in text):
            rejected['text_length_or_boundary'] += 1
            return
        if overlap(text, external):
            rejected['text_external_overlap'] += 1
            return
        key = (family, text)
        if key in seen:
            rejected['text_family_duplicate'] += 1
            return
        seen.add(key)
        corpus.append(dict(family=family, domain=domain, split=split(family), text=text, origin=origin))

    for r in map(json.loads, gzip.decompress(base.read_bytes()).decode().splitlines()):
        domain = r['domain']
        family = 'train:' + {'HK': 'hk', 'Tatoeba': 'tatoeba', 'authored': 'authored'}[domain] + ':' + r['family']
        add(family, domain, r['text'], r['origin'])
    for row in map(json.loads, gzip.decompress(pairfile.read_bytes()).decode().splitlines()):
        stage, family, context, code, positive, negative, margin, origin = row
        if stage != 'final':
            continue
        family = group(family)
        domain = ('HK' if family.startswith('train:hk:') else 'Tatoeba' if family.startswith('train:tatoeba:')
                  else 'UD' if family.startswith('train:ud:') else 'authored')
        if any(overlap(t, external) for t in (context + positive, context + negative)):
            rejected['pair_external_overlap'] += 1
            continue
        pairs.append(dict(family=family, domain=domain, split=split(family), context=context,
                          code=code, positive=positive, negative=negative,
                          offset=max(-4, min(4, margin)), origin=origin))
        # Full TRAIN positive text, never the rival, may supplement the LM corpus.
        add(family, domain, positive, dict(source='current_search:TRAIN-positive'))

    lines = cv.read_text().splitlines()
    parents = list(range(len(lines)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    def union(i, j):
        a, b = root(i), root(j)
        parents[max(a, b)] = min(a, b)
    signatures = {}
    for i, line in enumerate(lines):
        surface = ''.join(t for _, _, t, _ in spans(line, mapping))
        keys = {'full:' + surface}
        if 6 <= len(surface) <= 64:
            keys.update('delete:' + surface[:j] + surface[j+1:] for j in range(len(surface)))
        # Specific long shared spans group near duplicates; do not group by common short grammar.
        keys.update('long:' + surface[j:j+16] for j in range(max(0, len(surface)-15)))
        for key in sorted(keys):
            if key in signatures:
                union(i, signatures[key])
            else:
                signatures[key] = i
    cv_parts = [list(spans(line, mapping)) for line in lines]
    bad = {root(i) for i, parts in enumerate(cv_parts) if any(overlap(t, external) for _, _, t, _ in parts)}
    for i, parts in enumerate(cv_parts):
        if root(i) in bad:
            rejected['CV_external_overlap_rows'] += 1
            continue
        for start, end, text, changes in parts:
            add('cv:' + str(root(i)+1), 'CV', text, dict(line=i+1, start=start, end=end, changes=changes))

    # Internal validation is original-family disjoint in BOTH training stages.
    internal = gram_index([r['text'] for r in corpus if r['split'] == 'validation'] +
                          [r['context'] + r['positive'] for r in pairs if r['split'] == 'validation'])
    clean_corpus, clean_pairs = [], []
    bad_cv = {r['family'] for r in corpus if r['domain'] == 'CV' and overlap(r['text'], internal)}
    for r in corpus:
        if r['split'] == 'train' and (r['family'] in bad_cv or overlap(r['text'], internal)):
            rejected['text_internal_overlap'] += 1
        else:
            clean_corpus.append(r)
    for r in pairs:
        if r['split'] == 'train' and any(overlap(r['context'] + r[k], internal) for k in ('positive', 'negative')):
            rejected['pair_internal_overlap'] += 1
        else:
            clean_pairs.append(r)
    output.mkdir(parents=True)
    for name, rows in [('corpus', clean_corpus), ('pairs', clean_pairs)]:
        payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows).encode()
        (output / (name + '.jsonl.gz')).write_bytes(gzip.compress(payload, mtime=0))
    manifest = dict(parent_revision='1a6a67e', cv_revision='46407be8d4c5de28b62baf2b18a363ea461b3c4f',
                    cv_sha256=CV_SHA, cv_source_rows=len(lines), input_sha256=inputs,
                    corpus_sha256=digest(output/'corpus.jsonl.gz'), pairs_sha256=digest(output/'pairs.jsonl.gz'),
                    corpus={s: dict(Counter(r['domain'] for r in clean_corpus if r['split'] == s)) for s in ('train', 'validation')},
                    pairs={s: dict(Counter(r['domain'] for r in clean_pairs if r['split'] == s)) for s in ('train', 'validation')},
                    characters={s: sum(len(r['text']) for r in clean_corpus if r['split'] == s) for s in ('train', 'validation')},
                    families={s: len({r['family'] for r in clean_corpus if r['split'] == s}) for s in ('train', 'validation')},
                    rejected=dict(rejected),
                    policy='NFC/six reviewed glyph pairs; split all non-Han boundaries. Fixed original TRAIN conversations/translations only. Internal split by conversation/translation/scenario family shared across both stages. Common Voice prompts have no author IDs: near-duplicate clusters, TRAIN only, no independence or dialogue claim. Exclude external evaluation6+ and internal validation6+ from TRAIN. No Common Voice raw/derived text cache mirrored in Git.',
                    pairs_note='Current-parent actual full TRAIN rivals from3aa8870; app tree equals1a6a67e. Historical raw/final min offset clipped[-4,4]. Same-code adaptation, not new independent examples.')
    write(output/'manifest.json', manifest)
    print(json.dumps({k:manifest[k] for k in ('corpus','pairs','characters','families','rejected')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('common_voice', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    prepare(a.common_voice, a.output)
