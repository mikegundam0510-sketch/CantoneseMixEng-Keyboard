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
hk_extra = ['食咗咩', '食咩', '食咗未', '飲咗', '食完', '食緊', '做咗', '做緊', '做完', '睇咗', '睇緊', '睇完', '去咗', '去邊', '去過', '買咗', '買嘢', '有咩', '冇咩', '咩事', '點呀', '點樣', '點做', '今日', '今次', '今朝', '今晚', '聽朝', '聽晚', '下晝', '夜晚', '最近', '時間', '日期', '工作', '公司', '同事', '會議', '文件', '報告', '資料', '數據', '更新', '確認', '安排', '處理', '完成', '提供', '收到', '通知', '謝謝', '多謝', '唔該', '麻煩', '請問', '請你', '請確認', '請提供', '需要', '可以', '應該', '已經', '未有', '未能', '暫時', '之後', '之前', '現在', '今天', '明天', '昨天', '如果', '因為', '所以', '但是', '不過', '另外', '目前', '問題', '情況', '結果', '建議', '申請', '檢查', '檢測', '監測', '環境', '空氣', '質素', '健康', '指數', '濃度', '每日', '每月', '每年', '數字', '圖表', '比較', '地址', '電話', '電郵', '聯絡', '香港', '港人', '繁體', '中文', '英文', '返工', '放工', '返嚟', '返去', '過嚟', '過去', '喺邊', '喺度', '係咪', '唔係', '你哋', '我哋', '佢哋', '呢個', '嗰個', '邊個', '呢度', '嗰度', '邊度', '好呀', '好啦', '好嘅', '得閒', '冇問題', '唔緊要', '唔知道', '知唔知', '幾時', '點解']
hk_extra += ['我今日', '我聽日', '我尋日', '我今晚', '我而家', '我已經', '我可能', '我最近', '你今日', '你聽日', '你尋日', '你今晚', '你而家', '你已經', '你可能', '你最近', '佢今日', '佢聽日', '佢尋日', '佢今晚', '佢而家', '佢已經', '佢可能', '佢最近', '我哋今日', '我哋聽日', '我哋尋日', '我哋今晚', '我哋而家', '我哋已經', '我哋可能', '我哋最近', '你哋今日', '你哋聽日', '你哋尋日', '你哋今晚', '你哋而家', '你哋已經', '你哋可能', '你哋最近', '佢哋今日', '佢哋聽日', '佢哋尋日', '佢哋今晚', '佢哋而家', '佢哋已經', '佢哋可能', '佢哋最近', '今日食', '今日飲', '今日去', '今日返', '今日做', '今日睇', '今日買', '今日收到', '今日完成', '今日處理', '今日更新', '今日確認', '聽日食', '聽日飲', '聽日去', '聽日返', '聽日做', '聽日睇', '聽日買', '聽日收到', '聽日完成', '聽日處理', '聽日更新', '聽日確認', '尋日食', '尋日飲', '尋日去', '尋日返', '尋日做', '尋日睇', '尋日買', '尋日收到', '尋日完成', '尋日處理', '尋日更新', '尋日確認', '今晚食', '今晚飲', '今晚去', '今晚返', '今晚做', '今晚睇', '今晚買', '今晚收到', '今晚完成', '今晚處理', '今晚更新', '今晚確認', '而家食', '而家飲', '而家去', '而家返', '而家做', '而家睇', '而家買', '而家收到', '而家完成', '而家處理', '而家更新', '而家確認', '已經食', '已經飲', '已經去', '已經返', '已經做', '已經睇', '已經買', '已經收到', '已經完成', '已經處理', '已經更新', '已經確認', '可能食', '可能飲', '可能去', '可能返', '可能做', '可能睇', '可能買', '可能收到', '可能完成', '可能處理', '可能更新', '可能確認', '最近食', '最近飲', '最近去', '最近返', '最近做', '最近睇', '最近買', '最近收到', '最近完成', '最近處理', '最近更新', '最近確認']
hk_extra += ['食唔食', '飲唔飲', '去唔去', '做唔做', '睇唔睇', '買唔買', '返唔返', '係唔係', '有冇', '得唔得', '可唔可以', '好唔好', '請問', '今日食', '今日飲', '今日做', '食完未', '食咗未']
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

# Preserve the base vocabulary; supplement it with explicitly authored HK fragments.
with (ASSETS / 'character_frequencies.tsv').open('w') as out:
    out.write('# Derived single-character counts from pinned Rime Essay vocabulary (LGPL-3.0).\n')
    for word, count in sorted(singles): out.write(f'{word}\t{count}\n')
hk_rows = set()
for word in hk_extra:
    if not all(c in reverse for c in word): continue
    variants = [sorted(reverse[c], key=lambda s: (len(s), s)) for c in word]
    for parts in itertools.islice(itertools.product(*variants), 16):
        hk_rows.add((''.join(parts), word, 30000 if len(word) > 2 else 12000))
with (ASSETS / 'hk_phrases.tsv').open('w') as out:
    out.write('# Authored Hong Kong vocabulary and clause fragments; hand-set priorities, not measured frequencies.\n')
    for code, word, count in sorted(hk_rows): out.write(f'{code}\t{word}\t{count}\n')

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

