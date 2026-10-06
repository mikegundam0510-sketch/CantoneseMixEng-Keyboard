#!/usr/bin/env python3
"""Check legacy Chinese codec repertoires; not a Microsoft IME code-table audit."""
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]

def dictionary_characters():
    characters = set()
    body = False
    for line in (ROOT / 'app/src/main/assets/cangjie5.base.dict.yaml').read_text(encoding='utf-8').splitlines():
        if line == '...':
            body = True
            continue
        fields = line.split('\t')
        if body and not line.startswith('#') and len(fields) >= 2 and re.fullmatch('[a-z]{1,5}', fields[1]):
            characters.add(fields[0])
    return characters

def codec_characters(codec):
    characters = set()
    for lead in range(0x81, 0xff):
        for trail in range(0x40, 0xff):
            try:
                text = bytes((lead, trail)).decode(codec)
            except UnicodeDecodeError:
                continue
            if len(text) == 1 and 'CJK' in unicodedata.name(text, ''):
                characters.add(text)
    return characters

if __name__ == '__main__':
    available = dictionary_characters()
    report = {}
    for codec in ('cp950', 'big5hkscs'):
        expected = codec_characters(codec)
        missing = expected - available
        report[codec] = {'cjk_characters': len(expected), 'missing': sorted(missing)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(item['missing'] for item in report.values()):
        raise SystemExit('Chinese character coverage regression')
