#!/usr/bin/env python3
"""Split integrity and actual-competitor selection checks for offline ranker data."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_candidate_training as preparation


class CandidatePreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = Path(os.environ.get('HK_PHRASE_CORPUS', '/tmp/hkcancor-utf8.zip'))
        if not cls.corpus.exists():
            raise AssertionError('Pass the pinned corpus with HK_PHRASE_CORPUS or provide /tmp/hkcancor-utf8.zip')
        cls.report = json.loads((preparation.ASSETS / 'MODEL_REPORT.json').read_text())
        cls.authored = preparation.scenarios()
        cls.reverse = preparation.reverse_codes()
        excluded = set(cls.report['validation_conversation_files']) | set(cls.report['heldout_conversation_files'])
        phrase_report = json.loads((preparation.ASSETS / 'PHRASE_MODEL_REPORT.json').read_text())
        cls.source = next(source for source in phrase_report['training_conversation_files'] if source not in excluded)
        # All selection fixture competitors really match the same complete Quick code.
        left = sorted(c for c, codes in cls.reverse.items() if 'of' in codes)
        right = sorted(c for c, codes in cls.reverse.items() if 'vd' in codes)
        cls.competitors = [a + b for a in left for b in right if a + b != '你好'][:14]
        if len(cls.competitors) != 14:
            raise AssertionError('Expected at least fourteen genuine same-code competitors')

    def frozen(self, root, rows, candidates, ranks):
        cases = root / 'train.tsv'
        cases.write_text(''.join(row + '\n' for row in rows))
        manifest = {
            'baseline_revision': preparation.BASELINE,
            'source_sha256': {
                'hkcancor_zip': preparation.digest(self.corpus),
                'authored_scenarios': preparation.digest(preparation.ROOT / 'tools/data/hk_chat_scenarios.json'),
            },
            'allowed_sources': [self.source],
            'excluded_sources': self.report['validation_conversation_files'] + self.report['heldout_conversation_files'],
            'splits': {'train': {'cases': len(rows), 'case_sha256': preparation.digest(cases),
                                 'sources': [self.source] * len(rows)}},
        }
        (root / 'manifest.json').write_text(json.dumps(manifest))
        evaluation = root / 'baseline.tsv'
        evaluation.write_text(''.join(row + '\t' + str(rank) + '\t' + '|'.join(choices) + '\n'
                                      for row, rank, choices in zip(rows, ranks, candidates)))
        return manifest, evaluation

    def test_hard_negatives_above_gold_and_one_below_are_selected_without_gold(self):
        negative = self.competitors
        candidate_rows = [negative[:11] + ['你好'] + negative[11:],
                          ['你好'] + negative,
                          negative,
                          negative + ['你好']]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, evaluation = self.frozen(root, ['\tofvd\t你好'] * 4, candidate_rows, [12, 1, 0, 15])
            manifest = preparation.pairs(root, evaluation)
            actual = [line.split('\t') for line in (root / 'pairs.tsv').read_text().splitlines()]
            expected = negative[:10] + [negative[11]] + [negative[0]] + negative[:10] + negative[:10]
            self.assertEqual(expected, [row[4] for row in actual])
            self.assertTrue(all(row[:4] == [self.source, '', 'ofvd', '你好'] for row in actual))
            self.assertFalse(any(row[3] == row[4] for row in actual))
            self.assertEqual(3, manifest['reachable_training_positives'])
            self.assertEqual(len(expected), manifest['training_pairs'])
            self.assertEqual(preparation.digest(root / 'pairs.tsv'), manifest['pairs_sha256'])
            self.assertEqual(preparation.digest(evaluation), manifest['training_evaluation_sha256'])

    def test_mismatched_baseline_pin_frozen_payload_or_training_source_is_rejected(self):
        for mutation in ('baseline', 'case_checksum', 'source', 'excluded_source', 'source_checksum', 'evaluation_row'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, evaluation = self.frozen(root, ['\tofvd\t你好'], [['你好', self.competitors[0]]], [1])
                if mutation == 'baseline':
                    manifest['baseline_revision'] = '0' * 40
                elif mutation == 'case_checksum':
                    manifest['splits']['train']['case_sha256'] = 'wrong'
                elif mutation == 'source':
                    manifest['splits']['train']['sources'] = ['unknown_conversation']
                elif mutation == 'excluded_source':
                    manifest['excluded_sources'].append(self.source)
                elif mutation == 'source_checksum':
                    manifest['source_sha256']['authored_scenarios'] = 'wrong'
                else:
                    evaluation.write_text(evaluation.read_text().replace('你好', '你係', 1))
                (root / 'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    preparation.pairs(root, evaluation)
                self.assertFalse((root / 'pairs.tsv').exists())

    def test_wrong_corpus_checksum_is_rejected_before_freezing_any_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrong = root / 'wrong.zip'
            wrong.write_bytes(b'wrong source')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                preparation.prepare(wrong, root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_authored_validation_and_heldout_payloads_never_become_natural_training(self):
        forbidden = [(self.source, words) for split in ('validation', 'heldout')
                     for _, words in self.authored[split] if 6 <= len(''.join(words)) <= 16]
        self.assertTrue(forbidden)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(preparation, 'segmented_corpus', return_value=forbidden):
                manifest = preparation.prepare(self.corpus, root / 'cases')
            self.assertEqual(0, manifest['splits']['train']['natural_cases'])
            train_text = {line.split('\t')[2] for line in (root / 'cases/train.tsv').read_text().splitlines()}
            self.assertFalse(train_text & {''.join(words) for _, words in forbidden})

    def test_cached_public_corpus_has_disjoint_sources_and_complete_target_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = preparation.prepare(self.corpus, root / 'cases')
            texts, sources = {}, {}
            for split in ('train', 'validation', 'heldout'):
                case_file = root / 'cases' / (split + '.tsv')
                rows = [line.split('\t') for line in case_file.read_text().splitlines()]
                metadata = manifest['splits'][split]
                self.assertEqual(len(rows), metadata['cases'])
                self.assertEqual(len(rows), len(metadata['sources']))
                self.assertEqual(preparation.digest(case_file), metadata['case_sha256'])
                self.assertTrue(all(len(row) == 3 for row in rows))
                texts[split] = {row[2] for row in rows}
                sources[split] = set(metadata['sources'])
                if split != 'train':
                    texts[split].update(''.join(words) for _, words in self.authored[split])
                    sources[split].update(family for family, _ in self.authored[split])
                self.assertGreater(metadata['natural_cases'], 100)
            for left, right in (('train', 'validation'), ('train', 'heldout'), ('validation', 'heldout')):
                self.assertFalse(texts[left] & texts[right], (left, right))
                self.assertFalse(sources[left] & sources[right], (left, right))
            self.assertTrue(sources['train'] <= set(manifest['allowed_sources']))
            self.assertFalse(sources['train'] & set(manifest['excluded_sources']))


if __name__ == '__main__':
    unittest.main()
