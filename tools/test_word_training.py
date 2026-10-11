#!/usr/bin/env python3
"""Lexical evidence, independent support, and runtime export contracts."""
import base64
from collections import Counter
import gzip
from pathlib import Path
import struct
import tempfile
import unittest

from train_candidate_ranker import learn, encode
from train_word_ranker import WordFeatures, RoleFeatures, lexicon, word_roles


class WordTrainingTest(unittest.TestCase):
    def test_lexical_pairs_are_not_arbitrary_character_ngrams(self):
        f = WordFeatures({'研究', '一下', '訊息', '再', '個', '人', '研究一', '下'})
        self.assertIn('研究一下', f('', '研究一下'))
        self.assertEqual(1, f('', '研究一下')['研究一下'])  # ambiguous boundaries, same surface
        self.assertNotIn('研究', f('', '研究一下'))  # one word alone is not a relation
        self.assertNotIn('個人', f('', '個人'))  # two single-character words use the short ranker
        self.assertNotIn('究一', f('', '研究一下'))
        self.assertIn('再研究一下', f('', '再研究一下'))
        self.assertEqual({}, f('', '從未見過'))

    def test_incremental_features_are_additive_and_reset_at_non_han(self):
        f = WordFeatures({'研究', '一下', '再', '𠮩𠹌', '訊息'})
        text = '研究一下再研究𠮩𠹌訊息'
        for i in range(len(text) + 1):
            self.assertEqual(f('再', text), f('再', text[:i]) + f('再' + text[:i], text[i:]))
        self.assertIn('𠮩𠹌訊息', f('𠮩', '𠹌訊息'))
        self.assertNotIn('研究一下', f('研究，', '一下'))
        self.assertNotIn('研究一下', f('研究', 'abc一下'))
        self.assertTrue(all(len(x) <= 12 for x in f('', text)))

    def test_same_words_with_different_neighbours_learn_signed_relations(self):
        f = WordFeatures({'研究', '一下', '食飯', '而家', '聽日', '今晚'})
        pairs = [(f'utf8/{i}', '', 'abcd', prefix + '研究一下', prefix + '研究食飯', 0)
                 for i, prefix in enumerate(['而家', '聽日', '今晚'])]
        weights, report = learn(pairs, feature_extractor=f)
        self.assertGreater(weights['研究一下'], 0)
        self.assertLess(weights['研究食飯'], 0)
        self.assertNotIn('研究', weights)
        # An unknown relation containing the same word is not penalized.
        self.assertEqual(0, sum(weights.get(k, 0) * n for k, n in f('', '今晚食飯').items()))
        self.assertLess(report['final_logistic_objective'], report['initial_logistic_objective'])
        encoded, nodes, edges = encode(weights, word_relations=True)
        header = struct.unpack('>IIIIff', gzip.decompress(base64.decodebytes(encoded))[:24])
        self.assertEqual((0x57524b31, 12, nodes, edges, 1, 1.5), header)

    def test_one_utterance_with_many_competitors_does_not_meet_word_support(self):
        f = WordFeatures({'研究', '一下', '食飯', '收工', '返工', '聽日', '而家'})
        pairs = [('utf8/one', '', 'abcd', '研究一下', '研究' + w, 0) for w in ['食飯', '收工', '返工']]
        pairs += [(f'utf8/{i}', '', 'abcd', p + '收工食飯', p + '返工食飯', 0)
                  for i, p in enumerate(['聽日', '而家'])]
        weights, _ = learn(pairs, feature_extractor=f)
        self.assertNotIn('研究一下', weights)
        self.assertIn('收工食飯', weights)

    def test_corpus_checksum_checked_before_lexicon_use(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wrong.zip'
            path.write_bytes(b'not the pinned corpus')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                lexicon(path)

    def test_role_backoff_transfers_between_words_without_exporting_unknown_surfaces(self):
        inventory = {'研究一下': ('研究', '一下'), '研究食飯': ('研究', '食飯'),
                     '考慮一下': ('考慮', '一下')}
        features = RoleFeatures(inventory, {'研究': 'v', '考慮': 'v', '一下': 'd', '食飯': 'v'})
        pairs = [(f'utf8/{i}', '', 'abcd', prefix + '研究一下', prefix + '研究食飯', 0)
                 for i, prefix in enumerate(['而家', '聽日', '今晚'])]
        weights, _ = learn(pairs, feature_extractor=features)
        compiled = features.compile(weights)
        self.assertGreater(compiled['考慮一下'], 0)
        self.assertLess(compiled['研究食飯'], 0)
        self.assertNotIn('考慮食飯', compiled)  # unseen surface is not invented at export
        self.assertTrue(all(abs(w) <= 1.5 for w in compiled.values()))

    def test_compiled_roles_match_additive_training_features(self):
        inventory = {'研究一下': ('研究', '一下'), '再研究一下': ('再', '研究', '一下')}
        features = RoleFeatures(inventory, {'研究': 'v', '一下': 'd', '再': 'd'})
        weights = {f: .05 for vector in features.vectors.values() for f in vector}
        compiled = features.compile(weights)
        text = '研究一下再研究一下'
        expected = sum(weights.get(f, 0) * n for f, n in features('', text).items())
        surface_score = sum(text.count(surface) * value for surface, value in compiled.items())
        self.assertAlmostEqual(expected, surface_score)
        for at in range(len(text) + 1):
            self.assertEqual(features('', text), features('', text[:at]) + features(text[:at], text[at:]))
        self.assertEqual(Counter(), features('研究，', '一下'))
        self.assertEqual(['W:研究一下'], RoleFeatures(inventory, {}).vectors['研究一下'])

    def test_pos_dictionary_reads_only_allowed_conversations(self):
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'corpus.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('utf8/train', '研究/v/jin4/\n研究/n/jin4/\n研究/v/jin4/\n')
                z.writestr('utf8/heldout', '研究/n/jin4/\n秘密/n/bei3/\n')
            roles = word_roles(path, {'utf8/train'})
            self.assertEqual({'研究': 'v'}, roles)


if __name__ == '__main__':
    unittest.main()
