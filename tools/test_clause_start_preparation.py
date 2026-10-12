import json
from pathlib import Path
import tempfile
import unittest

from prepare_clause_start_cases import DATA, PUBLIC, prepare
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import reverse_codes


class ClauseStartPreparationTest(unittest.TestCase):
    def test_public_probe_excludes_every_previously_evaluated_family(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        excluded = set(manifest['excluded_previous_public_groups'])
        sources = manifest['sets']['prospective_public']['sources']
        self.assertEqual(len(sources), 100)
        self.assertFalse(excluded & {s.split(':')[0] for s in sources})
        source_manifest = json.loads((PUBLIC / 'manifest.json').read_text())
        old_ids = set(source_manifest['splits']['heldout']['case_record_ids'])
        records = [json.loads(line) for line in (PUBLIC / 'heldout.jsonl').read_text().splitlines()]
        self.assertEqual(excluded, {r['group'] for r in records if r['id'] in old_ids})

    def test_authored_families_do_not_cross_split_and_codes_are_exact(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        train = {s.split(':', 1)[1] for s in manifest['sets']['validation']['sources']}
        held = {s.split(':', 1)[1] for s in manifest['sets']['heldout']['sources']}
        self.assertFalse(train & held)
        reverse = reverse_codes()
        for name, metadata in manifest['sets'].items():
            path = DATA / (name + '.tsv')
            self.assertEqual(digest(path), metadata['sha256'])
            for line in path.read_text().splitlines():
                context, code, target = line.split('\t')
                self.assertLessEqual(len(context), 12)
                self.assertTrue(matches(code, target, reverse), target)

    def test_generation_reproduces_frozen_cases_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root)
            for name in ('validation.tsv', 'heldout.tsv', 'prospective_public.tsv', 'manifest.json'):
                self.assertEqual((DATA / name).read_bytes(), (root / name).read_bytes(), name)


if __name__ == '__main__':
    unittest.main()
