#!/usr/bin/env python3
"""Numerical derivatives, masks, serialization and TRAIN-only recurrent data."""
import json
import gzip
from pathlib import Path
import tempfile
import unittest
import numpy as np

from context_gru import initialize,forward,loss_gradient,padded,save,read,encode,tail
from prepare_clean_ranking import rules,spans
from prepare_phrase_relations import gram_index,overlap
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT,reverse_codes
from train_candidate_ranker import matches


class RecurrentReference(unittest.TestCase):
    def test_gradient_matches_finite_differences(self):
        values={k:v.astype(np.float64) for k,v in initialize(7,2,2,42).items()}
        pos=padded([[2,3,4],[2,4]]);neg=padded([[2,4,3],[2,5]])
        offset=np.array([.1,-.2]);weights=np.array([.8,1.2])
        loss,grad=loss_gradient(values,pos,neg,offset,weights,l2=.0001)
        self.assertTrue(np.isfinite(loss))
        for name,indices in {'embedding':[(3,0),(4,1)],'input':[(0,0),(1,4)],'recurrent':[(0,1),(1,5)],'bias':[(0,),(3,),(5,)],'output':[(0,)],'output_bias':[(0,)]}.items():
            for at in indices:
                old=values[name][at];eps=1e-5
                values[name][at]=old+eps;a=loss_gradient(values,pos,neg,offset,weights,l2=.0001)[0]
                values[name][at]=old-eps;b=loss_gradient(values,pos,neg,offset,weights,l2=.0001)[0]
                values[name][at]=old
                self.assertAlmostEqual((a-b)/(2*eps),grad[name][at],delta=2e-7,msg=name+str(at))

    def test_padding_does_not_change_scores(self):
        values=initialize(7,3,3)
        self.assertAlmostEqual(float(forward(values,np.array([[2,3,4]]))[0]),float(forward(values,np.array([[2,3,4,0,0]]))[0]),places=7)

    def test_order_and_longer_history_are_represented(self):
        values=initialize(9,3,3)
        a=forward(values,np.array([[2,3,4,5,6,7,8],[2,4,3,5,6,7,8]]))
        self.assertGreater(abs(float(a[0]-a[1])),1e-7)

    def test_context_boundaries_and_supplementary_encoding(self):
        self.assertEqual(tail('abcdefghijkl香港'),'香港')
        self.assertEqual(tail('甲'*20),'甲'*12)
        self.assertEqual(encode('你好，𠀀','香港',{'𠀀':3,'香':4,'港':5}),[3,2,4,5])

    def test_binary_roundtrip_is_exact(self):
        values=initialize(6,3,3);chars=list('你好港')
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.b64';b=Path(folder)/'b.b64';save(a,values,chars,.5);save(b,values,chars,.5)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            actual,actual_chars,cap,strength=read(a)
            self.assertEqual(actual_chars,chars);self.assertEqual((cap,strength),(2,.5))
            for k in values:np.testing.assert_array_equal(values[k],actual[k])

    def test_only_licensed_final_train_pairs_and_family_disjoint_internal_split(self):
        data=ROOT/'tools/data/context_neural';manifest=json.loads((data/'manifest.json').read_text())
        self.assertEqual(digest(data/'pairs.jsonl.gz'),manifest['pairs_sha256'])
        self.assertEqual(digest(ROOT/manifest['pair_source']),manifest['pair_source_sha256'])
        rows=[json.loads(s) for s in gzip.decompress((data/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
        allowed={tuple(s.split('\t')[1:]) for s in (ROOT/'tools/data/clean_ranking/train.tsv').read_text().splitlines()}
        families={split:{r['family'] for r in rows if r['split']==split} for split in ('train','validation')}
        self.assertFalse(families['train']&families['validation']);reverse=reverse_codes();trained=set()
        for r in rows:
            self.assertIn((r['context'],r['code'],r['positive']),allowed)
            self.assertTrue(matches(r['code'],r['negative'],reverse));self.assertTrue(-4<=r['offset']<=4)
            trained.update((r['positive'],r['negative']))
        mapping=rules();trained.update(t for text in list(trained) for _,_,t,_ in spans(text,mapping) if len(t)>=6)
        index=gram_index(trained)
        for split in ('validation','heldout'):
            for line in (ROOT/'tools/data/context_search'/(split+'.tsv')).read_text().splitlines():
                text=line.split('\t')[3];self.assertFalse(overlap(text,index))


if __name__=='__main__':unittest.main()
