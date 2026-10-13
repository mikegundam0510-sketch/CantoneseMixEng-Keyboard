"""Bounded, deterministic whole-candidate features shared with SentenceRanker.java.

No full sentence is a feature: local surfaces have 2..4 characters; skipped
relations join two characters within five positions; boundary/role relations
share evidence across words. These are evidence, not grammatical prohibitions.
"""
from collections import Counter

# Explicit shared blocks keep feature extraction identical on older Android/JDK
# Unicode tables; candidates in newer CJK extensions must not reset history.
HAN_RANGES = ((0x3400,0x4DBF),(0x4E00,0x9FFF),(0xF900,0xFAFF),
              (0x2E80,0x2E99),(0x2E9B,0x2EF3),(0x2F00,0x2FD5),
              (0x3005,0x3005),(0x3007,0x3007),(0x3021,0x3029),(0x3038,0x303B),
              (0x16FE2,0x16FE3),(0x16FF0,0x16FF1),(0x20000,0x2A6DF),
              (0x2A700,0x2B73F),(0x2B740,0x2B81F),(0x2B820,0x2CEAF),
              (0x2CEB0,0x2EBEF),(0x2EBF0,0x2EE5F),(0x2F800,0x2FA1F),
              (0x30000,0x3134F),(0x31350,0x323AF),(0x323B0,0x3347F))


def han(c):
    cp = ord(c)
    return any(start <= cp <= end for start, end in HAN_RANGES)

MARKERS = frozenset('我你佢係唔冇未有咗緊過會可要想就先再都又嘅啊呀喎呢嗎啦喇囉啲')
ACTIONS = frozenset('交還送借收寄傳發派覆帶留印睇試改做查問諗學聽講寫讀用打幫去返買飲食整揀拎攞玩行坐瞓等識知開關洗煮賣換記着著搵揾')
ACTION_WORDS = frozenset(('繼續','完善','改善','修改','調整','檢查','研究','練習','試用',
                          '更新','確認','提供','處理','解釋','補充','輸入','打字','安排',
                          '完成','幫手','返工','收工','食飯','買嘢','搭車','收到','知道'))


def unit_role(unit):
    if unit in ACTION_WORDS or len(unit) == 1 and unit in ACTIONS: return 'X'
    return role(unit) if len(unit) == 1 else 'O'


def anchored(unit):
    return unit in ACTION_WORDS or len(unit) == 1 and unit in MARKERS | ACTIONS


def long_features(context, text):
    """Relate short lexical units across up to12 Han positions, never a sentence."""
    history = ''
    for c in context:
        history = (history + c)[-12:] if han(c) else ''
    result = Counter()
    for c in text:
        if not han(c):
            history = ''; continue
        right_units = [c] + ([history[-1] + c] if history else [])
        for distance in range(2, min(12, len(history)) + 1):
            at = len(history) - distance
            left_units = [history[at]] + ([history[at-1:at+1]] if at > 0 else [])
            bucket = 's' if distance <= 3 else 'm' if distance <= 7 else 'l'
            for left in left_units:
                for right in right_units:
                    if not (anchored(left) or anchored(right)): continue
                    result[f'L|{left}|{bucket}|{right}'] += 1
                    result[f'J|{unit_role(left)}|{bucket}|{unit_role(right)}'] += 1
        history = (history + c)[-12:]
    return result


def role(c, schema=2):
    if c in '我你佢': return 'P'
    if c in '唔冇未': return 'N'
    if c in '咗緊過': return 'A'
    if c in '嘅啊呀喎呢嗎啦喇囉': return 'T'
    if c in '係有會可要想': return 'V'
    if schema >= 2 and c in '就先再都又': return 'M'
    if schema >= 2 and c == '啲': return 'B'
    return 'O'


def features(context, text, role_schema=2):
    history = ''
    for c in context:
        history = (history + c)[-12:] if han(c) else ''
    initial = not history
    history = history[-5:]
    result = Counter()
    for c in text:
        if not han(c):
            history = ''
            continue
        window = history + c
        for n in range(2, min(4, len(window)) + 1):
            result['W|' + window[-n:]] += 1
        for distance in range(2, min(5, len(history)) + 1):
            previous = history[-distance]
            if previous in MARKERS or c in MARKERS:
                result[f'K|{previous}|{distance}|{c}'] += 1
                result[f'R|{role(previous, role_schema)}|{distance}|{role(c, role_schema)}'] += 1
        history = window[-5:]
    first = ''
    for c in text:
        if not han(c): break
        first += c
    if initial:
        for n in range(1, min(3, len(first)) + 1):
            result['S|' + first[:n]] += 1
    tail = ''
    for c in text:
        tail = (tail + c)[-3:] if han(c) else ''
    for n in range(1, len(tail) + 1):
        result['E|' + tail[-n:]] += 1
    if initial and len(first) == len(text) and first:
        bucket = 's' if len(first) <= 4 else 'm' if len(first) <= 8 else 'l'
        result[f'D|{role(first[0], role_schema)}|{bucket}|{role(first[-1], role_schema)}'] += 1
        if first[0] in MARKERS:
            result[f'H|{first[0]}|{bucket}|{role(first[-1], role_schema)}'] += 1
    if role_schema >= 3:
        result.update(long_features(context, text))
    # Repetition is not treated as several independent observations of a relation.
    return Counter({f: min(2, count) for f, count in result.items()})
