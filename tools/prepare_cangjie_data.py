"""Merge pinned Cangjie 5 HK completion mappings without removing legacy codes.

Run from any directory. Optional --inputs points at a directory containing
base.yaml, Cangjie5_HK.txt and LICENSE for a reproducible offline build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
BASE_REV = '52d90a1b1312e74042b38c1cbc8142defbc53171'
HK_REV = 'e4a4242f518ab0d34066bbd8aa44cb0cefd61db2'
SOURCES = {
    'base.yaml': (f'https://raw.githubusercontent.com/rime/rime-cangjie/{BASE_REV}/cangjie5.base.dict.yaml',
                  '8690f2ad8aafd38780846881aa916b5779e6d9247a351a1da426d3f3257afca4'),
    'Cangjie5_HK.txt': (f'https://raw.githubusercontent.com/Jackchows/Cangjie5/{HK_REV}/Cangjie5_HK.txt',
                       'fdbbc0af05a289d88f2ab3ceae12f5a4f0bd54966cbb0c4c8f34145246194314'),
    'LICENSE': (f'https://raw.githubusercontent.com/Jackchows/Cangjie5/{HK_REV}/LICENSE',
                'cf2746abe0b37ba14fb0e735eb868d418e4d335b9040887f579da958f95ffa77'),
}

def mappings(text):
    for line in text.splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and len(fields[0]) == 1 and re.fullmatch('[a-z]{1,5}', fields[1]):
            yield fields[0], fields[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path)
    args = parser.parse_args()
    inputs = {}
    for name, (url, digest) in SOURCES.items():
        data = (args.inputs / name).read_bytes() if args.inputs else urllib.request.urlopen(url, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'{name}: checksum mismatch')
        inputs[name] = data
    base = inputs['base.yaml'].decode('utf-8')
    old = set(mappings(base))
    combined = set(old)
    added = []
    for row in mappings(inputs['Cangjie5_HK.txt'].decode('utf-8')):
        if row not in combined:
            combined.add(row)
            added.append(row)
    if len(combined) < 130000:
        raise ValueError('Incomplete merged dictionary')
    output = base.rstrip() + '\n\n# Cangjie5 HK completion mappings (MIT); see licenses/cangjie-completion.\n'
    output += ''.join(f'{word}\t{code}\n' for word, code in added)
    (ASSETS / 'cangjie5.base.dict.yaml').write_text(output, encoding='utf-8')
    notices = ASSETS / 'licenses/cangjie-completion'
    notices.mkdir(parents=True, exist_ok=True)
    (notices / 'LICENSE.txt').write_bytes(inputs['LICENSE'])
    report = {
        'sources': [{'url': url, 'sha256': digest} for url, digest in SOURCES.values()],
        'base_revision': BASE_REV, 'completion_revision': HK_REV,
        'base_mappings': len(old), 'added_mappings': len(added),
        'mappings': len(combined), 'characters': len({word for word, _ in combined}),
        'output_sha256': hashlib.sha256(output.encode('utf-8')).hexdigest(),
        'processing': 'Keep all original mappings and candidate order; append unique HK completion mappings, '
                      'including alternative regional forms and supplementary-plane characters. '
                      'Quick indexes are derived at runtime. Glyph display depends on device fonts.'
    }
    (notices / 'SOURCE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('base_mappings', 'added_mappings', 'mappings', 'characters')}))

if __name__ == '__main__':
    main()
