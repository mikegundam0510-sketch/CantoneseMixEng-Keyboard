#!/usr/bin/env python3
"""Meaningful data-boundary and short-relation ranker fitting checks."""
import base64
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

import train_candidate_ranker as training


class CandidateTrainingTest(unittest.TestCase):
    def pairs(self):
        return [(f'train:messages:{at}', '', 'ofqm', positive, negative, 0)
                for at, (positive, negative) in enumerate((
                    ('覆個訊息', '覆個辛德'), ('收個訊息', '收個辛德'),
                    ('睇個訊息', '睇個辛德'), ('你覆訊息', '你覆辛德')))]

    def test_pairwise_training_learns_signed_competition_and_generalizes_short_relations(self):
        weights, report = training.learn(self.pairs(), min_count=2)
        def score(text):
            return sum(weights.get(feature, 0) * count for feature, count in training.features('', text).items())
        self.assertGreater(score('幫我覆返個訊息'), score('幫我覆返個辛德'))
        self.assertGreater(weights['訊息'], 0)
        self.assertLess(weights['辛德'], 0)
        self.assertLess(report['final_logistic_objective'], report['initial_logistic_objective'])
        self.assertTrue(all(2 <= len(feature) <= 3 for feature in weights))
        self.assertTrue(all(abs(weight) <= 1.5 for weight in weights.values()))
        self.assertFalse(any(feature in weights for feature in ('覆個訊息', '覆個辛德')))

    def test_runtime_features_reset_and_are_additive_without_code_features(self):
        self.assertEqual(training.features('個，', '訊息'), training.features('', '訊息'))
        self.assertEqual(training.features('個', 'abc訊息'), training.features('', '訊息'))
        text = '你覆個訊息再睇個辛德'
        for split in range(len(text) + 1):
            left, right = text[:split], text[split:]
            self.assertEqual(training.features('香港', text),
                             training.features('香港', left) + training.features('香港' + left, right))
        self.assertEqual({'𠮩𠹌': 1}, training.features('𠮩', '𠹌'))

    def test_exact_code_matching_handles_alternative_and_variable_length_codes(self):
        reverse = {'你': {'of', 'o'}, '好': {'nd'}, '佢': {'oo'}}
        self.assertTrue(training.matches('ofnd', '你好', reverse))
        self.assertTrue(training.matches('ond', '你好', reverse))
        self.assertFalse(training.matches('ofnd', '佢好', reverse))
        self.assertFalse(training.matches('ofndq', '你好', reverse))

    def test_training_and_encoding_are_deterministic_and_export_only_short_signed_features(self):
        first, _ = training.learn(self.pairs(), min_count=2)
        second, _ = training.learn(self.pairs(), min_count=2)
        self.assertEqual(first, second)
        encoded, nodes, edges = training.encode(first, .5)
        self.assertEqual(encoded, training.encode(second, .5)[0])
        header = struct.unpack('>IIIIff', gzip.decompress(base64.decodebytes(encoded))[:24])
        self.assertEqual((0x43524b31, 3, nodes, edges, .5, 1.5), header)
        self.assertEqual(nodes - 1, edges)
        with self.assertRaisesRegex(ValueError, 'Invalid candidate feature'):
            training.encode({'覆返個訊息': 1})

    def test_manifest_cannot_allow_heldout_and_checksum_mismatch_fails_before_output(self):
        allowed, excluded, hashes = training.allowed_training_sources()
        source, forbidden = sorted(allowed)[0], sorted(excluded)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pairs = root / 'pairs.tsv'
            pairs.write_text(f'{source}\t\tofnd\t你好\t佢好\n')
            manifest = {'allowed_sources': [source], 'excluded_sources': sorted(excluded),
                        'source_sha256': hashes, 'baseline_revision': '0' * 40,
                        'pairs_sha256': hashlib.sha256(pairs.read_bytes()).hexdigest()}
            path = root / 'manifest.json'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'do not match the complete code'):
                training.read_pairs(pairs, path, {'你': {'of'}, '好': {'nd'}, '佢': {'oo'}})
            manifest['allowed_sources'].append(forbidden)
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'non-training or excluded'):
                training.read_pairs(pairs, path)
            manifest['pairs_sha256'] = 'wrong'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'pair checksum mismatch'):
                training.train(pairs, path, root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_offset_ablation_is_explicit_and_keeps_all_provenance_checks(self):
        allowed, excluded, hashes = training.allowed_training_sources()
        source = sorted(allowed)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pairs = root / 'pairs.tsv'
            pairs.write_text(f'{source}\t\tofvd\t你好\t係好\t20\n')
            manifest = {'allowed_sources': [source], 'excluded_sources': sorted(excluded),
                        'source_sha256': hashes, 'baseline_revision': '0' * 40,
                        'pairs_sha256': hashlib.sha256(pairs.read_bytes()).hexdigest()}
            path = root / 'manifest.json'
            path.write_text(json.dumps(manifest))
            with contextlib.redirect_stdout(io.StringIO()):
                with_offset = training.train(pairs, path, root / 'offset', min_count=1)
                without_offset = training.train(pairs, path, root / 'zero', ignore_offsets=True, min_count=1)
            self.assertFalse(with_offset['ignored_baseline_margins'])
            self.assertTrue(without_offset['ignored_baseline_margins'])
            self.assertEqual('zero', without_offset['baseline_margin_mode'])
            self.assertEqual(with_offset['training_pair_sha256'], without_offset['training_pair_sha256'])
            self.assertGreater(without_offset['training']['features_exported'], with_offset['training']['features_exported'])
            manifest['allowed_sources'].append(sorted(excluded)[0])
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'non-training or excluded'):
                training.train(pairs, path, root / 'invalid', ignore_offsets=True, min_count=1)
            self.assertFalse((root / 'invalid').exists())


if __name__ == '__main__':
    unittest.main()
