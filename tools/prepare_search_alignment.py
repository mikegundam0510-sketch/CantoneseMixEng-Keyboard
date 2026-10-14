#!/usr/bin/env python3
"""Freeze fresh dictionary families before search/ranking trials; evaluation only."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from prepare_daily_prefix_data import prepare as dictionary_pool
from prepare_phrase_relations import gram_index,overlap,hkcancor,ud
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT,reverse_codes
from sentence_features import han

BASELINE='4c57f9501acef5a8a04d9b1e5521b7927c0f7cc5'
DATA=ROOT/'tools/data/search_alignment'

def prepare(dictionary,hk,treebank,output=DATA):
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE],cwd=ROOT,text=True).splitlines()
    seen=set();inputs={}
    for name in tracked:
        if not name.startswith('tools/') or not name.endswith('.tsv'):continue
        path=ROOT/name;inputs[name]=digest(path)
        for line in path.read_text().splitlines():
            if line.startswith('#'):continue
            for value in line.split('\t'):
                if len(value)>=6 and all(han(c) for c in value):seen.add(value)
    groups=set()
    for name in ('tools/data/daily_prefix/validation-source.jsonl','tools/data/daily_prefix/heldout-source.jsonl',
                 'tools/data/phrase_relations/evaluation-source.jsonl'):
        path=ROOT/name;inputs[name]=digest(path)
        groups.update(json.loads(line)['group'] for line in path.read_text().splitlines())
    report=json.loads((ROOT/'app/src/main/assets/PHRASE_MODEL_REPORT.json').read_text())
    if digest(hk)!=report['source_sha256']['hkcancor_zip']:raise ValueError('Pinned HKCanCor required')
    allowed=set(report['training_conversation_files'])
    old_manifest=json.loads((ROOT/'tools/data/phrase_relations/manifest.json').read_text())
    if digest(treebank)!=old_manifest['ud_sha256']:raise ValueError('Pinned UD source required')
    raw={''.join(w for w,_ in words) for name,_,words in hkcancor(hk) if name in allowed}
    raw.update(''.join(w for w,_ in words) for ident,_,words in ud(treebank) if ident<=547)
    raw.update(json.loads(line)['text'] for line in (ROOT/'tools/data/tatoeba_corpus/train.jsonl').read_text().splitlines())
    previous=gram_index(seen|raw)
    with tempfile.TemporaryDirectory(prefix='alignment-dictionary-') as temporary:
        pool=Path(temporary);dictionary_pool(dictionary,pool,heldout_count=4000)
        rows=[json.loads(s) for s in (pool/'heldout-source.jsonl').read_text().splitlines()]
    fresh=[r for r in rows if r['group'] not in groups and not overlap(r['text'],previous)]
    validation=fresh[:100];vindex=gram_index({r['text'] for r in validation})
    heldout=[r for r in fresh[100:] if not overlap(r['text'],vindex)][:500]
    if len(validation)!=100 or len(heldout)!=500:raise ValueError('Insufficient fresh families')
    output.mkdir(parents=True,exist_ok=True)
    reverse=reverse_codes()
    def code(text):return ''.join(sorted(reverse[c],key=lambda s:(-len(s),s))[0] for c in text)
    for split,rs in [('validation',validation),('heldout',heldout)]:
        (output/(split+'.tsv')).write_text(''.join('\t'.join(('alignment:'+split,'',code(r['text']),r['text']))+'\n' for r in rs))
        (output/(split+'-source.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rs))
    manifest=dict(baseline_revision=BASELINE,validation_cases=100,heldout_cases=500,dictionary_sha256=digest(dictionary),
        hkcancor_sha256=digest(hk),ud_sha256=digest(treebank),known_input_sha256=inputs,
        file_sha256={name:digest(output/name) for name in ('validation.tsv','heldout.tsv','validation-source.jsonl','heldout-source.jsonl')},
        selection='Before trial decoding: extend fixed4000-family hash pool; exclude every previously tracked evaluation/train target, old dictionary families and raw training full-target exposure; remove cross-split full-target substring6+.',
        license='words.hk NCDOL1.0 evaluation-only; never train or bundle in APK. Full license/attribution in tools/data/daily_prefix.',
        limits='Public dictionary usage, not private typing accuracy; earlier796 and803 are calibration/diagnosis only. No test outcome selects a target.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('validation_cases','heldout_cases','dictionary_sha256')},ensure_ascii=False))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dictionary','hk','treebank'):p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,default=DATA);a=p.parse_args()
    prepare(a.dictionary,a.hk,a.treebank,a.output)
