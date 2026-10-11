#!/usr/bin/env python3
"""Fit signed two/three-word relations on frozen same-code candidate pairs.

The lexicon uses only segmented training conversations and authored TRAIN words.
No runtime greedy segmentation is committed to: a matching two/three-word surface
is a possible relation, counted once per endpoint. At least one word must have
multiple characters. Optional coarse POS and lexical anchors share evidence
between training surfaces. Export uses the shared bounded runtime trie, with
no on-device tagger. This is collocation evidence, not an impossibility filter.
Unknown word relations stay neutral.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
import zipfile
from pathlib import Path

from train_candidate_ranker import ASSETS, read_pairs, learn, encode
from train_language_model import han
from train_phrase_model import DATA, segmented_corpus, scenarios

MAX_LENGTH = 12


def lexicon(source):
    report = json.loads((ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != report['source_sha256']['hkcancor_zip']:
        raise ValueError('HKCanCor checksum mismatch')
    if hashlib.sha256(DATA.read_bytes()).hexdigest() != report['source_sha256']['authored_scenarios']:
        raise ValueError('Authored scenario checksum mismatch')
    allowed = set(report['training_conversation_files'])
    excluded = set(report['excluded_conversation_files'])
    if allowed & excluded:
        raise ValueError('Training conversations overlap excluded sources')
    counts = Counter()
    for name, words in segmented_corpus(source):
        if name in allowed:
            counts.update(words)
    families = {}
    for family, words in scenarios()['train']:
        families.setdefault(family, set()).update(words)
    for words in families.values():
        counts.update(words)
    return {w for w, count in counts.items() if count >= 2 and len(w) <= 8}, report


class WordFeatures:
    def __init__(self, words):
        self.words = set(words)
        if not self.words or any(not w or not all(han(c) for c in w) for w in self.words):
            raise ValueError('Invalid segmented word lexicon')
        self.maximum_word = max(map(len, self.words))

    def __call__(self, context, text):
        result = Counter()
        history = ''
        for c in context:
            history = (history + c)[-(MAX_LENGTH - 1):] if han(c) else ''
        for c in text:
            if not han(c):
                history = ''
                continue
            window = history + c
            # Enumerate backwards, without selecting a segmentation that could
            # change when the next character arrives. One surface, one endpoint.
            surfaces = set()
            frontier = [(len(window), False)]
            for number in range(1, 4):
                following = set()
                for end, multi in frontier:
                    for start in range(max(0, end - self.maximum_word), end):
                        word = window[start:end]
                        if word not in self.words:
                            continue
                        has_multi = multi or len(word) > 1
                        if number >= 2 and has_multi:
                            surfaces.add(window[start:])
                        following.add((start, has_multi))
                frontier = following
            result.update(surfaces)
            history = window[-(MAX_LENGTH - 1):]
        return result


def word_roles(source, allowed):
    """Training-only majority coarse POS; unknown authored words have no role."""
    counts = defaultdict(Counter)
    with zipfile.ZipFile(source) as archive:
        for name in sorted(allowed):
            for line in archive.read(name).decode('utf-8-sig').splitlines():
                match = re.fullmatch(r'\s*([^/<>\s]+)/([^/]+)/[^/]*/\s*', line)
                if match and all(han(c) for c in match[1]) and re.fullmatch('[a-z][a-z0-9]*', match[2]):
                    counts[match[1]][match[2][0]] += 1
    return {word: sorted(values, key=lambda tag: (-values[tag], tag))[0]
            for word, values in counts.items()}


def segmentations(surface, words):
    """Two/three known words; matching the same surface does not multiply it."""
    for a in range(1, len(surface)):
        left = surface[:a]
        if left not in words:
            continue
        if surface[a:] in words and max(a, len(surface) - a) > 1:
            yield (left, surface[a:])
        for b in range(a + 1, len(surface)):
            if surface[a:b] in words and surface[b:] in words and max(a, b - a, len(surface) - b) > 1:
                yield (left, surface[a:b], surface[b:])


def relation_inventory(source, pairs, words, allowed):
    counts = Counter()
    rows = [tokens for name, tokens in segmented_corpus(source) if name in allowed]
    rows += [tokens for _, tokens in scenarios()['train']]
    for tokens in rows:
        for size in (2, 3):
            for at in range(len(tokens) - size + 1):
                group = tuple(tokens[at:at + size])
                if all(w in words for w in group) and any(len(w) > 1 for w in group) and len(''.join(group)) <= MAX_LENGTH:
                    counts[group] += 1
    # Prefer original training word boundaries; ties are deterministic. This
    # inventory is frozen from TRAIN text, never expanded from validation cases.
    inventory = {}
    for group in sorted(counts, key=lambda g: (-counts[g], g)):
        inventory.setdefault(''.join(group), group)
    extractor = WordFeatures(words)
    for _, context, _, positive, negative, _ in pairs:
        for text in (positive, negative):
            for surface in sorted(extractor(context, text)):
                if surface not in inventory:
                    inventory[surface] = sorted(segmentations(surface, words))[0]
    return inventory


class RoleFeatures:
    def __init__(self, inventory, roles):
        self.inventory = inventory
        self.vectors = {}
        for surface, words in sorted(inventory.items()):
            tags = [roles.get(w) for w in words]
            vector = ['W:' + surface]
            if all(tags):
                vector.append('P:' + '/'.join(tags))
                vector.append('L:' + words[0] + '/' + '/'.join(tags[1:]))
                vector.append('R:' + '/'.join(tags[:-1]) + '/' + words[-1])
            self.vectors[surface] = vector

    def __call__(self, context, text):
        result = Counter()
        history = ''
        for c in context:
            history = (history + c)[-(MAX_LENGTH - 1):] if han(c) else ''
        for c in text:
            if not han(c):
                history = ''
                continue
            window = history + c
            for size in range(3, len(window) + 1):
                result.update(self.vectors.get(window[-size:], ()))
            history = window[-(MAX_LENGTH - 1):]
        return result

    def compile(self, weights):
        # Compile lexical/POS evidence to exact surfaces. The device needs no
        # tagger or dynamic segmentation, and sees exactly the training features.
        return {surface: max(-1.5, min(1.5, sum(weights.get(f, 0) for f in vector)))
                for surface, vector in self.vectors.items()
                if abs(sum(weights.get(f, 0) for f in vector)) >= 1e-4}


def train(source, pairs_path, manifest_path, output, strength=1, l2=.002, role_backoff=False):
    pairs, manifest = read_pairs(pairs_path, manifest_path)
    words, corpus_report = lexicon(source)
    # Approximate decoder language-only margins omit priors. As in the selected
    # short ranker, use a standalone pairwise objective with explicit zero offsets.
    pairs = [(*row[:5], 0) for row in pairs]
    extractor = WordFeatures(words)
    if role_backoff:
        allowed = set(corpus_report['training_conversation_files'])
        inventory = relation_inventory(source, pairs, words, allowed)
        extractor = RoleFeatures(inventory, word_roles(source, allowed))
    weights, metrics = learn(pairs, l2=l2, feature_extractor=extractor)
    latent_weights = weights
    if role_backoff:
        weights = extractor.compile(weights)
    encoded, nodes, edges = encode(weights, strength, word_relations=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'word_ranker.b64').write_bytes(encoded)
    report = {
        'algorithm': 'Signed two/three-word surface relations; pairwise logistic AdaGrad',
        'role_backoff': role_backoff,
        'role_features': 'Coarse majority training POS sequence, lexical first/last word anchors; compiled to training-only surfaces' if role_backoff else None,
        'compiled_surface_relations': len(weights),
        'training_pair_sha256': hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'baseline_decoder_revision_for_pairs': manifest['baseline_revision'],
        'source_sha256': corpus_report['source_sha256'],
        'training_conversation_files': corpus_report['training_conversation_files'],
        'excluded_conversation_files': corpus_report['excluded_conversation_files'],
        'authored_split': 'train only; family variants count as one observation',
        'lexicon_words': len(words), 'minimum_word_occurrences': 2,
        'lexicon_sha256': hashlib.sha256('\n'.join(sorted(words)).encode()).hexdigest(),
        'maximum_word_characters': 8, 'maximum_relation_words': 3,
        'maximum_relation_characters': MAX_LENGTH,
        'requires_multi_character_word': True, 'unknown_relation_score': 0,
        'actual_candidate_pairs': len(pairs), 'complete_typed_code_checked': True,
        'baseline_margin_mode': 'zero', 'strength': strength, 'endpoint_limit': 1.5,
        'training': metrics, 'trie_nodes': nodes, 'trie_edges': edges,
        'compiled_relations_at_weight_limit': sum(abs(w) == 1.5 for w in weights.values()),
        'encoded_bytes': len(encoded), 'primitive_array_bytes': 12 * nodes + 8 * edges + 4 * 65536,
        'model_sha256': hashlib.sha256(encoded).hexdigest(),
        'limitations': 'Lexical and optional majority-POS relations, not a syntactic parser or grammatical proof. Compile-time weight clipping is another fitting approximation. Ambiguous segmentations share a surface weight. Negative candidates can be valid in other contexts. Old spoken corpus and synthetic training families; no new modern chat corpus. Linear fitting approximates the endpoint cap.'}
    (output / 'WORD_RANKER_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    # Training inspection only, not an Android asset or full-sentence lookup table.
    (output / 'latent_weights.json').write_text(json.dumps(latent_weights, ensure_ascii=False, sort_keys=True) + '\n')
    (output / 'word_weights.json').write_text(json.dumps(weights, ensure_ascii=False, sort_keys=True) + '\n')
    print(json.dumps({'features': len(weights), 'lexicon': len(words), 'bytes': len(encoded)}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('--pairs', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--strength', type=float, default=1)
    parser.add_argument('--l2', type=float, default=.002)
    parser.add_argument('--role-backoff', action='store_true')
    a = parser.parse_args()
    train(a.corpus, a.pairs, a.manifest, a.output, a.strength, a.l2, a.role_backoff)
