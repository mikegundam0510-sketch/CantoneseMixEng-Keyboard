#!/usr/bin/env python3
"""Reproduce readable phrase/emoji assets from pinned, attributed upstream data.

Usage: python tools/prepare_language_data.py /path/to/essay.txt /path/to/emoji-test.txt
Essay revision: 054920de4f54c9e5994276a96a4fc2a35cb51aa3 (rime/rime-essay, LGPL-3.0).
Emoji source: https://www.unicode.org/Public/emoji/15.1/emoji-test.txt (Unicode License).
"""
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
reverse = {}
for line in (ASSETS / 'cangjie5.base.dict.yaml').read_text().splitlines():
    f = line.split('\t')
    if len(f) < 2 or len(f[0]) != 1 or not re.fullmatch('[a-z]{1,5}', f[1]):
        continue
    code = f[1] if len(f[1]) == 1 else f[1][0] + f[1][-1]
    reverse.setdefault(f[0], set()).add(code)

weights = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    f = line.split('\t')
    if len(f) == 2 and 1 <= len(f[0]) <= 8 and all(c in reverse for c in f[0]):
        weights[f[0]] = max(1, int(f[1]))
# Explicitly authored Hong Kong everyday vocabulary. These are hand-set priorities.
hk = ('你好嗎 你好 早晨 晚安 多謝 唔該 唔該晒 多謝晒 對唔住 唔好意思 冇問題 冇所謂 '
      '冇嘢 唔使 唔使客氣 唔緊要 唔知道 知道 知唔知 係咪 唔係 係呀 係喎 係囉 '
      '好呀 好啦 好嘅 好嗎 好似 好彩 好靚 好正 好攰 好忙 好熱 好凍 好肚餓 '
      '我哋 你哋 佢哋 佢嘅 我嘅 你嘅 嗰個 呢個 嗰啲 呢啲 嗰度 呢度 邊個 邊度 '
      '喺度 喺邊 喺屋企 返工 放工 返屋企 出門口 搭車 搭地鐵 食飯 食咗飯未 '
      '食咗 飲茶 飲嘢 等陣 等陣先 陣間 一陣間 聽日 尋日 琴日 今日 今晚 '
      '幾時 點解 點樣 點算 咁樣 咁多 咁少 真係 梗係 得閒 得唔得 可以嗎 '
      '可以 唔可以 香港 九龍 新界 將軍澳 屯門 元朗 荃灣 銅鑼灣 旺角 尖沙咀 '
      '我愛你 我想 你想 佢想 我係 你係 佢係 我喺 你喺 佢喺 我要 你要 佢要 '
      '唔記得 記得 收到 明白 冇錯 冇時間 唔得 得啦 得嘅 唔洗 客氣 再見 拜拜').split()
for word in hk:
    if all(c in reverse for c in word):
        weights[word] = max(weights.get(word, 0), 30000 if len(word) > 2 else 12000)
singles = [(w, n) for w, n in weights.items() if len(w) == 1]
phrases = sorted(((w, n) for w, n in weights.items() if len(w) > 1), key=lambda x: (-x[1], x[0]))[:80000]
rows = []
for word, count in singles + phrases:
    variants = [sorted(reverse[c], key=lambda s: (len(s), s)) for c in word]
    for parts in itertools.islice(itertools.product(*variants), 16):
        rows.append((''.join(parts), word, count))
rows = sorted(set(rows))
with (ASSETS / 'quick_phrases.tsv').open('w') as out:
    out.write('# Rime Essay-derived Quick vocabulary; LGPL-3.0. See licenses/ESSAY-AUTHORS.txt.\n')
    for code, word, count in rows:
        out.write(f'{code}\t{word}\t{count}\n')

group = ''
emoji = []
for line in Path(sys.argv[2]).read_text().splitlines():
    if line.startswith('# group: '): group = line[9:]
    m = re.match(r'^([0-9A-F ]+)\s*;\s*fully-qualified\s*#\s*\S+\s+E[\d.]+\s+(.+)$', line)
    if m:
        symbol = ''.join(chr(int(cp, 16)) for cp in m[1].split())
        emoji.append((group, symbol, m[2]))
with (ASSETS / 'emoji.tsv').open('w') as out:
    out.write('# Unicode Emoji 15.1, fully-qualified sequences. Copyright Unicode, Inc.\n')
    for fields in emoji: out.write('\t'.join(fields) + '\n')
print(json.dumps({'phrase_entries':len(rows),'phrases':len(phrases),'emoji':len(emoji),'groups':len(set(e[0] for e in emoji))}))
