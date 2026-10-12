#!/usr/bin/env python3
"""Train a bounded whole-candidate correction on frozen exact-code competitors."""
import argparse
import base64
import gzip
import json
import math
from pathlib import Path
import struct

from prepare_tatoeba_corpus import digest, load_training
from sentence_features import features
from train_candidate_ranker import learn, matches
from train_phrase_model import ROOT, ASSETS, reverse_codes, scenarios
from train_language_model import corpus, chunks

DATA = ROOT / 'tools/data/sentence_ranking'


def encode(weights, strength=1, role_schema=2):
    if not math.isfinite(strength) or not 0 <= strength <= 2: raise ValueError('Invalid strength')
    if len(weights) > 16000: raise ValueError('Too many features')
    if role_schema not in (1, 2): raise ValueError('Invalid role schema')
    payload = struct.pack('>IIIff', 0x53524b32, len(weights), role_schema, strength, 3)
    for key, value in sorted(weights.items()):
        encoded = key.encode('utf-8')
        if not 3 <= len(encoded) <= 64 or not math.isfinite(value) or abs(value) > 1.5: raise ValueError('Invalid feature')
        payload += struct.pack('>H', len(encoded)) + encoded + struct.pack('>f', value)
    return base64.encodebytes(gzip.compress(payload, mtime=0))


def stored_weights(weights): return {k: struct.unpack('>f', struct.pack('>f', v))[0] for k, v in weights.items()}


def correction(weights, context, text, strength=1, role_schema=2):
    total = sum(count * weights.get(key, 0) for key, count in features(context, text, role_schema).items())
    return strength * max(-3, min(3, total))


def read_pairs(scored, corpus_path, data=DATA):
    manifest = json.loads((data / 'manifest.json').read_text())
    protocol = json.loads((data / 'protocol.json').read_text())
    if digest(data / 'train.tsv') != manifest['training_case_sha256']: raise ValueError('Training cases changed')
    if digest(ROOT / 'tools/data/tatoeba_corpus/manifest.json') != manifest['public_manifest_sha256']:
        raise ValueError('Public source manifest changed')
    if digest(ROOT / 'tools/data/hk_chat_scenarios.json') != manifest['authored_source_sha256']:
        raise ValueError('Authored source changed')
    report = json.loads((ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())
    if digest(corpus_path) != report['source_sha256']['hkcancor_zip'] or digest(corpus_path) != manifest['hkcancor_sha256']:
        raise ValueError('HKCanCor source changed')
    hk = {}
    for name, text in corpus(corpus_path): hk.setdefault(name, set()).add(text)
    training_files = set(report['training_conversation_files'])
    excluded = set(report['excluded_conversation_files'])
    public, _ = load_training(ROOT / 'tools/data/tatoeba_corpus')
    groups = {}
    for r in public: groups.setdefault(r['group'], set()).update(chunks(r['text']))
    authored = {}
    for family, words in scenarios()['train']: authored.setdefault(family, set()).add(''.join(words))
    allowed = set(manifest['allowed_sources']); reverse = reverse_codes()
    expected = (data / 'train.tsv').read_text().splitlines()
    lines = scored.read_text().splitlines()
    if len(lines) != len(expected): raise ValueError('Scored training cases incomplete')
    pairs = []; reachable = 0
    for case, line in zip(expected, lines):
        fields = line.split('\t')
        if len(fields) != 7 or '\t'.join(fields[:4]) != case or fields[0] not in allowed:
            raise ValueError('Unexpected training row/source')
        source, context, code, gold, rank, candidates, scores = fields
        if source.startswith('train:hk:'):
            name, identity = source[len('train:hk:'):].rsplit(':', 1)
            import hashlib
            valid = name in training_files and name not in excluded and gold in hk.get(name, ()) \
                and identity == hashlib.sha256(gold.encode()).hexdigest()[:16]
        elif source.startswith('train:tatoeba:'):
            valid = gold in groups.get(source[len('train:tatoeba:'):], ())
        elif source.startswith('train:authored:'):
            valid = gold in authored.get(source[len('train:authored:'):], ())
        else: valid = False
        if not valid: raise ValueError('Non-training or misattributed source: ' + source)
        values = candidates.split('|') if candidates else []
        numbers = [float.fromhex(s) for s in scores.split('|')] if scores else []
        if len(values) != len(numbers) or len(values) > 20 or len(set(values)) != len(values) \
                or any(not math.isfinite(s) for s in numbers): raise ValueError('Invalid candidates/scores')
        if any(not matches(code, value, reverse) for value in [gold] + values): raise ValueError('Inexact candidate')
        position = values.index(gold) if gold in values else -1
        if int(rank) != position + 1: raise ValueError('Mismatched gold rank')
        if position < 0: continue
        reachable += 1
        # Several competitors of one gold/family are still one observation.
        negatives = values[:min(8, position)] + values[position + 1:position + 3]
        for negative in negatives:
            margin = numbers[position] - numbers[values.index(negative)]
            pairs.append((source, context, code, gold, negative, margin))
    if not pairs: raise ValueError('No reachable competing training examples')
    return pairs, {'cases': len(lines), 'reachable': reachable, 'pairs': len(pairs),
                   'scored_sha256': digest(scored), 'protocol_sha256': digest(data / 'protocol.json'),
                   'manifest_sha256': digest(data / 'manifest.json'), 'parameters': protocol['parameters']}


def train(scored, output, corpus_path, role_schema=2):
    pairs, report = read_pairs(scored, corpus_path)
    p = report['parameters']
    weights, metrics = learn(pairs, epochs=p['epochs'], rate=p['rate'], l2=p['l2'],
                            min_count=p['minimum_independent_support'], maximum_features=p['maximum_features'],
                            feature_extractor=lambda context, text: features(context, text, role_schema))
    weights = stored_weights(weights)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'weights.json').write_text(json.dumps(weights, ensure_ascii=False, sort_keys=True) + '\n')
    (output / 'sentence_ranker.b64').write_bytes(encode(weights, role_schema=role_schema))
    report.update({'algorithm': 'Whole-candidate residual pairwise logistic ranker with actual decoder path margins',
                   'baseline_revision': json.loads((DATA / 'protocol.json').read_text())['baseline_revision'],
                   'training': metrics, 'feature_count': len(weights), 'candidate_correction_limit': 3,
                   'base_model_sha256': digest(ROOT / 'app/src/main/assets/language_model.b64'),
                   'role_schema': role_schema,
                   'limitations': 'Local/skip/boundary evidence, not grammatical proof. Final correction clipping is a training approximation. Missing gold candidates do not train pairs. Repeated competitors and family variants are downweighted. This reranker preserves the existing displayed pool and cannot recover lost search paths.'})
    (output / 'SENTENCE_RANKER_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return weights, report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('scored', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--corpus', type=Path, required=True)
    p.add_argument('--role-schema', type=int, choices=(1,2), default=2)
    a = p.parse_args(); train(a.scored, a.output, a.corpus, a.role_schema)
