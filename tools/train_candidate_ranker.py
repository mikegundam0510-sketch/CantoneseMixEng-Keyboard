#!/usr/bin/env python3
"""Train a bounded signed ranker on actual same-code decoder mistakes.

Input TSV: source, preceding context, typed code, correct text, competing text,
and optionally the correct-minus-competitor baseline score. The manifest names
the allowed training sources and pins the pairs, source corpus and decoder.
Only short Han bigrams/trigrams are exported, never whole training sentences.
Validation/held-out text is forbidden even when an input manifest allows it.
"""
import argparse
import base64
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from train_language_model import han
from train_phrase_model import scenarios, reverse_codes

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
MAX_LENGTH = 3
ENDPOINT_LIMIT = 1.5


def features(context, text):
    """Match runtime character-endpoint features, including only trailing Han context."""
    history = ''
    for character in context:
        history = (history + character)[-(MAX_LENGTH - 1):] if han(character) else ''
    result = Counter()
    for character in text:
        if not han(character):
            history = ''
            continue
        window = history + character
        for size in range(2, min(MAX_LENGTH, len(window)) + 1):
            result[window[-size:]] += 1
        history = window[-(MAX_LENGTH - 1):]
    return result


def matches(code, text, reverse):
    positions = {0}
    for character in text:
        positions = {at + len(part) for at in positions for part in reverse.get(character, ())
                     if code.startswith(part, at)}
        if not positions:
            return False
    return len(code) in positions


def allowed_training_sources():
    report = json.loads((ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())
    authored = scenarios()
    train = set(report['training_conversation_files']) | {family for family, _ in authored['train']}
    excluded = set(report['excluded_conversation_files'])
    excluded |= {family for split in ('validation', 'heldout') for family, _ in authored[split]}
    return train, excluded, report['source_sha256']


def read_pairs(path, manifest_path, reverse=None):
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('pairs_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Candidate pair checksum mismatch')
    train, forbidden, hashes = allowed_training_sources()
    allowed = set(manifest.get('allowed_sources', ()))
    excluded = set(manifest.get('excluded_sources', ())) | forbidden
    if not allowed or not allowed <= train or allowed & excluded:
        raise ValueError('Manifest includes non-training or excluded source')
    if any(manifest.get('source_sha256', {}).get(name) != digest for name, digest in hashes.items()):
        raise ValueError('Training source checksum mismatch')
    if not re.fullmatch('[0-9a-f]{40}', manifest.get('baseline_revision', '')):
        raise ValueError('Baseline decoder revision must be pinned')
    if reverse is None:
        reverse = reverse_codes()
    result, seen = [], set()
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        row = line.split('\t')
        if len(row) not in (5, 6):
            raise ValueError(f'Invalid candidate pair at line {number}')
        source, context, code, positive, negative = row[:5]
        if source not in allowed or source in excluded:
            raise ValueError(f'Excluded training source at line {number}: {source}')
        if not re.fullmatch('[a-z]{3,48}', code) or positive == negative:
            raise ValueError(f'Invalid competing candidate at line {number}')
        if not positive or not negative or not all(han(c) for c in positive + negative):
            raise ValueError(f'Non-Han candidate at line {number}')
        if len(context) > 12:
            raise ValueError(f'Context exceeds decoder bound at line {number}')
        if not matches(code, positive, reverse) or not matches(code, negative, reverse):
            raise ValueError(f'Competing candidates do not match the complete code at line {number}')
        offset = float(row[5]) if len(row) == 6 else 0
        if not math.isfinite(offset) or abs(offset) > 1000:
            raise ValueError(f'Invalid baseline margin at line {number}')
        identity = tuple(row[:5])
        if identity in seen:
            continue
        seen.add(identity)
        result.append((source, context, code, positive, negative, offset))
    if not result:
        raise ValueError('No candidate training pairs')
    return result, manifest


def learn(pairs, epochs=80, rate=.3, l2=.02, min_count=2, maximum_features=50000):
    """Deterministic full-batch pairwise logistic objective with L2 and bounded weights."""
    if not 1 <= epochs <= 1000 or not 0 < rate <= 2 or not 0 < l2 <= 2:
        raise ValueError('Invalid training hyperparameters')
    if not 1 <= min_count <= 100 or not 1 <= maximum_features <= 50000:
        raise ValueError('Invalid ranker feature bounds')
    differences, support = [], defaultdict(set)
    target_pairs, family_targets = Counter(), defaultdict(set)
    for source, context, code, positive, negative, offset in pairs:
        left, right = features(context, positive), features(context, negative)
        delta = {feature: left[feature] - right[feature] for feature in left.keys() | right.keys()
                 if left[feature] != right[feature]}
        identity = (source, context, code, positive)
        # Ten wrong candidates from one gold utterance are one observation,
        # not ten independent reasons to generalize its short relations.
        # Authored subject/time variants likewise count as one family.
        observation = source if source.startswith('train:') else identity
        for feature in delta:
            support[feature].add(observation)
        target_pairs[identity] += 1
        if source.startswith('train:'):
            family_targets[source].add(identity)
        differences.append((identity, delta, offset))
    # Select by independent positive-target/family support, not competitor count.
    vocabulary = sorted(sorted((f for f, targets in support.items() if len(targets) >= min_count),
                               key=lambda f: (-len(support[f]), f))[:maximum_features])
    if not vocabulary:
        raise ValueError('No supported candidate features')
    indices = {feature: at for at, feature in enumerate(vocabulary)}
    examples = []
    for identity, delta, offset in differences:
        sparse = sorted((indices[f], count) for f, count in delta.items() if f in indices)
        if sparse:
            weight = 1 / target_pairs[identity]
            # Six authored subject/time variants must not act as six real observations.
            if identity[0] in family_targets:
                weight /= len(family_targets[identity[0]])
            examples.append((sparse, weight, offset))
    if not examples:
        raise ValueError('No supported competing differences')
    total_weight = sum(weight for _, weight, _ in examples)
    weights, accumulated = [0.0] * len(vocabulary), [0.0] * len(vocabulary)
    losses = []
    for epoch in range(epochs):
        gradient = [l2 * value for value in weights]
        loss = 0
        for sparse, pair_weight, offset in examples:
            margin = offset + sum(weights[index] * count for index, count in sparse)
            # Stable softplus(-margin) and sigmoid(-margin).
            loss += pair_weight * (max(0, -margin) + math.log1p(math.exp(-abs(margin))))
            probability = math.exp(-margin) / (1 + math.exp(-margin)) if margin >= 0 else 1 / (1 + math.exp(margin))
            multiplier = -probability * pair_weight / total_weight
            for index, count in sparse:
                gradient[index] += multiplier * count
        losses.append(loss / total_weight + l2 * sum(w * w for w in weights) / 2)
        for index, value in enumerate(gradient):
            accumulated[index] += value * value
            weights[index] = max(-ENDPOINT_LIMIT, min(ENDPOINT_LIMIT,
                weights[index] - rate * value / math.sqrt(accumulated[index] + 1e-8)))
    learned = {feature: weight for feature, weight in zip(vocabulary, weights) if abs(weight) >= 1e-4}
    return learned, {'epochs': epochs, 'rate': rate, 'l2': l2, 'minimum_independent_target_support': min_count,
                     'feature_support_unit': 'Distinct (source,context,code,positive); authored variants collapsed to family',
                     'features_considered': len(support), 'features_supported': len(vocabulary),
                     'features_exported': len(learned), 'training_examples': len(examples),
                     'initial_logistic_objective': losses[0], 'final_logistic_objective': losses[-1],
                     'positive_features': sum(w > 0 for w in learned.values()),
                     'negative_features': sum(w < 0 for w in learned.values())}


def encode(weights, strength=1):
    if not math.isfinite(strength) or not 0 <= strength <= 2:
        raise ValueError('Invalid candidate ranker strength')
    root = {'children': {}, 'value': 0}
    for text, value in sorted(weights.items()):
        if not 2 <= len(text) <= MAX_LENGTH or not all(han(c) for c in text) or not math.isfinite(value) or abs(value) > ENDPOINT_LIMIT:
            raise ValueError('Invalid candidate feature')
        node = root
        for character in reversed(text):
            node = node['children'].setdefault(ord(character), {'children': {}, 'value': 0})
        node['value'] = value
    nodes = []
    def visit(node):
        node['id'] = len(nodes)
        nodes.append(node)
        for _, child in sorted(node['children'].items()):
            visit(child)
    visit(root)
    if len(nodes) > 150000:
        raise ValueError('Candidate ranker exceeds runtime node bound')
    edges, records = [], []
    for node in nodes:
        records.append((len(edges), len(node['children']), node['value']))
        edges.extend((character, child['id']) for character, child in sorted(node['children'].items()))
    payload = struct.pack('>IIIIff', 0x43524b31, MAX_LENGTH, len(nodes), len(edges), strength, ENDPOINT_LIMIT)
    payload += b''.join(struct.pack('>IIf', *record) for record in records)
    payload += b''.join(struct.pack('>II', *edge) for edge in edges)
    return base64.encodebytes(gzip.compress(payload, mtime=0)), len(nodes), len(edges)


def train(pairs_path, manifest_path, output, strength=1, ignore_offsets=False, **parameters):
    pairs, manifest = read_pairs(pairs_path, manifest_path)
    if ignore_offsets:
        pairs = [(*row[:5], 0) for row in pairs]
    weights, metrics = learn(pairs, **parameters)
    encoded, nodes, edges = encode(weights, strength)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'candidate_ranker.b64').write_bytes(encoded)
    report = {'algorithm': 'Signed character bigram/trigram pairwise logistic ranker; regularized full-batch AdaGrad',
              'training_pair_sha256': hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
              'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              'baseline_decoder_revision': manifest['baseline_revision'],
              'source_sha256': manifest['source_sha256'],
              'training_sources': sorted({source for source, *_ in pairs}),
              'excluded_sources': sorted(set(manifest['excluded_sources']) | allowed_training_sources()[1]),
              'actual_candidate_pairs': len(pairs), 'complete_typed_code_checked': True,
              'baseline_margin_mode': 'zero' if ignore_offsets else 'input_column_or_zero',
              'ignored_baseline_margins': bool(ignore_offsets),
              'maximum_feature_characters': MAX_LENGTH, 'unknown_feature_score': 0,
              'endpoint_weight_limit': ENDPOINT_LIMIT, 'strength': strength,
              'trie_nodes': nodes, 'trie_edges': edges, 'encoded_bytes': len(encoded),
              'primitive_array_bytes': 12 * nodes + 8 * edges + 4 * 65536,
              'training': metrics,
              'limitations': 'Short local relations only; a competing negative is evidence from decoding, not proof that its wording is impossible. Training uses older public conversations and authored scenarios. The linear fitting objective approximates the runtime endpoint cap. Optional language-score margins may omit decoder vocabulary priors. Model fitting accuracy is not held-out accuracy.'}
    (output / 'CANDIDATE_RANKER_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pairs': len(pairs), 'features': len(weights), 'bytes': len(encoded)}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--strength', type=float, default=1)
    parser.add_argument('--ignore-offset', '--ignore-offsets', dest='ignore_offsets', action='store_true',
                        help='Fit standalone relations when input margins omit decoder priors')
    parser.add_argument('--epochs', type=int, default=80)
    parser.add_argument('--rate', type=float, default=.3)
    parser.add_argument('--l2', type=float, default=.02)
    parser.add_argument('--min-count', type=int, default=2,
                        help='Minimum independent positive utterances/families supporting a feature')
    parser.add_argument('--maximum-features', type=int, default=50000)
    arguments = parser.parse_args()
    train(arguments.pairs, arguments.manifest, arguments.output, arguments.strength, arguments.ignore_offsets,
          epochs=arguments.epochs, rate=arguments.rate, l2=arguments.l2,
          min_count=arguments.min_count, maximum_features=arguments.maximum_features)
