"""Merge pinned Cangjie 5 HK completion mappings without removing legacy codes.

Run from any directory. Optional --inputs points at a directory containing
base.yaml, Cangjie5_HK.txt, cj3.txt, cj3-special.txt, LICENSE and LICENSE-CJ3
for a reproducible offline build.
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
CJ3_REV = '26a3e71f6328ab3aa0505304803bb8d8092ee785'
SOURCES = {
    'base.yaml': (f'https://raw.githubusercontent.com/rime/rime-cangjie/{BASE_REV}/cangjie5.base.dict.yaml',
                  '8690f2ad8aafd38780846881aa916b5779e6d9247a351a1da426d3f3257afca4'),
    'Cangjie5_HK.txt': (f'https://raw.githubusercontent.com/Jackchows/Cangjie5/{HK_REV}/Cangjie5_HK.txt',
                       'fdbbc0af05a289d88f2ab3ceae12f5a4f0bd54966cbb0c4c8f34145246194314'),
    'LICENSE': (f'https://raw.githubusercontent.com/Jackchows/Cangjie5/{HK_REV}/LICENSE',
                'cf2746abe0b37ba14fb0e735eb868d418e4d335b9040887f579da958f95ffa77'),
    'cj3.txt': (f'https://raw.githubusercontent.com/Arthurmcarthur/Cangjie3-Plus/{CJ3_REV}/cj3.txt',
                '1cd45efb3e434d625abbaa1f5017e14ebe932e5f93681c90312d265e04cc5147'),
    'cj3-special.txt': (f'https://raw.githubusercontent.com/Arthurmcarthur/Cangjie3-Plus/{CJ3_REV}/cj3-special.txt',
                        'b5b0f1e69ba8438bb2a640b013f60fe0ad778a46bd8601daa3ab68f1319f68df'),
    'LICENSE-CJ3': (f'https://raw.githubusercontent.com/Arthurmcarthur/Cangjie3-Plus/{CJ3_REV}/LICENSE',
                    '4a8820e0f68cc6fa95586fd211172cc20d6de23a5e44fb451ed67563444f8461'),
}

def mappings(text):
    for line in text.splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and len(fields[0]) == 1 and re.fullmatch('[a-z]{1,5}', fields[1]):
            yield fields[0], fields[1]

def third_generation_mappings(text):
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 2 and len(fields[1]) == 1 and re.fullmatch('[a-z]{1,5}', fields[0]):
            yield fields[1], fields[0]

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
    third_added = []
    for name in ('cj3.txt', 'cj3-special.txt'):
        for row in third_generation_mappings(inputs[name].decode('utf-8')):
            if row not in combined:
                combined.add(row)
                third_added.append(row)
    output += '\n# Cangjie 3 compatibility mappings (MIT); see licenses/cangjie-completion/LICENSE-CJ3.txt.\n'
    output += ''.join(f'{word}\t{code}\n' for word, code in third_added)
    (ASSETS / 'cangjie5.base.dict.yaml').write_text(output, encoding='utf-8')
    notices = ASSETS / 'licenses/cangjie-completion'
    notices.mkdir(parents=True, exist_ok=True)
    (notices / 'LICENSE.txt').write_bytes(inputs['LICENSE'])
    (notices / 'LICENSE-CJ3.txt').write_bytes(inputs['LICENSE-CJ3'])
    report = {
        'sources': [{'url': url, 'sha256': digest} for url, digest in SOURCES.values()],
        'base_revision': BASE_REV, 'completion_revision': HK_REV,
        'third_generation_revision': CJ3_REV, 'third_generation_added_mappings': len(third_added),
        'base_mappings': len(old), 'added_mappings': len(added),
        'mappings': len(combined), 'characters': len({word for word, _ in combined}),
        'output_sha256': hashlib.sha256(output.encode('utf-8')).hexdigest(),
        'processing': 'Keep all original mappings and candidate order; append unique HK completion mappings, '
                      'including alternative regional forms and supplementary-plane characters; '
                      'append unique Cangjie 3 and legacy special-table codes of 1–5 letters. '
                      'Quick indexes are derived at runtime. Glyph display depends on device fonts.'
    }
    (notices / 'SOURCE.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('base_mappings', 'added_mappings', 'mappings', 'characters')}))

if __name__ == '__main__':
    main()
