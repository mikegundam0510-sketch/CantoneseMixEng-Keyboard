"""Meaningful frozen-row, legal-generation and weighting regression checks."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
from expanded_model import initialize,assert_frozen,update,ROW_KEYS,Codec,batch,loss_gradient,decode,save,load
from fit_expansion import balanced

class ExpansionChecks(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(17);size,h,c=5,3,2
        self.old=dict(embedding=rng.normal(0,.1,(size,h)),input=rng.normal(0,.1,(h,3*h)),
            recurrent=rng.normal(0,.1,(h,3*h)),bias=np.zeros(3*h),word_h=rng.normal(0,.1,(size,h)),
            word_c=rng.normal(0,.1,(size,c)),word_bias=np.zeros(size),code_embedding=rng.normal(0,.1,(27,c)),
            code_recurrent=rng.normal(0,.1,(c,c)),length_h=np.zeros((h,2)),length_c=np.zeros((c,2)),length_bias=np.zeros(2))
        self.old={k:np.asarray(v,np.float32) for k,v in self.old.items()}
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'parent.npz';save(self.path,self.old,['乙','甲'])
        self.characters=['丙','乙','甲','𠝹'];self.counts={'丙':2,'𠝹':3}
    def test_old_rows_and_shared_bits_survive_reindex(self):
        v,parent,oldids,newids=initialize(self.path,self.characters,self.counts)
        assert_frozen(v,parent,oldids)
        self.assertEqual(list(oldids),[0,1,2,4,5]);self.assertEqual(list(newids),[3,6])
        for a in v.values():self.assertTrue(np.isfinite(a).all())
    def test_real_gradient_updates_only_new_rows(self):
        v,parent,oldids,newids=initialize(self.path,self.characters,self.counts)
        codec=Codec(self.characters,{'丙':['aa'],'乙':['aa'],'甲':['bb'],'𠝹':['bb']})
        row=dict(context='乙',code='aabb',text='丙𠝹')
        loss,grad=loss_gradient(v,batch([row],codec),codec,np.ones(1,np.float32))
        before={k:a.copy() for k,a in v.items()};m={k:np.zeros_like(v[k][newids]) for k in ROW_KEYS};var={k:a.copy() for k,a in m.items()}
        update(v,grad,newids,m,var,1);assert_frozen(v,parent,oldids)
        self.assertTrue(any(not np.array_equal(v[k][newids],before[k][newids]) for k in ROW_KEYS))
        self.assertTrue(np.isfinite(loss))
    def test_new_character_is_a_legal_output(self):
        v,parent,oldids,newids=initialize(self.path,self.characters,self.counts)
        codec=Codec(self.characters,{'丙':['aa'],'乙':['aa'],'甲':['bb'],'𠝹':['bb']})
        oldcodec=Codec(['乙','甲'],{'乙':['aa'],'甲':['bb']})
        self.assertIsNone(oldcodec.align('aabb','丙𠝹'));self.assertIsNotNone(codec.align('aabb','丙𠝹'))
        v['word_bias'][3]=20;v['word_bias'][6]=20
        actual=decode(v,codec,'aabb')
        self.assertEqual(actual[0][0],'丙𠝹')
        for t,s in actual:self.assertIsNotNone(codec.align('aabb',t))
    def test_old_characters_cannot_be_deleted(self):
        with self.assertRaises(ValueError):initialize(self.path,['丙','甲'],{'丙':2})
    def test_half_mass_for_addition_and_protection(self):
        rows=[dict(family=str(i),domain='HK',kind='protection',text='甲乙') for i in range(5)]
        rows.append(dict(family='new',domain='HK',kind='addition',text='丙甲'))
        w=balanced(rows);self.assertAlmostEqual(float(sum(w[:5])),float(w[5]),places=5)
    def test_masked_optimizer_is_detected_if_it_touches_old(self):
        v,parent,oldids,newids=initialize(self.path,self.characters,self.counts)
        v['word_bias'][4]+=.1
        with self.assertRaises(ValueError):assert_frozen(v,parent,oldids)

if __name__=='__main__':unittest.main()
