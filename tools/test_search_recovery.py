import json
from pathlib import Path
import unittest
from prepare_search_recovery import DATA
from prepare_phrase_relations import gram_index,overlap
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes

class SearchAlignmentDataTest(unittest.TestCase):
    def test_frozen_fresh_families_are_exact_and_separated(self):
        manifest=json.loads((DATA/'manifest.json').read_text());reverse=reverse_codes()
        groups={};targets={}
        for split,count in [('validation',100),('heldout',500)]:
            rows=[s.split('\t') for s in (DATA/(split+'.tsv')).read_text().splitlines()]
            self.assertEqual(len(rows),count)
            for row in rows:self.assertTrue(matches(row[2],row[3],reverse))
            source=[json.loads(s) for s in (DATA/(split+'-source.jsonl')).read_text().splitlines()]
            groups[split]={r['group'] for r in source};targets[split]={r[3] for r in rows}
            self.assertEqual(len(groups[split]),count)
        self.assertFalse(groups['validation']&groups['heldout'])
        self.assertTrue(all(not overlap(t,gram_index(targets['validation'])) for t in targets['heldout']))
        for name,checksum in manifest['file_sha256'].items():self.assertEqual(digest(DATA/name),checksum)

    def test_known_dictionary_families_never_reappear(self):
        known=set()
        for name in ['tools/data/daily_prefix/validation-source.jsonl','tools/data/daily_prefix/heldout-source.jsonl',
                     'tools/data/phrase_relations/evaluation-source.jsonl','tools/data/search_alignment/validation-source.jsonl',
                     'tools/data/search_alignment/heldout-source.jsonl']:
            known.update(json.loads(s)['group'] for s in (ROOT/name).read_text().splitlines())
        for split in ['validation','heldout']:
            fresh={json.loads(s)['group'] for s in (DATA/(split+'-source.jsonl')).read_text().splitlines()}
            self.assertFalse(known&fresh)

    def test_new_evaluation_never_overlaps_training_targets(self):
        training={s.split('\t')[3] for s in (ROOT/'tools/data/phrase_relations/train.tsv').read_text().splitlines()}
        index=gram_index(training)
        for split in ['validation','heldout']:
            for line in (DATA/(split+'.tsv')).read_text().splitlines():
                self.assertFalse(overlap(line.split('\t')[3],index))

if __name__=='__main__':unittest.main()
