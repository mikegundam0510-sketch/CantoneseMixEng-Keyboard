import base64
import gzip
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes
from train_tail_recovery import DATA,train

class TailRecoveryTest(unittest.TestCase):
    def test_pairs_are_exact_and_only_from_the_licensed_training_targets(self):
        rows=[s.split('\t') for s in (ROOT/'tools/data/phrase_relations/train.tsv').read_text().splitlines()]
        allowed={(family(s),c,code,gold) for s,c,code,gold in rows};reverse=reverse_codes()
        for model in ['005','015']:
            folder=DATA/('model'+model);report=json.loads((folder/'tail-training-report.json').read_text())
            pairs=[s.split('\t') for s in (folder/'tail-pairs.tsv').read_text().splitlines()]
            self.assertEqual(len(pairs),236);self.assertEqual(report['source_families'],41)
            for row in pairs:
                self.assertEqual(len(row),8);self.assertIn(tuple(row[:4]),allowed)
                self.assertIn(row[7],['-1','1']);self.assertTrue(math.isfinite(float.fromhex(row[6])))
                self.assertEqual(row[3],row[4] if row[7]=='1' else row[5])
                for value in row[4:6]:self.assertTrue(matches(row[2],value,reverse))
            self.assertEqual(digest(folder/'tail-pairs.tsv'),report['pairs_sha256'])
            self.assertEqual(digest(folder/'tail-weights.json'),report['weights_sha256'])
            self.assertEqual(digest(folder/'tail_ranker.b64'),report['model_sha256'])

    def test_models_are_bounded_legacy_payloads_and_optional_bundle_matches_the_fit(self):
        for model in ['005','015']:
            folder=DATA/('model'+model);payload=gzip.decompress(base64.decodebytes((folder/'tail_ranker.b64').read_bytes()))
            magic,words,count,strength,limit=struct.unpack('>IIIff',payload[:20])
            self.assertEqual(magic,0x50525231);self.assertEqual(words,5610);self.assertLessEqual(count,6000)
            self.assertEqual((strength,limit),(1.5,2))
        bundled=ROOT/'app/src/main/assets/tail_ranker.b64'
        if bundled.exists():self.assertEqual(bundled.read_bytes(),(DATA/'model015/tail_ranker.b64').read_bytes())

    def test_nontraining_observation_is_rejected_before_fitting(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);p=d/'bad.tsv';p.write_text('evaluation\t\tofvd\t你好\n')
            with self.assertRaisesRegex(ValueError,'Pinned actual native'):train(p,d/'output',.015)
            self.assertFalse((d/'output').exists())

    def test_fitted_selected_model_reproduces_byte_for_byte(self):
        observed=ROOT/'.native/search-recovery-20261015/head-observer-training.tsv'
        if not observed.exists():self.skipTest('Pinned native training observer unavailable; regenerate from fixed baseline')
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);train(observed,out,.015)
            for name in ['tail-weights.json','tail-pairs.tsv','tail_ranker.b64','tail-training-report.json']:
                self.assertEqual((out/name).read_bytes(),(DATA/'model015'/name).read_bytes(),name)

    def test_native_candidate_preserves_the_first_five_and_adds_at_most_two(self):
        before=ROOT/'tools/reports/prefix-retrieval-2026-10-15/baseline700.tsv'
        after=ROOT/'tools/reports/completion-scoring-2026-10-15/selected700.tsv'
        old=before.read_text().splitlines();new=after.read_text().splitlines();self.assertEqual(len(new),700)
        for b,a in zip(old,new):
            b=b.split('\t');a=a.split('\t');self.assertEqual(b[:4],a[:4])
            bv=b[5].split('|') if b[5] else [];av=a[5].split('|') if a[5] else []
            self.assertEqual(bv[:5],av[:5]);self.assertLessEqual(len(av),20)
            self.assertEqual(len(av),len(set(av)));self.assertLessEqual(len(set(av)-set(bv)),2)

if __name__=='__main__':unittest.main()
