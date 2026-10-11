import json
from collections import Counter
from pathlib import Path
import sqlite3
import tempfile
import unittest

from prepare_tatoeba_corpus import (DB_SHA256, digest, group_records, load_training,
                                    normalize, overlap_index, overlaps, read_source, split_for)
from train_language_model import chunks, add_family_counts


class TatoebaPreparationTest(unittest.TestCase):
    def test_family_count_cap_and_non_han_boundaries(self):
        counts = [Counter() for _ in range(6)]
        families = add_family_counts(counts, [
            {'group': 'a', 'text': '返工返工，開 Zoom 會議'},
            {'group': 'a', 'text': '我哋返工'},
            {'group': 'b', 'text': '佢哋返工'}], 6)
        self.assertEqual(families, 2)
        self.assertEqual(counts[2]['返工'], 12)
        self.assertEqual(counts[2]['會議'], 6)
        self.assertEqual(counts[2]['工開'], 0)
        self.assertEqual(counts[2]['開會'], 0)

    def test_source_links_are_required_not_just_yue_language(self):
        conn = sqlite3.connect(':memory:')
        conn.executescript('''
            CREATE TABLE sources(source_id, sourcename, version, legal, link);
            CREATE TABLE chinese_sentences(chinese_sentence_id, traditional, language);
            CREATE TABLE sentence_links(fk_chinese_sentence_id, fk_non_chinese_sentence_id, fk_source_id);
            INSERT INTO sources VALUES(10,'Tatoeba—Cantonese-English','2023-04-08','CC BY 2.0 FR','url');
            INSERT INTO chinese_sentences VALUES(1,'我哋今日返工','yue'),(2,'佢哋今日返工','yue'),(3,'test','cmn');
            INSERT INTO sentence_links VALUES(1,21,10),(1,22,10),(2,23,9),(3,24,10);
        ''')
        rows = read_source(conn)
        self.assertEqual([r['id'] for r in rows], ['1'])
        self.assertEqual(rows[0]['links'], {'21', '22'})
        conn.execute("UPDATE sources SET legal='research only'")
        with self.assertRaisesRegex(ValueError, 'attribution'):
            read_source(conn)
        conn.close()

    def test_punctuation_and_english_do_not_join_chinese_context(self):
        text = normalize('我哋\n今日開 Zoom，之後返工。')
        self.assertEqual(text, '我哋 今日開 Zoom，之後返工。')
        self.assertEqual(chunks(text), ['我哋', '今日開', '之後返工'])

    def test_transitive_translation_and_near_duplicate_groups(self):
        rows = [
            {'id': '1', 'text': '我哋今日一齊返工', 'links': {'a'}},
            {'id': '2', 'text': '佢哋今日一齊返工', 'links': {'b'}},
            {'id': '3', 'text': '聽日咩時間見面', 'links': {'b'}},
            {'id': '4', 'text': '點解突然停電呢', 'links': {'c'}},
        ]
        grouped = group_records(rows)
        self.assertEqual(len({r['group'] for r in grouped[:3]}), 1)
        self.assertNotEqual(grouped[0]['group'], grouped[3]['group'])
        self.assertEqual({r['id']: r['group'] for r in grouped},
                         {r['id']: r['group'] for r in group_records(list(reversed(rows)))})

    def test_shared_chunk_keeps_long_sentences_together(self):
        rows = [{'id': '1', 'text': '佢今日真係唔使返工，早啲休息啦', 'links': set()},
                {'id': '2', 'text': '佢今日真係唔使返工，遲啲再見啦', 'links': set()}]
        self.assertEqual(len({r['group'] for r in group_records(rows)}), 1)

    def test_protected_overlap_both_directions_and_minimum_length(self):
        index = overlap_index(['我哋今日一齊返工', '唔該'])
        self.assertTrue(overlaps('今日一齊返工', index))
        self.assertTrue(overlaps('我哋今日一齊返工之後食飯', index))
        self.assertFalse(overlaps('唔該你幫我開門', index))
        self.assertFalse(overlaps('今日一齊放假', index))

    def fixture(self, root):
        manifest = {'schema': 1, 'database_sha256': DB_SHA256, 'splits': {}}
        for i, split in enumerate(('train', 'validation', 'heldout')):
            group = next(f'{j:08x}' + '0' * 56 for j in range(20)
                         if split_for(f'{j:08x}' + '0' * 56) == split)
            row = {'id': str(i), 'group': group, 'text': ['我哋今日一齊返工', '記得早啲返屋企', '佢唔知聽日落雨'][i]}
            path = root / (split + '.jsonl')
            path.write_text(json.dumps(row, ensure_ascii=False) + '\n')
            manifest['splits'][split] = {'sha256': digest(path)}
        (root / 'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def test_training_reader_excludes_validation_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            rows, _ = load_training(root)
            self.assertEqual([r['text'] for r in rows], ['我哋今日一齊返工'])
            with (root / 'heldout.jsonl').open('a') as out:
                out.write('{}\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_training(root)

    def test_cross_split_duplicate_fails_even_with_updated_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.fixture(root)
            path = root / 'heldout.jsonl'
            row = json.loads(path.read_text())
            row['text'] = '我哋今日一齊返工'
            path.write_text(json.dumps(row))
            manifest['splits']['heldout']['sha256'] = digest(path)
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'leakage'):
                load_training(root)


if __name__ == '__main__':
    unittest.main()
