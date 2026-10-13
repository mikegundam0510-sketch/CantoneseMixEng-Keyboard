#!/usr/bin/env python3
"""Freeze additional train-only utterances and unused validation/guard utterances.

No decoder outcomes are consulted. Conversation splits and public family splits
remain those of the licensed corpus manifests.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from prepare_tatoeba_corpus import digest, load_training
from train_language_model import corpus, chunks
from train_phrase_model import ROOT, ASSETS, reverse_codes

DATA = ROOT / 'tools/data/sentence_search'


def hashed(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(source, output=DATA):
    old = ROOT / 'tools/data/sentence_ranking'
    model = json.loads((ASSETS / 'MODEL_REPORT.json').read_text())
    phrase = json.loads((ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())
    if digest(source) != phrase['source_sha256']['hkcancor_zip']:
        raise ValueError('Pinned corpus required')
    reverse = reverse_codes()
    prior = set((ROOT / 'tools/data/hk_chat_cases/prior_targets.txt').read_text().splitlines())
    inputs = list(ROOT.glob('tools/data/**/*.tsv')) + list(ROOT.glob('tools/*cases.tsv'))
    excluded_hashes = {}
    for path in sorted(inputs):
        if path.parent == DATA or path.parent == output:
            continue
        excluded_hashes[str(path.relative_to(ROOT))] = digest(path)
        # Include all plain Han surfaces; candidate output files are not inputs.
        for line in path.read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            for value in line.split('\t'):
                if len(value) >= 6 and all(c in reverse for c in value):
                    prior.add(value)

    def overlap(text):
        return any(len(p) >= 6 and (p in text or text in p) for p in prior)

    def eligible(text):
        return 6 <= len(text) <= 24 and all(c in reverse for c in text) and not overlap(text)

    def code(text):
        return ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)

    allowed = set(phrase['training_conversation_files'])
    held = set(model['heldout_conversation_files'])
    observations = list(corpus(source))
    held_texts = {text for name, text in observations if name in phrase['excluded_conversation_files']}
    training = {}
    fresh = {}
    for name, text in observations:
        if not eligible(text):
            continue
        if name in allowed and text not in held_texts:
            training.setdefault(text, ('train:hk:' + name + ':' + hashed(text)[:16], '', code(text), text))
        elif name in held:
            fresh.setdefault(text, (name, '', code(text), text))
    hk = sorted(training.values(), key=lambda r: hashed('search-long-train-v1:' + r[0]))[:1000]
    public, _ = load_training(ROOT / 'tools/data/tatoeba_corpus')
    families = {}
    for record in public:
        for text in chunks(record['text']):
            if eligible(text) and text not in held_texts:
                families.setdefault(record['group'], []).append((record['id'], text))
    public_rows = []
    for family in sorted(families, key=lambda g: hashed('search-long-public-v1:' + g))[:500]:
        _, text = min(families[family], key=lambda r: hashed(r[0] + r[1]))
        public_rows.append(('train:tatoeba:' + family, '', code(text), text))
    original = [tuple(s.split('\t')) for s in (old / 'train.tsv').read_text().splitlines()]
    rows = original + hk + public_rows
    new = sorted(fresh.values(), key=lambda r: hashed('search-long-fresh-v1:' + r[0] + r[3]))[:200]
    if len(hk) != 1000 or len(public_rows) != 500 or len(new) != 200:
        raise ValueError('Insufficient independent cases')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'train.tsv').write_text(''.join('\t'.join(r) + '\n' for r in rows))
    for name, portion in (('validation', new[:100]), ('heldout', new[100:])):
        (output / (name + '.tsv')).write_text(''.join('\t'.join(r[1:]) + '\n' for r in portion))
    manifest = {
        'baseline_revision': subprocess.check_output(['git', 'rev-parse', 'b82a517'], cwd=ROOT, text=True).strip(),
        'hkcancor_sha256': digest(source),
        'public_manifest_sha256': digest(ROOT / 'tools/data/tatoeba_corpus/manifest.json'),
        'authored_source_sha256': digest(ROOT / 'tools/data/hk_chat_scenarios.json'),
        'training_case_sha256': digest(output / 'train.tsv'),
        'training_cases': len(rows), 'reused_training_cases': len(original),
        'candidate_pool_limit': 96,
        'additional_hk_cases': len(hk), 'additional_public_families': len(public_rows),
        'allowed_sources': sorted({r[0] for r in rows}),
        'excluded_input_sha256': excluded_hashes,
        'validation_sha256': digest(output / 'validation.tsv'),
        'heldout_sha256': digest(output / 'heldout.tsv'),
        'validation_sources': [r[0] for r in new[:100]],
        'heldout_sources': [r[0] for r in new[100:]],
        'selection': 'Hashed source/text order; no candidate outcomes; exact source splits retained; all prior case/training targets6+ excluded by substring from additional cases.',
        'limits': 'New utterances from previously excluded conversations whose other utterances have been evaluated. Older spoken language, not new speakers or current HK chat frequency.'
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def prepare_reserve(source, output=DATA):
    """Freeze another100 after the first heldout became diagnostic for search."""
    model=json.loads((ASSETS/'MODEL_REPORT.json').read_text());reverse=reverse_codes()
    old=json.loads((DATA/'manifest.json').read_text())
    if digest(source)!=old['hkcancor_sha256']:raise ValueError('Pinned corpus required')
    excluded=set((ROOT/'tools/data/hk_chat_cases/prior_targets.txt').read_text().splitlines())
    for path in list(ROOT.glob('tools/data/**/*.tsv'))+list(ROOT.glob('tools/*cases.tsv')):
        if path.name=='reserve.tsv' and path.parent in (DATA,output):continue
        for line in path.read_text().splitlines():
            if not line or line.startswith('#'):continue
            for text in line.split('\t'):
                if len(text)>=6 and all(c in reverse for c in text):excluded.add(text)
    held=set(model['heldout_conversation_files']);pool={}
    for name,text in corpus(source):
        if name not in held or not 6<=len(text)<=24 or not all(c in reverse for c in text):continue
        if any(p in text or text in p for p in excluded if len(p)>=6):continue
        code=''.join(sorted(reverse[c],key=lambda s:(-len(s),s))[0] for c in text)
        pool.setdefault(text,(name,'',code,text))
    rows=sorted(pool.values(),key=lambda r:hashed('search-long-reserve2:'+r[0]+r[3]))[:100]
    if len(rows)!=100:raise ValueError('Insufficient new reserve')
    output.mkdir(parents=True,exist_ok=True)
    (output/'reserve.tsv').write_text(''.join('\t'.join(r[1:])+'\n' for r in rows))
    manifest={'cases':100,'case_sha256':digest(output/'reserve.tsv'),'hkcancor_sha256':digest(source),
        'exclusion_sha256':hashed('\n'.join(sorted(excluded))),'sources':[r[0] for r in rows],
        'selection':'Hashed order; all existing train/validation/heldout targets6+ excluded by substring. Frozen before selecting search reserve. No decoder outcomes used.',
        'limits':'Unused utterances from previously observed excluded conversations; not new speakers or real chat-frequency measurement.'}
    (output/'reserve-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus', type=Path); p.add_argument('--output', type=Path, default=DATA)
    p.add_argument('--reserve',action='store_true')
    a = p.parse_args(); m = prepare_reserve(a.corpus, a.output) if a.reserve else prepare(a.corpus, a.output)
    print(m if a.reserve else {k: m[k] for k in ('training_cases', 'additional_hk_cases', 'additional_public_families')})
