#!/usr/bin/env python3
"""Data-boundary and reproducibility checks for the new offline word model."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import train_phrase_model as training


class PhraseTrainingTest(unittest.TestCase):
    def test_punctuation_latin_and_sentence_boundaries_do_not_create_relations(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.zip'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('utf8/conversation', '<sent>\n轉/v/x/\n錢/n/x/\n，/w/x/\n覆返/v/x/\nOK/xa/x/\n訊息/n/x/\n</sent_tag>\n香港/n/x/\n')
            self.assertEqual([['轉', '錢'], ['覆返'], ['訊息'], ['香港']],
                             [words for _, words in training.segmented_corpus(source)])

    def test_scenario_families_and_complete_sentences_are_disjoint(self):
        rows = training.scenarios()
        train = {''.join(words) for _, words in rows['train']}
        self.assertEqual((240, 60, 120), tuple(len(rows[s]) for s in ('train', 'validation', 'heldout')))
        for split in ('validation', 'heldout'):
            self.assertFalse(train & {''.join(words) for _, words in rows[split]})
        with tempfile.TemporaryDirectory() as directory:
            data = json.loads(training.DATA.read_text())
            data['heldout']['work'][0] = data['train']['work'][0]
            source = Path(directory) / 'scenarios.json'
            source.write_text(json.dumps(data, ensure_ascii=False))
            with patch.object(training, 'DATA', source):
                with self.assertRaisesRegex(ValueError, 'family crosses splits'):
                    training.scenarios()

    def test_source_hash_mismatch_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'wrong.zip'; source.write_bytes(b'wrong source')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                training.train(source, root / 'assets', root / 'cases', 1)
            self.assertFalse((root / 'assets').exists())

    def test_pinned_training_reproduces_bundled_bytes_and_excludes_test_words(self):
        source = Path(os.environ.get('HK_PHRASE_CORPUS', '/tmp/hkcancor-utf8.zip'))
        if not source.exists():
            self.fail('Pass the pinned corpus path with HK_PHRASE_CORPUS or provide /tmp/hkcancor-utf8.zip')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):
                training.train(source, root / 'assets', root / 'cases', 1)
            for name in ('phrase_model.b64', 'hk_chat_phrases.tsv', 'PHRASE_MODEL_REPORT.json'):
                self.assertEqual(hashlib.sha256((training.ASSETS / name).read_bytes()).hexdigest(),
                                 hashlib.sha256((root / 'assets' / name).read_bytes()).hexdigest(), name)
            for name in ('validation.tsv', 'heldout.tsv', 'natural_heldout.tsv'):
                self.assertEqual((training.ROOT / 'tools/data/hk_chat_cases' / name).read_bytes(),
                                 (root / 'cases' / name).read_bytes(), name)
            report = json.loads((root / 'assets/PHRASE_MODEL_REPORT.json').read_text())
            self.assertFalse(set(report['training_conversation_files']) & set(report['excluded_conversation_files']))
            words = {line.split('\t')[1] for line in (root / 'assets/hk_chat_phrases.tsv').read_text().splitlines() if not line.startswith('#')}
            test_sentences = {''.join(words) for _, words in training.scenarios()['heldout']}
            self.assertFalse(words & test_sentences)


if __name__ == '__main__':
    unittest.main()
