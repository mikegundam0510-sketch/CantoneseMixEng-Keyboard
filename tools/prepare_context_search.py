#!/usr/bin/env python3
"""Freeze new evaluation families; all previously observed targets remain guards."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

from prepare_clean_ranking import rules,spans
from prepare_daily_prefix_data import prepare as dictionary_pool,hashed
from prepare_phrase_relations import gram_index,overlap
from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_phrase_model import ROOT,reverse_codes

DATA=ROOT/'tools/data/context_search'
BASELINE='e209474'


def prepare(source,output=DATA):
    if output.exists():raise ValueError('Preserve frozen data; choose a fresh output folder')
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE],cwd=ROOT,text=True).splitlines()
    seen,groups,inputs=set(),set(),{}
    for name in tracked:
        if not name.startswith('tools/'):continue
        p=ROOT/name
        if name.endswith('.tsv'):
            inputs[name]=digest(p)
            for line in p.read_text().splitlines():
                if line.startswith('#'):continue
                seen.update(t for t in line.split('\t') if len(t)>=6 and all(han(c) for c in t))
        elif name.endswith('.jsonl') and 'source' in p.name:
            inputs[name]=digest(p)
            for line in p.read_text().splitlines():
                row=json.loads(line)
                if 'group' in row and 'lemmas' in row:groups.add(str(row['group']))
    corpus=ROOT/'tools/data/clean_language_models/corpus.jsonl.gz';inputs[str(corpus.relative_to(ROOT))]=digest(corpus)
    for line in gzip.decompress(corpus.read_bytes()).decode().splitlines():
        row=json.loads(line);seen.add(row['text'])
    mapping=rules();seen.update(t for text in list(seen) for _,_,t,_ in spans(text,mapping) if len(t)>=6)
    excluded=gram_index(seen)
    with tempfile.TemporaryDirectory(prefix='context-search-families-') as folder:
        pool=Path(folder);dictionary_pool(source,pool,heldout_count=5000)
        candidates=[json.loads(s) for s in (pool/'heldout-source.jsonl').read_text().splitlines()]
    fresh=[]
    for row in sorted(candidates,key=lambda r:hashed('context-search-families-v1:'+r['group'])):
        forms=[row['text']]+[t for _,_,t,_ in spans(row['text'],mapping)]
        if str(row['group']) in groups or any(overlap(t,excluded) for t in forms):continue
        fresh.append(row)
    validation=fresh[:150];vindex=gram_index({r['text'] for r in validation})
    heldout=[r for r in fresh[150:] if not overlap(r['text'],vindex)][:500]
    if len(validation)!=150 or len(heldout)!=500:raise ValueError('Insufficient unused families: '+str(len(fresh)))
    output.mkdir(parents=True)
    reverse=reverse_codes()
    for split,rows in (('validation',validation),('heldout',heldout)):
        coded=lambda t:''.join(sorted(reverse[c],key=lambda x:(-len(x),x))[0] for c in t)
        (output/(split+'.tsv')).write_text(''.join('\t'.join(('context-search:'+split,'',coded(r['text']),r['text']))+'\n' for r in rows))
        (output/(split+'-source.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
    manifest=dict(baseline_revision=BASELINE,dictionary_sha256=digest(source),validation_cases=150,heldout_cases=500,
        eligible_unused_families=len(fresh),previous_source_groups=len(groups),known_input_sha256=inputs,
        file_sha256={n:digest(output/n) for n in ('validation.tsv','heldout.tsv','validation-source.jsonl','heldout-source.jsonl')},
        selection='Before candidate trials:5000-family fixed public dictionary pool; hash(context-search-families-v1:+group); exclude all parent-main tracked TSV targets, previously used lemma/duplicate families, complete clean primary TRAIN spans, and reviewed-normalization overlaps6+. First150 validation, next500 without cross-split target containment6+. No decoder success filters. Initial source-capacity request8000 exceeded5550 eligible families; reduced before any decoding, not based on outcomes.',
        text='Retain existing daily-written extractor labels/code convention; its punctuation/comma/lookup-mark normalization is documented in original daily_prefix provenance. New labels frozen before decoding and never recoded after results.',
        license='words.hk NCDOL1.0 evaluation-only, never training or APK. See tools/data/daily_prefix/NOTICE.txt and LICENSE.txt.',
        limits='Public dictionary examples from held-separated families, not private phone typing or a new independent corpus. All old500/800/3893 are now observed guards. Reading fresh labels for exclusions is permitted; no holdout decoder outcomes before qualification.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('validation_cases','heldout_cases','eligible_unused_families','previous_source_groups')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path,default=DATA)
    a=p.parse_args();prepare(a.source,a.output)
