#!/usr/bin/env python3
"""Freeze independent training utterances and new diagnostic holdout before decoding."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from prepare_tatoeba_corpus import digest, load_training
from train_language_model import corpus, chunks
from train_phrase_model import ROOT, ASSETS, reverse_codes, scenarios

DATA = ROOT / 'tools/data/sentence_ranking'
BASELINE = 'fac1e87'  # Resolved to the full revision in the frozen protocol.
PRIOR_SNAPSHOT = 'b82a517095bee0113afc254546eea6eba86e0207'


def prior_paths(patterns):
    """Later experiments must not retroactively change this frozen exclusion set."""
    tracked = set(subprocess.check_output(['git','ls-tree','-r','--name-only',PRIOR_SNAPSHOT],
                                        cwd=ROOT,text=True).splitlines())
    return [p for pattern in patterns for p in ROOT.glob(pattern)
            if str(p.relative_to(ROOT)) in tracked]


def prepare(source, output=DATA):
    report = json.loads((ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())
    if digest(source) != report['source_sha256']['hkcancor_zip']:
        raise ValueError('Pinned HKCanCor source required')
    reverse = reverse_codes()
    public = ROOT / 'tools/data/tatoeba_corpus'
    public_train, public_manifest = load_training(public)
    prior = set()
    # Previously inspected validation/holdout/regression targets are not training.
    for path in prior_paths(('tools/data/**/*validation*.tsv', 'tools/data/**/*heldout*.tsv',
                    'tools/data/**/*prospective*.tsv', 'tools/hk_*cases.tsv',
                    'tools/data/word_ranking/old600.tsv', 'tools/lm_heldout_cases.tsv',
                    'tools/continuous_clause_cases.tsv', 'tools/semantic_cases.tsv')):
        if path.parent == output: continue
        for line in path.read_text().splitlines():
            if line and not line.startswith('#'):
                fields = line.split('\t')
                if len(fields) >= 3: prior.add(fields[2])
    prior.update((ROOT / 'tools/data/hk_chat_cases/prior_targets.txt').read_text().splitlines())
    old_train = {s.split('\t')[2] for s in (ROOT / 'tools/data/candidate_ranking/train.tsv').read_text().splitlines()}

    def reachable(text):
        return 6 <= len(text) <= 16 and all(c in reverse for c in text)

    def overlap(text, texts):
        return any(len(p) >= 6 and (p in text or text in p) for p in texts)

    def code(text):
        return ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)

    train = {}
    allowed = set(report['training_conversation_files'])
    observations = corpus(source)
    excluded_texts = {text for name, text in observations if name in report['excluded_conversation_files']}
    for name, text in observations:
        if name in allowed and reachable(text) and text not in old_train | excluded_texts and not overlap(text, prior):
            train.setdefault(text, ('train:hk:' + name + ':' + digest_text(text)[:16], '', code(text), text))
    hk = sorted(train.values(), key=lambda r: digest_text('sentence-ranker-v1:' + r[0]))[:800]
    grouped = {}
    for record in public_train:
        for text in chunks(record['text']):
            if reachable(text) and text not in excluded_texts and not overlap(text, prior):
                grouped.setdefault(record['group'], []).append((record['id'], text))
    public_cases = []
    for group in sorted(grouped, key=lambda g: digest_text('sentence-ranker-v1:' + g))[:600]:
        ident, text = min(grouped[group], key=lambda r: digest_text(r[0] + r[1]))
        public_cases.append(('train:tatoeba:' + group, '', code(text), text))
    authored = [('train:authored:' + family, '', code(''.join(words)), ''.join(words))
                for family, words in scenarios()['train'] if not overlap(''.join(words), prior)]
    rows = hk + public_cases + authored
    if len(hk) != 800 or len(public_cases) != 600:
        raise ValueError('Insufficient independent training cases')
    # New excluded-conversation utterances, selected without any candidate results.
    training_texts = {r[3] for r in rows}
    held = {}
    model = json.loads((ASSETS / 'MODEL_REPORT.json').read_text())
    for name, text in observations:
        if name in model['heldout_conversation_files'] and reachable(text) \
                and not overlap(text, prior | training_texts | old_train):
            held.setdefault(text, ('heldout:hk:' + name + ':' + digest_text(text)[:16], '', code(text), text))
    fresh = sorted(held.values(), key=lambda r: digest_text('sentence-ranker-fresh-v1:' + r[0]))[:100]
    if len(fresh) < 100: raise ValueError('Insufficient new heldout utterances')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'train.tsv').write_text(''.join('\t'.join(r) + '\n' for r in rows), encoding='utf-8')
    (output / 'fresh_natural.tsv').write_text(''.join('\t'.join(r[1:]) + '\n' for r in fresh), encoding='utf-8')
    manifest = {'baseline_revision': BASELINE, 'hkcancor_sha256': digest(source),
                'public_manifest_sha256': digest(public / 'manifest.json'),
                'authored_source_sha256': digest(ROOT / 'tools/data/hk_chat_scenarios.json'),
                'training_case_sha256': digest(output / 'train.tsv'), 'training_cases': len(rows),
                'training_hk': len(hk), 'training_public': len(public_cases), 'training_authored': len(authored),
                'allowed_sources': sorted({r[0] for r in rows}),
                'excluded_conversations': sorted(set(report['excluded_conversation_files'])),
                'fresh_natural_sha256': digest(output / 'fresh_natural.tsv'), 'fresh_natural_sources': [r[0] for r in fresh],
                'prior_targets_sha256': digest_text('\n'.join(sorted(prior))),
                'selection': 'Hashed order; entire independent train-only Han utterances6..16; existing HK pair-training targets excluded; all known validation/regression/heldout target substrings6+ excluded. New holdout is frozen before model selection.',
                'limits': 'Old public spoken conversations and community example sentences, not measured current HK chat frequency. New holdout uses previously excluded conversations, but those conversation sources have been observed in other tests. Authored variants are correlated.'}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def digest_text(text): return hashlib.sha256(text.encode()).hexdigest()


def prepare_followup(source, output=DATA):
    """Reserve another hundred utterances after the first guard became diagnostic."""
    manifest = json.loads((DATA / 'manifest.json').read_text())
    if digest(source) != manifest['hkcancor_sha256']: raise ValueError('Pinned corpus required')
    report = json.loads((ASSETS / 'MODEL_REPORT.json').read_text()); reverse = reverse_codes()
    excluded = set((ROOT / 'tools/data/hk_chat_cases/prior_targets.txt').read_text().splitlines())
    for path in prior_paths(('tools/data/**/*validation*.tsv','tools/data/**/*heldout*.tsv',
                    'tools/data/**/*prospective*.tsv','tools/hk_*cases.tsv',
                    'tools/data/word_ranking/old600.tsv','tools/lm_heldout_cases.tsv',
                    'tools/continuous_clause_cases.tsv','tools/semantic_cases.tsv',
                    'tools/data/candidate_ranking/train.tsv','tools/data/sentence_ranking/fresh_natural.tsv')):
        for line in path.read_text().splitlines():
            if line and not line.startswith('#'):
                fields = line.split('\t')
                if len(fields) >= 3: excluded.add(fields[2])
    excluded.update(s.split('\t')[3] for s in (DATA / 'train.tsv').read_text().splitlines())
    held = set(report['heldout_conversation_files']); pool = {}
    for name, text in corpus(source):
        if name not in held or not 6 <= len(text) <= 16 or not all(c in reverse for c in text): continue
        if any(len(old) >= 6 and (old in text or text in old) for old in excluded): continue
        code = ''.join(sorted(reverse[c], key=lambda s: (-len(s),s))[0] for c in text)
        pool.setdefault(text, (name, '', code, text))
    rows = sorted(pool.values(), key=lambda r: digest_text('sentence-ranker-followup-v1:' + r[0] + r[3]))[:100]
    if len(rows) != 100: raise ValueError('Insufficient followup utterances')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'fresh_followup.tsv').write_text(''.join('\t'.join(r[1:]) + '\n' for r in rows))
    report = {'cases':100,'hkcancor_sha256':digest(source),'case_sha256':digest(output / 'fresh_followup.tsv'),
              'sources':[r[0] for r in rows],'exclusion_sha256':digest_text('\n'.join(sorted(excluded))),
              'selection':'Hashed order of reachable6..16 character utterances in excluded conversations; prior test/training targets and the first fresh100 excluded by substring6+. Reserved before gated selection; no candidate outcomes used.',
              'limits':'These utterances are new to evaluation, but other utterances in the same heldout conversations have been observed. Not contemporary HK chat-frequency evidence.'}
    (output / 'followup-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus', type=Path)
    p.add_argument('--output', type=Path, default=DATA)
    p.add_argument('--followup', action='store_true')
    args = p.parse_args()
    m = prepare_followup(args.corpus, args.output) if args.followup else prepare(args.corpus, args.output)
    print(json.dumps(m if args.followup else {k:m[k] for k in ('training_cases','training_hk','training_public','training_authored')},indent=2))
