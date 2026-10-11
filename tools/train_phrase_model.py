#!/usr/bin/env python3
"""Train bounded word-transition evidence from segmented training conversations.

HKCanCor's original word boundaries are retained. Authored scenario families are
split before expansion, are not real-user statistics, and have a documented prior.
Validation and held-out text never contributes words or transition counts.
"""
import argparse
import base64
from collections import Counter
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import struct
import zipfile

from train_language_model import han

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
DATA = ROOT / 'tools/data/hk_chat_scenarios.json'
MAX_LENGTH = 12
AUTHOR_PRIOR = 3


def segmented_corpus(source):
    """Yield Han-only segments; punctuation/Latin and sentence tags reset words."""
    with zipfile.ZipFile(source) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith('utf8/') or name.endswith('/'):
                continue
            words = []
            for line in archive.read(name).decode('utf-8-sig').splitlines():
                match = re.fullmatch(r'\s*([^/<>\s]+)/[^/]+/[^/]*/\s*', line)
                if match and all(han(c) for c in match[1]):
                    words.append(match[1])
                elif match or '</sent_tag>' in line or '<sent>' in line:
                    if words:
                        yield name, words
                    words = []
            if words:
                yield name, words


def scenarios():
    data = json.loads(DATA.read_text())
    families, texts, result = set(), set(), {}
    for split in ('train', 'validation', 'heldout'):
        rows = []
        for topic, templates in data[split].items():
            for index, template in enumerate(templates):
                if template in families:
                    raise ValueError('Scenario family crosses splits: ' + template)
                families.add(template)
                family = f'{split}:{topic}:{index}'
                for subject, time in data['variants']:
                    words = template.format(s=subject, t=time).split()
                    text = ''.join(words)
                    if text in texts or not all(han(c) for c in text):
                        raise ValueError('Duplicate or non-Han scenario: ' + text)
                    texts.add(text)
                    rows.append((family, words))
        result[split] = rows
    return result


def reverse_codes():
    reverse = {}
    for line in (ASSETS / 'cangjie5.base.dict.yaml').read_text().splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and len(fields[0]) == 1 and re.fullmatch('[a-z]{1,5}', fields[1]):
            code = fields[1] if len(fields[1]) == 1 else fields[1][0] + fields[1][-1]
            reverse.setdefault(fields[0], set()).add(code)
    return reverse


def prepare_cases(rows, reverse):
    result = []
    for family, words in rows:
        text = ''.join(words)
        # Zero editor context tests an entire unseen composition, not next-word recall.
        if not all(c in reverse for c in text):
            raise ValueError('Unreachable authored scenario: ' + text)
        code = ''.join(sorted(reverse[c], key=lambda x: (-len(x), x))[0] for c in text)
        if len(code) > 48:
            raise ValueError('Composition exceeds decoder limit: ' + text)
        result.append('\t'.join(('', code, text)))
    return '\n'.join(result) + '\n'


def natural_cases(source, old_report, reverse, cases):
    # The exclusions were frozen before model selection. Do not inspect results
    # to add/remove utterances or change this deterministic sample.
    prior = set((ROOT / 'tools/data/hk_chat_cases/prior_targets.txt').read_text().splitlines())
    held = set(old_report['heldout_conversation_files'])
    rows = set()
    for name, words in segmented_corpus(source):
        text = ''.join(words)
        if name not in held or not 6 <= len(text) <= 16 or not all(c in reverse for c in text):
            continue
        if any(old in text or text in old for old in prior):
            continue
        code = ''.join(sorted(reverse[c], key=lambda s: (-len(s), s))[0] for c in text)
        if len(code) <= 48:
            rows.add((name, code, text))
    rows = sorted(rows, key=lambda r: hashlib.sha256(('word-model-v1:' + r[0] + r[2]).encode()).hexdigest())[:180]
    path = cases / 'natural_heldout.tsv'
    path.write_text(''.join('\t' + code + '\t' + text + '\n' for name, code, text in rows))
    (cases / 'natural_heldout_source.json').write_text(json.dumps({
        'source_sha256': old_report['source_sha256']['hkcancor_zip'],
        'selection': 'Full Han utterance chunks, 6..16 characters; held-out conversations only; exclude any earlier regression target substring >=4 Han in either direction; SHA256(word-model-v1:+filename+text) first180',
        'exclusion_sha256': hashlib.sha256((ROOT / 'tools/data/hk_chat_cases/prior_targets.txt').read_bytes()).hexdigest(),
        'case_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'cases': len(rows),
        'conversation_files': sorted({r[0] for r in rows}),
        'limitation': 'New full utterances, but conversation files were also used in historical evaluations; not independently collected modern chat.'
    }, ensure_ascii=False, indent=2) + '\n')


def train(source, output, cases, strength):
    strength = float(strength)
    if not math.isfinite(strength) or not 0 <= strength <= 2:
        raise ValueError('Invalid phrase model strength')
    old_report = json.loads((ASSETS / 'MODEL_REPORT.json').read_text())
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != old_report['source_sha256']['hkcancor_zip']:
        raise ValueError('HKCanCor checksum mismatch')
    excluded = set(old_report['validation_conversation_files'] + old_report['heldout_conversation_files'])
    authored = scenarios()
    reverse = reverse_codes()
    cases.mkdir(parents=True, exist_ok=True)
    for split in ('validation', 'heldout'):
        (cases / (split + '.tsv')).write_text(prepare_cases(authored[split], reverse))
    natural_cases(source, old_report, reverse, cases)
    # Predeclare the release gate before evaluating either candidate implementation.
    gate = {'authored_heldout_min_cases': 100, 'authored_top1_gain_percentage_points': 10,
            'authored_top5_gain_percentage_points': 5, 'natural_heldout_top1_gain_percentage_points': 5,
            'old_top1_max_regression_percentage_points': 1, 'median_latency_max_ratio': 1.2,
            'note': 'Synthetic gains alone do not establish a major real-world improvement.'}
    (cases / 'release_gate.json').write_text(json.dumps(gate, indent=2) + '\n')

    unigrams, pairs, triples = Counter(), Counter(), Counter()
    conversations, chunks = set(), 0
    for name, words in segmented_corpus(source):
        if name in excluded:
            continue
        conversations.add(name)
        chunks += 1
        unigrams.update(words)
        pairs.update(zip(words, words[1:]))
        triples.update(zip(words, words[1:], words[2:]))
    # Each family contributes at most once to a repeated transition. Expanding six
    # subjects/time phrases must not masquerade as six observations of that phrase.
    family_counts = {}
    for family, words in authored['train']:
        counters = family_counts.setdefault(family, (set(), set(), set()))
        counters[0].update(words)
        counters[1].update(zip(words, words[1:]))
        counters[2].update(zip(words, words[1:], words[2:]))
    for words, twos, threes in family_counts.values():
        unigrams.update({w: AUTHOR_PRIOR for w in words})
        pairs.update({w: AUTHOR_PRIOR for w in twos})
        triples.update({w: AUTHOR_PRIOR for w in threes})
    total = sum(unigrams.values())
    outgoing = Counter()
    triple_outgoing = Counter()
    for (left, right), count in pairs.items():
        outgoing[left] += count
    for (one, two, three), count in triples.items():
        triple_outgoing[(one, two)] += count
    relations = {}
    def keep(words, count, denominator):
        text = ''.join(words)
        if count < 2 or len(text) > MAX_LENGTH or not any(len(w) > 1 for w in words):
            return
        marginal = (unigrams[words[-1]] + .5) / (total + .5 * len(unigrams))
        conditional = (count + 4 * marginal) / (denominator + 4)
        lift = max(0, math.log(conditional / marginal))
        # Unknown relations are neutral; observed transitions supply bounded evidence.
        value = min(3, lift) * count / (count + 4)
        if value > .1:
            relations[text] = max(relations.get(text, 0), value)
    for words, count in pairs.items():
        keep(words, count, outgoing[words[0]])
    for words, count in triples.items():
        keep(words, count, triple_outgoing[words[:2]])
    # Reverse trie shares suffixes. Runtime walks at most twelve edges per character,
    # rather than hashing and looking up every possible suffix independently.
    trie = {'children': {}, 'value': 0}
    for text, value in sorted(relations.items()):
        node = trie
        for character in reversed(text):
            node = node['children'].setdefault(ord(character), {'children': {}, 'value': 0})
        node['value'] = value
    nodes = []
    def visit(node):
        node['id'] = len(nodes)
        nodes.append(node)
        for _, child in sorted(node['children'].items()):
            visit(child)
    visit(trie)
    edges, records = [], []
    for node in nodes:
        records.append((len(edges), len(node['children']), node['value']))
        edges.extend((character, child['id']) for character, child in sorted(node['children'].items()))
    payload = struct.pack('>IIIIf', 0x574c4d31, MAX_LENGTH, len(nodes), len(edges), strength)
    payload += b''.join(struct.pack('>IIf', *record) for record in records)
    payload += b''.join(struct.pack('>II', *edge) for edge in edges)
    encoded = base64.encodebytes(gzip.compress(payload, mtime=0))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'phrase_model.b64').write_bytes(encoded)
    # Only segmented training words enter the lattice; never complete authored sentences.
    words = Counter()
    for family, tokens in authored['train']:
        for word in set(tokens):
            if 2 <= len(word) <= 8 and all(c in reverse for c in word):
                words[word] += 1
    vocabulary = set()
    for word, count in words.items():
        for variant in itertools.islice(itertools.product(*(sorted(reverse[c]) for c in word)), 8):
            vocabulary.add((''.join(variant), word, min(100, count)))
    (output / 'hk_chat_phrases.tsv').write_text(
        '# Project-authored training words; counts are synthetic priorities, not usage frequency.\n' +
        ''.join(f'{code}\t{word}\t{count}\n' for code, word, count in sorted(vocabulary)))
    report = {'algorithm': 'Segmented-word bigram/trigram likelihood-ratio evidence, bounded positive backoff',
              'maximum_relation_characters': MAX_LENGTH, 'unknown_relation_score': 0,
              'source_sha256': {'hkcancor_zip': digest, 'authored_scenarios': hashlib.sha256(DATA.read_bytes()).hexdigest()},
              'training_conversation_files': sorted(conversations), 'excluded_conversation_files': sorted(excluded),
              'training_utterance_chunks': chunks, 'authored_family_prior': AUTHOR_PRIOR,
              'authored_expansion_counts': {s: len(r) for s, r in authored.items()},
              'relations': len(relations), 'strength': strength, 'trie_nodes': len(nodes),
              'trie_array_bytes': 12 * len(nodes) + 8 * len(edges),
              'primitive_array_bytes': 12 * len(nodes) + 8 * len(edges) + 4 * 65536,
              'runtime_root_index_bytes': 4 * 65536,
              'encoded_bytes': len(encoded), 'training_vocabulary_words': len(words),
              'training_vocabulary_entries': len(vocabulary), 'release_gate': gate,
              'case_sha256': {s: hashlib.sha256((cases / (s + '.tsv')).read_bytes()).hexdigest() for s in ('validation', 'heldout', 'natural_heldout')},
              'limitations': 'Authored scenarios are synthetic and share vocabulary across distinct scenario families. HKCanCor is older spoken conversation, not current chat. Reused corpus regressions are not a fresh independent typing study.'}
    (output / 'PHRASE_MODEL_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'relations': len(relations), 'scenarios': report['authored_expansion_counts']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('corpus', type=Path)
    parser.add_argument('--output', type=Path, default=ASSETS)
    parser.add_argument('--cases', type=Path, default=ROOT / 'tools/data/hk_chat_cases')
    parser.add_argument('--strength', type=float, default=1)
    args = parser.parse_args()
    if not 0 <= args.strength <= 2:
        parser.error('strength must be between zero and two')
    train(args.corpus, args.output, args.cases, args.strength)
