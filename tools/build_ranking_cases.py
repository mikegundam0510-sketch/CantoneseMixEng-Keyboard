#!/usr/bin/env python3
"""Reproduce separate ranking validation and new evaluation snippets; never train on them."""
import argparse, hashlib, json
from pathlib import Path
from train_language_model import corpus

ROOT = Path(__file__).resolve().parent.parent

def generate(source, output, count):
    report = json.loads((ROOT / 'app/src/main/assets/MODEL_REPORT.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != report['source_sha256']['hkcancor_zip']:
        raise ValueError('HKCanCor checksum differs from the pinned training source')
    reverse = {}
    for line in (ROOT / 'app/src/main/assets/cangjie5.base.dict.yaml').read_text().splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and len(fields[0]) == 1 and fields[1].isalpha():
            full = fields[1]
            reverse.setdefault(fields[0], set()).add(full if len(full) == 1 else full[0] + full[-1])
    existing = {(r['context'], r['text']) for r in json.loads((ROOT/'tools/lm_heldout_cases.json').read_text())}
    output.mkdir(parents=True, exist_ok=True)
    for split in ('validation', 'heldout'):
        names = set(report[split + '_conversation_files'])
        rows, seen = [], set()
        for name, text in corpus(source):
            if name not in names or len(text) < 8: continue
            for at in range(4, len(text)-3, 4):
                context, target = text[max(0,at-4):at], text[at:at+6]
                if not all(c in reverse for c in target) or target in seen: continue
                seen.add(target)
                if split == 'heldout' and (context, target) in existing: continue
                code = ''.join(sorted(reverse[c], key=lambda x:(-len(x),x))[0] for c in target)
                rows.append((context, code, target))
        rows.sort(key=lambda r: hashlib.sha256((r[0]+r[2]).encode()).hexdigest())
        path=output/(split+'.tsv')
        path.write_text(''.join('\t'.join(r)+'\n' for r in rows[:count]))
        print(split, min(count,len(rows)), hashlib.sha256(path.read_bytes()).hexdigest())

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--count',type=int,default=240)
    args=parser.parse_args();generate(args.source,args.output,args.count)
