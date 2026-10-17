#!/usr/bin/env python3
"""Gradient, causal distribution, serialization and data separation checks."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

from sentence_language_model import initialize, paths, batch, forward, lm_gradient, pair_gradient, save, read, encode
from prepare_sentence_pretrain import split, group
from train_phrase_model import ROOT, reverse_codes
from train_candidate_ranker import matches
from prepare_clean_ranking import rules, spans
from prepare_phrase_relations import gram_index, overlap

CACHE = ROOT/'.native/sentence-pretrain-20261017/data'


def fixture():
    rows = [dict(text=text, family='f'+str(i), context='') for i in range(3)
            for text in ('你唔使返工未', '你使唔返工未')]
    v,c,t,p = initialize(rows, 3, 3)
    rng = np.random.default_rng(42)
    v = {k:x.astype(np.float64) for k,x in v.items()}
    v['output'][:] = rng.normal(0,.1,v['output'].shape)
    return rows,v,c,t,p


class SentencePretraining(unittest.TestCase):
    def test_next_character_and_pair_gradients(self):
        rows,v,c,t,p = fixture(); vocabulary={c:i+3 for i,c in enumerate(c)}
        tp=paths(t,len(p)); positive=batch(rows[:2],vocabulary)
        negative=batch([dict(text='你返工唔使未'),dict(text='你唔返工使未')],vocabulary)
        w=np.array([.8,1.2]); offset=np.array([.1,-.2])
        calls=[lambda:lm_gradient(v,*positive,tp,p,w), lambda:pair_gradient(v,positive,negative,tp,p,offset,w)]
        coordinates={'embedding':[(3,0),(4,1)],'input':[(0,0),(1,7)],'recurrent':[(0,1),(1,8)],
                     'bias':[(0,),(4,),(8,)],'output':[(0,1),(2,2)],'output_bias':[(0,),(2,)]}
        for call in calls:
            loss,grad=call(); self.assertTrue(np.isfinite(loss))
            for name,indices in coordinates.items():
                for at in indices:
                    old=v[name][at];eps=1e-5
                    v[name][at]=old+eps; a=call()[0]
                    v[name][at]=old-eps; b=call()[0];v[name][at]=old
                    self.assertAlmostEqual((a-b)/(2*eps),grad[name][at],delta=3e-7,msg=name+str(at))

    def test_hierarchical_probabilities_sum_to_one_and_initial_score_neutral(self):
        rows,_,c,_,_=fixture();v,c,t,p=initialize(rows,3,3);vocabulary={c:i+3 for i,c in enumerate(c)}
        targets=[dict(text=c) for c in c]+[dict(text='𠀀')]
        score,nll=forward(v,*batch(targets,vocabulary),paths(t,len(p)),p)
        self.assertAlmostEqual(float(np.exp(-nll).sum()),1.,places=6)
        np.testing.assert_allclose(score,0,atol=2e-6)

    def test_padding_and_past_context_boundaries(self):
        rows,v,c,t,p=fixture();vocabulary={c:i+3 for i,c in enumerate(c)};tp=paths(t,len(p))
        a=batch(rows[:1],vocabulary);b=(np.pad(a[0],((0,0),(0,4))),np.pad(a[1],((0,0),(0,4))))
        for left,right in zip(forward(v,*a,tp,p),forward(v,*b,tp,p)):np.testing.assert_allclose(left,right,atol=1e-12)
        self.assertEqual(encode('中文abc𠀀','你',{'𠀀':3,'你':4}),([2,3,4],1))
        self.assertEqual(encode('甲'*20,'你',{'甲':3,'你':4}),([2]+[3]*12+[4],12))

    def test_binary_roundtrip(self):
        _,v,c,t,p=fixture();v={k:x.astype(np.float32) for k,x in v.items()}
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';save(a,v,c,t,p);save(b,v,c,t,p)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            actual,chars,tree,prior,strength=read(a)
            self.assertEqual(chars,c);self.assertEqual(strength,.5)
            np.testing.assert_array_equal(tree,t);np.testing.assert_array_equal(prior,p)
            for k in v:np.testing.assert_array_equal(v[k],actual[k])

    def test_family_separation_shared_by_both_stages(self):
        corpus=[json.loads(s) for s in gzip.decompress((CACHE/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
        pairs=[json.loads(s) for s in gzip.decompress((CACHE/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
        families={s:{r['family'] for r in corpus+pairs if r['split']==s} for s in ('train','validation')}
        self.assertFalse(families['train']&families['validation'])
        for r in corpus+pairs:self.assertEqual(split(r['family']),r['split'])
        self.assertTrue(all(r['split']=='train' for r in corpus if r['domain']=='CV'))
        self.assertEqual(group('train:authored:train:delivery:3'),'authored:delivery')
        self.assertGreater(sum(r['domain']=='CV' for r in corpus),10000)

    def test_adaptation_candidates_have_exact_codes_and_licensed_train_membership(self):
        pairs=[json.loads(s) for s in gzip.decompress((CACHE/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
        allowed={tuple(s.split('\t')[1:]) for s in (ROOT/'tools/data/clean_ranking/train.tsv').read_text().splitlines()}
        reverse=reverse_codes()
        for r in pairs:
            self.assertIn((r['context'],r['code'],r['positive']),allowed)
            self.assertTrue(matches(r['code'],r['negative'],reverse))
            self.assertTrue(-4<=r['offset']<=4)

    def test_external_target_containment_excluded_from_both_stages(self):
        corpus=[json.loads(s) for s in gzip.decompress((CACHE/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
        pairs=[json.loads(s) for s in gzip.decompress((CACHE/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
        texts=[r['text'] for r in corpus]
        texts.extend(r['context']+r[k] for r in pairs for k in ('positive','negative'))
        index=gram_index(texts);mapping=rules()
        for split_name in ('validation','heldout'):
            for line in (ROOT/'tools/data/context_search'/(split_name+'.tsv')).read_text().splitlines():
                target=line.split('\t')[3]
                self.assertFalse(overlap(target,index))
                for _,_,normalized,_ in spans(target,mapping):self.assertFalse(overlap(normalized,index))


if __name__ == '__main__':unittest.main()
