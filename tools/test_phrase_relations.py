"""Behavioral and source-isolation checks for phrase relation training."""
import json
import unittest
from phrase_relation_features import features,category,encode
from prepare_phrase_relations import gram_index,overlap
from train_phrase_relations import DATA,check_inputs

class PhraseRelationsTest(unittest.TestCase):
    def test_food_person_and_equipment_do_not_follow_misleading_suffixes(self):
        self.assertEqual(category('花生'),'F');self.assertEqual(category('司機'),'H')
        self.assertEqual(category('錢包'),'G');self.assertEqual(category('薪水'),'G')
        f=features('','我買咗碟豬腸粉',{'買':['V',2]})
        self.assertIn('CN|碟|F',f);self.assertIn('VO|買|F',f)

    def test_question_and_preverb_negation_have_different_relations(self):
        lex={'交':['V',2]}
        self.assertIn('VQ|交|Y',features('','你交功課未',lex))
        self.assertNotIn('VQ|交|Y',features('','你未交功課',lex))
        self.assertIn('NV|未|交',features('','你未交功課',lex))

    def test_context_resets_without_banning_unknown_words(self):
        lex={'交':['V',2]}
        self.assertIn('VO|交|D',features('你交','功課',lex))
        self.assertNotIn('VO|交|D',features('你交，','功課',lex))
        self.assertTrue(features('','龘龘',{}))
        self.assertTrue(all(v<=2 for v in features('','你交功課'*20,lex).values()))

    def test_frozen_sources_evaluation_and_lexicon_cannot_change_silently(self):
        manifest,_=check_inputs()
        self.assertEqual(manifest['training_cases'],5381)
        self.assertEqual(manifest['additional_hk'],2000);self.assertEqual(manifest['additional_ud'],300)
        self.assertFalse(set(manifest['source_splits']['hk_training'])&set(manifest['source_splits']['hk_excluded']))
        rows=[s.split('\t') for s in (DATA/'train.tsv').read_text().splitlines()]
        index=gram_index({r[3] for r in rows})
        validation=[s.split('\t')[3] for s in (DATA/'validation.tsv').read_text().splitlines()]
        held=[s.split('\t')[3] for s in (DATA/'heldout.tsv').read_text().splitlines()]
        self.assertTrue(all(not overlap(t,index) for t in validation+held))
        self.assertTrue(all(not overlap(t,gram_index(validation)) for t in held))
        for r in rows:
            self.assertTrue(r[0].startswith('train:'))
            if r[0].startswith('train:ud:'):self.assertLessEqual(int(r[0].rsplit(':',1)[1].split('-')[0]),547)

    def test_binary_export_is_reproducible_and_rejects_invalid_weights(self):
        lex=json.loads((DATA/'lexicon.json').read_text());weights={'VO|食|F':.2}
        self.assertEqual(encode(lex,weights,.5),encode(lex,weights,.5))
        with self.assertRaises(ValueError):encode(lex,{'VO|食|F':float('nan')},.5)

if __name__=='__main__':unittest.main()
