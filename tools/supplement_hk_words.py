#!/usr/bin/env python3
"""Add authored daily vocabulary to the existing HK table without rebuilding other assets.

Uses the same bounded Quick-code variant generation as prepare_language_data.py.
Priorities are authored preferences, not measured corpus frequencies.
"""
import itertools
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
reverse = {}
for line in (ASSETS / 'cangjie5.base.dict.yaml').read_text().splitlines():
    f = line.split('\t')
    if len(f) >= 2 and len(f[0]) == 1 and re.fullmatch('[a-z]{1,5}', f[1]):
        code = f[1] if len(f[1]) == 1 else f[1][0] + f[1][-1]
        reverse.setdefault(f[0], set()).add(code)
original = (ASSETS / "hk_phrases.tsv").read_text()
rows = {}
additions = {}
for line in (ASSETS / 'hk_phrases.tsv').read_text().splitlines():
    f = line.split('\t')
    if len(f) == 3:
        key = (f[0], f[1])
        rows[key] = max(rows.get(key, 0), int(f[2]))
for word in (ROOT / 'tools/hk_daily_words.txt').read_text().splitlines():
    if not word or word.startswith('#'):
        continue
    if not all(c in reverse for c in word):
        raise ValueError('Missing character code: ' + word)
    variants = [sorted(reverse[c], key=lambda s: (len(s), s)) for c in word]
    for parts in itertools.islice(itertools.product(*variants), 16):
        key = (''.join(parts), word)
        priority = 30000 if len(word) > 2 else 12000
        if priority > rows.get(key, 0):
            rows[key] = priority
            additions[key] = priority
if additions:
    (ASSETS / 'hk_phrases.tsv').write_text(original.rstrip() + '\n\n'
        + '# Additional authored daily words and productive request/action vocabulary.\n'
        + ''.join(f'{code}\t{word}\t{priority}\n' for (code, word), priority in sorted(additions.items())))
