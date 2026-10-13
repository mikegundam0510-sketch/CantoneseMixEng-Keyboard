import json
from pathlib import Path
import tempfile
import unittest

from prepare_sentence_search import DATA, prepare, prepare_reserve
from prepare_tatoeba_corpus import digest
from sentence_features import features
from train_sentence_ranker import encode_additive, correction
from train_candidate_ranker import matches
from train_phrase_model import reverse_codes


class SentenceSearchTest(unittest.TestCase):
    def test_separate_short_and_long_caps_preserve_base_at_zero(self):
        weights={'W|研究':1.5,'W|一下':1.5,'E|下':1.5,'L|研究|s|下':1.5}
        # A frozen short correction is retained exactly with added channel off.
        self.assertEqual(correction(weights,'','研究一下',1.5,3,0),4.5)
        self.assertEqual(correction(weights,'','研究一下',1.5,3,.25),4.775)
        weights['L|你|l|未']=1.5
        self.assertEqual(correction(weights,'','你交咗所有嗰啲功課未',1.5,3,.25),.275)
        self.assertEqual(encode_additive(weights),encode_additive(dict(reversed(list(weights.items())))))
        self.assertEqual(correction({'L|你|l|未':-1.5},'','你交咗所有嗰啲功課未',1.5,3,.25),0)

    def test_frozen_new_cases_are_reachable_and_disjoint(self):
        manifest=json.loads((DATA/'manifest.json').read_text());reverse=reverse_codes()
        rows={name:[s.split('\t') for s in (DATA/(name+'.tsv')).read_text().splitlines()]
              for name in ('train','validation','heldout')}
        self.assertEqual(digest(DATA/'train.tsv'),manifest['training_case_sha256'])
        for name in ('validation','heldout'):
            self.assertEqual(len(rows[name]),100)
            self.assertEqual(digest(DATA/(name+'.tsv')),manifest[name+'_sha256'])
        for values in rows.values():
            for row in values:self.assertTrue(matches(row[-2],row[-1],reverse))
        surfaces={name:{r[-1] for r in values} for name,values in rows.items()}
        for a,b in (('train','validation'),('train','heldout'),('validation','heldout')):
            self.assertFalse(surfaces[a]&surfaces[b])

    def test_new_preparation_reproduces_frozen_inputs(self):
        source=Path('/tmp/hkcancor-utf8.zip')
        if not source.exists():self.skipTest('Pinned public corpus unavailable')
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory);prepare(source,output)
            for name in ('train.tsv','validation.tsv','heldout.tsv','manifest.json'):
                self.assertEqual((DATA/name).read_bytes(),(output/name).read_bytes(),name)

    def test_second_reserve_reproduces_and_excludes_first_targets(self):
        source=Path('/tmp/hkcancor-utf8.zip')
        if not source.exists():self.skipTest('Pinned public corpus unavailable')
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory);prepare_reserve(source,output)
            for name in ('reserve.tsv','reserve-manifest.json'):
                self.assertEqual((DATA/name).read_bytes(),(output/name).read_bytes(),name)
        older={s.split('\t')[-1] for name in ('train','validation','heldout')
               for s in (DATA/(name+'.tsv')).read_text().splitlines()}
        reserve={s.split('\t')[-1] for s in (DATA/'reserve.tsv').read_text().splitlines()}
        self.assertEqual(len(reserve),100)
        self.assertFalse(any(a in b or b in a for a in older for b in reserve))


if __name__=='__main__':unittest.main()
