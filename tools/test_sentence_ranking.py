import json
from pathlib import Path
import tempfile
import unittest

from sentence_features import features, role
from train_sentence_ranker import encode, correction, stored_weights, read_pairs
from prepare_sentence_ranking import DATA, prepare, prepare_followup
from prepare_tatoeba_corpus import digest
from train_phrase_model import reverse_codes
from train_candidate_ranker import matches
from evaluate_sentence_ranker import evaluate


class SentenceRankingTest(unittest.TestCase):
    def test_boundaries_skips_and_unknown_unicode(self):
        weights = stored_weights({'K|你|2|咗': .7, 'W|𠮩𠹌': .75})
        self.assertAlmostEqual(correction(weights, '你交', '咗錢'), .7)
        self.assertEqual(correction(weights, '你交，', '咗錢'), 0)
        self.assertEqual(correction(weights, '你交', 'abc咗錢'), 0)
        self.assertEqual(correction(weights, '𠮩', '𠹌'), .75)
        self.assertEqual(correction(weights, '', '未知名字'), 0)
        self.assertEqual(features('', '唔唔唔唔唔唔')['W|唔唔'], 2)
        self.assertIn('K|你|2|未', features('', '你' + chr(0x33468) + '未'))

    def test_ordering_and_determiner_roles_are_not_open_class(self):
        self.assertEqual(role('先'), 'M')
        self.assertEqual(role('啲'), 'B')
        self.assertIn('R|O|2|M', features('', '訊息先覆你'))
        self.assertNotIn('R|O|2|O', features('', '訊息先覆你'))

    def test_encoding_is_deterministic_and_correction_bounded(self):
        a = {'W|研究': 1.5, 'W|一下': 1.5, 'E|下': 1.5}
        self.assertEqual(encode(a), encode(dict(reversed(list(a.items())))))
        self.assertEqual(correction(a, '', '研究一下研究一下'), 3)
        self.assertEqual(correction(a, '', '研究一下', 0), 0)

    def test_frozen_cases_are_reachable_and_sources_disjoint(self):
        m = json.loads((DATA / 'manifest.json').read_text()); reverse = reverse_codes()
        train = [s.split('\t') for s in (DATA / 'train.tsv').read_text().splitlines()]
        held = [s.split('\t') for s in (DATA / 'fresh_natural.tsv').read_text().splitlines()]
        self.assertEqual(digest(DATA / 'train.tsv'), m['training_case_sha256'])
        self.assertEqual(digest(DATA / 'fresh_natural.tsv'), m['fresh_natural_sha256'])
        for _, context, code, text in train: self.assertTrue(matches(code, text, reverse))
        for context, code, text in held: self.assertTrue(matches(code, text, reverse))
        self.assertFalse({s[3] for s in train} & {s[2] for s in held})
        self.assertFalse(set(m['allowed_sources']) & set(m['fresh_natural_sources']))

    def test_preparation_reproduces_cases_without_decoder_results(self):
        source = Path('/tmp/hkcancor-utf8.zip')
        if not source.exists(): self.skipTest('Pinned public corpus not available')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory); prepare(source, output)
            for name in ('train.tsv', 'fresh_natural.tsv', 'manifest.json'):
                self.assertEqual((DATA / name).read_bytes(), (output / name).read_bytes(), name)

    def test_followup_is_reproducible_and_excludes_prior_fresh_targets(self):
        source = Path('/tmp/hkcancor-utf8.zip')
        if not source.exists(): self.skipTest('Pinned public corpus not available')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory); prepare_followup(source, output)
            for name in ('fresh_followup.tsv','followup-manifest.json'):
                self.assertEqual((DATA / name).read_bytes(), (output / name).read_bytes())
        first = [s.split('\t')[2] for s in (DATA / 'fresh_natural.tsv').read_text().splitlines()]
        later = [s.split('\t')[2] for s in (DATA / 'fresh_followup.tsv').read_text().splitlines()]
        self.assertEqual(len(later),100)
        self.assertFalse(any(a in b or b in a for a in first for b in later))

    def test_supported_winner_stays_first_and_other_candidates_still_reorder(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);scored=path/'scored.tsv'
            scored.write_text('guard:test\t\tabcd\t你交咗\t1\t你交咗|係交咗|佢交咗\t'+
                              '|'.join(x.hex() for x in (0.0,-1.0,-2.0))+'\t'+
                              '|'.join(x.hex() for x in (1.0,0.0,1.0))+'\n')
            evaluate({'S|佢':1.5},scored,1,path/'output')
            fields=(path/'output/test-1.tsv').read_text().strip().split('\t')
            self.assertEqual(fields[-1],'你交咗|佢交咗|係交咗')

    def test_misattributed_excluded_conversation_cannot_train(self):
        source=Path('/tmp/hkcancor-utf8.zip')
        if not source.exists(): self.skipTest('Pinned public corpus not available')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);manifest=json.loads((DATA/'manifest.json').read_text())
            invalid='train:hk:utf8/FC-005b_v2:0000000000000000'
            case=invalid+'\t\tofvdkb\t你好有\n';(path/'train.tsv').write_text(case)
            manifest['allowed_sources']=[invalid];manifest['training_case_sha256']=digest(path/'train.tsv')
            (path/'manifest.json').write_text(json.dumps(manifest))
            (path/'protocol.json').write_text((DATA/'protocol.json').read_text())
            scored=path/'scored.tsv';scored.write_text(case.rstrip('\n')+'\t1\t你好有\t0x0.0p0\n')
            with self.assertRaisesRegex(ValueError,'Non-training or misattributed'):
                read_pairs(scored,source,path)


if __name__ == '__main__': unittest.main()
