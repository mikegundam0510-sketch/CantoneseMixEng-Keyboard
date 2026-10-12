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
    # Repetition is not treated as several independent observations of a relation.
    return Counter({f: min(2, count) for f, count in result.items()})
