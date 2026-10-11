"""Verify source integrity, repeatable import and preservation of existing data."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import import_wordshk


class WordsHkImportTest(unittest.TestCase):
    def test_mismatched_snapshot_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'wordslist.json'
            source.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Unexpected words.hk snapshot'):
                import_wordshk.load(source)

    def test_import_is_idempotent_and_preserves_codes_and_stronger_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); assets = root / 'assets'; assets.mkdir()
            original_codes = '...\n返\tyhe\n返\tye\n工\tmlm\n㤀\tvup\n'
            (assets / 'cangjie5.base.dict.yaml').write_text(original_codes)
            original = 'yemm\t返工\t9000\n'
            (assets / 'quick_phrases.tsv').write_text(original)
            (assets / 'hk_phrases.tsv').write_text('')
            (assets / 'cantonese_phrases.tsv').write_text('')
            (assets / 'character_frequencies.tsv').write_text('返\t200\n工\t100\n㤀\t3\n')
            data = {'charcount.json': {'返': 1000, '工': 1, '\n': 100000},
                    'existingwordcount.json': {'返工': 10},
                    'wordslist.json': {'返工': ['faan1 gung1'], '工返': ['gung1 faan1'],
                        '返*工': ['faan1 gung1'], '返A': ['faan1 ei1'], '返𠮷': ['faan1 gat1']}}
            sources = []
            for name, value in data.items():
                path = root / name; path.write_text(json.dumps(value)); sources.append(path)
            expected = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
            with patch.dict(import_wordshk.EXPECTED, expected, clear=True):
                first = import_wordshk.import_data(*sources, assets)
                snapshots = {name: (assets / name).read_bytes() for name in
                    ('cantonese_phrases.tsv', 'character_frequencies.tsv', 'licenses/wordshk/SOURCE.json')}
                second = import_wordshk.import_data(*sources, assets)
            self.assertEqual(first, second)
            for name, raw in snapshots.items(): self.assertEqual(raw, (assets / name).read_bytes())
            self.assertEqual(original, (assets / 'quick_phrases.tsv').read_text())
            self.assertEqual(original_codes, (assets / 'cangjie5.base.dict.yaml').read_text())
            self.assertEqual(2, first['selected_words'])
            self.assertEqual(1, first['observed_selected_words'])
            self.assertEqual(1, first['excluded_words']['missing_existing_character_code'])
            text = (assets / 'character_frequencies.tsv').read_text()
            self.assertIn('㤀\t3\n', text)
            self.assertNotIn('\n\t100000', text)
            self.assertIn('yemm\t返工\t300\t10\n', (assets / 'cantonese_phrases.tsv').read_text())


if __name__ == '__main__':
    unittest.main()
