#!/usr/bin/env python3
"""Import only attested high-frequency new word surfaces; use our native code aliases at runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REVISION='438d89283cab793148b04ebbe756e228153213c8'
FILES=('lexicon/hk/kinfx_hk_words.dict.yaml','lexicon/hk/kinfx_hk_idioms.dict.yaml')
MIN_FREQUENCY=3000 # KINFX's own threshold for accepting a complete short phrase.


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(source,existing,characters):
    words={};rows=0
    for relative in FILES:
        body=False
        for line in (source/relative).read_text().splitlines():
            if line=='...':body=True;continue
            if not body or not line or line.startswith('#'):continue
            f=line.split('\t')
            if len(f)!=3:raise ValueError('Unexpected upstream word table')
            rows+=1;text=f[0];count=int(f[2])
            # Upstream spellings and Microsoft ordering are deliberately not
            # imported. All native alternative spellings remain usable.
            if 2<=len(text)<=5 and count>=MIN_FREQUENCY and text not in existing and all(c in characters for c in text):
                words[text]=max(words.get(text,0),count)
    return words,rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--native-facts',type=Path,required=True);args=p.parse_args()
    actual=subprocess.check_output(['git','-C',str(args.source),'rev-parse','HEAD'],text=True).strip()
    if actual!=REVISION:raise ValueError('Use the reviewed upstream revision')
    if subprocess.check_output(['git','-C',str(args.source),'status','--porcelain'],text=True).strip():
        raise ValueError('Upstream checkout has unreviewed changes')
    oldpaths=[ROOT/'app/src/main/assets'/name for name in
        ('quick_phrases.tsv','hk_phrases.tsv','cantonese_phrases.tsv','hk_chat_phrases.tsv')]
    existing=set()
    for path in oldpaths:
        for line in path.read_text().splitlines():
            if line.startswith('#'):continue
            f=line.split('\t')
            if len(f)>=3:existing.add(f[1])
    characters={s.split('\t')[0] for s in args.native_facts.read_text().splitlines()}
    words,rows=collect(args.source,existing,characters)
    output=ROOT/'app/src/main/assets/kinfx_words.tsv'
    text='# KINFX/rime-cantonese word surfaces (CC BY4.0); native aliases are matched at runtime. See licenses/kinfx/README.md.\n'
    text+=''.join(word+'\t'+str(words[word])+'\n' for word in sorted(words))
    output.write_text(text)
    directory=ROOT/'app/src/main/assets/licenses/kinfx';directory.mkdir(exist_ok=True)
    (directory/'UPSTREAM-LEXICON-NOTICE.txt').write_bytes((args.source/'lexicon/NOTICE').read_bytes())
    (directory/'LGPL-3.0.txt').write_bytes((args.source/'licenses/rime-quick-LGPL-3.0.txt').read_bytes())
    (directory/'CC-BY-4.0.txt').write_bytes((ROOT/'app/src/main/assets/licenses/RIME-CANTONESE-CC-BY-4.0.txt').read_bytes())
    manifest=dict(source='https://github.com/Kinfxhk/kinfx-ime',revision=REVISION,
        upstream_rows=rows,imported_new_words=len(words),minimum_source_frequency=MIN_FREQUENCY,
        word_lengths=[2,3,4,5],native_dictionary_characters=len(characters),
        native_dictionary_sha256=sha(ROOT/'app/src/main/assets/cangjie5.base.dict.yaml'),
        changes='New word surfaces/frequencies only; deduplicate current assets; every character must exist in native dictionary. No upstream code column, Windows order or Lua top-out behavior imported.',
        source_frequency_limitation='Source corpus counts are not measured Hong Kong phone typing frequency.',
        source_sha256={relative:sha(args.source/relative) for relative in FILES},
        preexisting_vocabulary_sha256={path.name:sha(path) for path in oldpaths},output_sha256=sha(output))
    (directory/'SOURCE.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'upstream_rows':rows,'new_common_words':len(words),'output_sha256':sha(output)},ensure_ascii=False))


if __name__=='__main__':main()
