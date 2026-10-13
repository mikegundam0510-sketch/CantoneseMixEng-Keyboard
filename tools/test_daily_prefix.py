import json
from pathlib import Path
import tempfile
import unittest
from prefix_features import features,encode
from prepare_daily_prefix_data import DATA,prepare,extracts
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import reverse_codes
from train_prefix_ranker import read_pairs
from train_prefix_ranker import train

class DailyPrefixTest(unittest.TestCase):
    def test_hints_are_bounded_and_context_resets(self):
        f=features('英文abc你','交咗',['份報告','份文件','同事'])
        self.assertIn('K|你|2|咗',f)
        self.assertIn('B|0|咗|份報',f)
        self.assertIn('B|1|交咗|同事',f)
        self.assertNotIn('K|你|2|咗',features('你交，','咗'))
        self.assertEqual(features('我你佢'*20,'交咗'),features(('我你佢'*20)[-12:],'交咗'))
        self.assertEqual(features('','你交',['份文件']*7),features('','你交',['份文件']*6))
        self.assertTrue(all(v<=2 for v in features('','你你你你你你',['份文件']*6).values()))
        self.assertIn('W|𠮩𠹌',features('𠮩','𠹌'))
        self.assertEqual(encode({'W|返工':.5}),encode({'W|返工':.5}))

    def test_frozen_data_reachable_disjoint_and_licensed(self):
        m=json.loads((DATA/'manifest.json').read_text());reverse=reverse_codes()
        targets={};groups={}
        for name,count in (('train',3081),('validation',200),('heldout',800)):
            p=DATA/(name+'.tsv');self.assertEqual(digest(p),m['file_sha256'][p.name])
            rows=[s.split('\t') for s in p.read_text().splitlines()];self.assertEqual(len(rows),count)
            targets[name]={r[-1] for r in rows}
            for r in rows:self.assertTrue(matches(r[-2],r[-1],reverse))
        self.assertFalse(targets['validation']&targets['heldout'])
        self.assertFalse(any(a in b or b in a for a in targets['train'] for b in targets['validation']|targets['heldout']))
        for name in ('validation','heldout'):
            records=[json.loads(s) for s in (DATA/(name+'-source.jsonl')).read_text().splitlines()]
            groups[name]={r['group'] for r in records}
            self.assertEqual(len(groups[name]),len(records))
            self.assertTrue(all(any(p in r['original'] for p in '。！？!?；;') for r in records))
        self.assertFalse(groups['validation']&groups['heldout'])

    def test_preparation_reproduces_frozen_inputs(self):
        source=Path('/tmp/hk035-wordshk-tools/examples/wordshk.csv')
        if not source.exists():self.skipTest('Pinned public source unavailable')
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);prepare(source,out)
            for name in ('train.tsv','validation.tsv','heldout.tsv','manifest.json','validation-source.jsonl','heldout-source.jsonl'):
                self.assertEqual((DATA/name).read_bytes(),(out/name).read_bytes(),name)

    def test_training_rejects_evaluation_source_before_fitting(self):
        row=(DATA/'validation.tsv').read_text().splitlines()[0].split('\t')
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'bad.tsv';p.write_text('\t'.join(('validation:written',row[0],row[1],row[2],'2',row[2][:1],'你','0x0p0','','2'))+'\n')
            with self.assertRaisesRegex(ValueError,'Non-training'):read_pairs(p)

    def test_independent_translation_families_and_training_reproduce(self):
        pairs=read_pairs(DATA/'pairs.tsv')
        families={r[0] for r in pairs if r[0].startswith('train:tatoeba:')}
        self.assertGreater(len(families),500)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory);train(DATA/'pairs.tsv',output)
            for name in ('weights.json','training-report.json','prefix_ranker.b64'):
                self.assertEqual((output/name).read_bytes(),(DATA/name).read_bytes(),name)

    def test_extracts_require_terminated_sentence_and_remove_markup(self):
        self.assertEqual(list(extracts('<eg>\nyue:#你去咗邊度。 (nei5 heoi3 zo2 bin1 dou6)'))[0][1],'你去咗邊度')
        self.assertFalse(list(extracts('<eg>\nyue:你去咗邊度')))

if __name__=='__main__':unittest.main()
