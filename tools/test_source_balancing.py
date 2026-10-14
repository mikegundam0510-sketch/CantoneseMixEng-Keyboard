"""Corpus balancing must not turn repeated family variants into more evidence."""
from collections import Counter
import unittest
from train_candidate_ranker import learn


class SourceBalancingTest(unittest.TestCase):
    def setUp(self):
        self.pairs=[('train:hk:dialogue','','aaaa','甲甲','乙乙',0),
                    ('train:daily:template','','aaaa','甲甲','乙乙',0),
                    ('train:authored:legacy','','aaaa','甲甲','乙乙',0)]
        self.pairs += [(f'train:tatoeba:family{i}','','bbbb','乙乙','甲甲',0) for i in range(8)]
        self.mix={'train:hk:':.5,'train:tatoeba:':.25,'train:daily:|train:authored:':.25}

    def test_large_corpus_cannot_override_explicit_source_shares(self):
        default,_=learn(self.pairs,min_count=1)
        balanced,report=learn(self.pairs,min_count=1,source_mix=self.mix)
        self.assertLess(default['甲甲'],0)
        self.assertGreater(balanced['甲甲'],0)
        self.assertEqual(report['source_balance']['desired_mix'],self.mix)

    def test_duplicate_pairs_do_not_increase_family_or_corpus_mass(self):
        before,report=learn(self.pairs,min_count=3,source_mix=self.mix)
        after,duplicated=learn(self.pairs+[self.pairs[0]]*7,min_count=3,source_mix=self.mix)
        self.assertEqual(report['features_supported'],duplicated['features_supported'])
        self.assertEqual(set(before),set(after))
        for key in before:self.assertAlmostEqual(before[key],after[key],places=10)

    def test_ambiguous_or_missing_source_groups_are_rejected(self):
        for mix in ({'train:':.5,'train:hk:':.5},{'train:hk:':1},
                    {**self.mix,'train:unknown:':.1}):
            with self.subTest(mix=mix),self.assertRaises(ValueError):
                learn(self.pairs,min_count=1,source_mix=mix)


if __name__=='__main__':unittest.main()
