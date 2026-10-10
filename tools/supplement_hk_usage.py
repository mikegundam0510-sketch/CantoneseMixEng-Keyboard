#!/usr/bin/env python3
"""Import selected public Cantonese phrase weights; never use evaluation sentences."""
import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
REVISION = '259f0e48bba840c3a2e0d117539e96937f3d89bc'
SHA256 = 'd08836175f598219f43c2f2f9e12e12711212dbefe08d57b2eddb7a9d9f22a5d'

def supplement(source):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Unexpected Rime Cantonese source checksum')
    weights = dict((f[0], int(f[1])) for line in source.read_text().splitlines()
                   if len(f := line.split('\t')) == 2)
    reverse = {}
    for line in (ASSETS / 'cangjie5.base.dict.yaml').read_text().splitlines():
        f = line.split('\t')
        if len(f) >= 2 and len(f[0]) == 1 and re.fullmatch('[a-z]{1,5}', f[1]):
            code = f[1] if len(f[1]) == 1 else f[1][0] + f[1][-1]
            reverse.setdefault(f[0], set()).add(code)
    target = ASSETS / 'cantonese_phrases.tsv'
    original = target.read_text()
    existing = {}
    for line in original.splitlines():
        f = line.split('\t')
        if len(f) == 3:
            existing[f[0], f[1]] = max(existing.get((f[0], f[1]), 0), int(f[2]))
    additions, selected, absent = {}, {}, []
    for word in (ROOT / 'tools/hk_usage_terms.txt').read_text().splitlines():
        if not word or word.startswith('#'):
            continue
        if word not in weights or not 2 <= len(word) <= 6 or not all(c in reverse for c in word):
            absent.append(word)
            continue
        # Source weights are dictionary weights, not a modern chat frequency estimate.
        priority = min(3000, max(1, weights[word]))
        selected[word] = {'source_weight': weights[word], 'applied_weight': priority}
        variants = [sorted(reverse[c], key=lambda s: (len(s), s)) for c in word]
        for parts in itertools.islice(itertools.product(*variants), 8):
            key = (''.join(parts), word)
            if priority > existing.get(key, 0):
                additions[key] = priority
    if additions:
        target.write_text(original.rstrip() + '\n\n# Additional selected Rime Cantonese dictionary weights; CC BY 4.0. See licenses/hk-usage/SOURCE.json.\n'
            + ''.join(f'{code}\t{word}\t{value}\n' for (code, word), value in sorted(additions.items())))
    manifest = {'source': f'https://raw.githubusercontent.com/rime/rime-cantonese/{REVISION}/essay-cantonese.txt',
        'revision': REVISION, 'source_sha256': SHA256, 'upstream_revision_date': '2026-08-13',
        'authors': 'CanCLID and Rime Cantonese contributors; see https://github.com/rime/rime-cantonese',
        'license': 'CC BY 4.0; ../RIME-CANTONESE-CC-BY-4.0.txt',
        'transform': 'Curated daily terms; source weight capped at 3000; at most eight exact Quick-code variants; base entries retained',
        'terms': selected, 'not_in_frequency_source': absent,
        'note': 'Public dictionary weights, not measured Hong Kong chat frequencies. No evaluation sentences or personal text imported.'}
    directory = ASSETS / 'licenses/hk-usage'
    directory.mkdir(exist_ok=True)
    (directory / 'SOURCE.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'selected_terms={len(selected)} additional_rows={len(additions)} absent_terms={len(absent)}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    supplement(parser.parse_args().source)
