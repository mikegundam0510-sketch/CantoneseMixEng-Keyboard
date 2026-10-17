"""Finite differences through masked edge softmax, both RNNs and pair loss."""
import unittest
import numpy as np
from model import NAMES,Codec,batch,forward,loss_gradient,pair_gradient,decode,step,code_states


class GeneratorMath(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(41);d,h,c,size=3,2,2,6
        shapes=[(size,d),(d,3*h),(h,3*h),(3*h,),(size,h),(size,c),(size,),
            (27,c),(c,c),(h,2),(c,2),(2,)]
        self.v={k:rng.normal(0,.15,s) for k,s in zip(NAMES,shapes)};self.v['embedding'][0]=0;self.v['code_embedding'][0]=0
        self.codec=Codec(['丙','乙','甲'],{'甲':['aa','a'],'乙':['aa','b'],'丙':['bb','ab']})
        self.rows=[dict(context='乙',code='aabb',text='甲丙',positive='甲丙',negative='乙丙'),
                   dict(context='',code='ab',text='甲乙',positive='甲乙',negative='丙')]
    def gradients(self,pair):
        v=self.v;codec=self.codec;weights=np.array([.7,1.3])
        packed=batch(self.rows,codec)
        def objective():
            return pair_gradient(v,batch(self.rows,codec,'positive'),batch(self.rows,codec,'negative'),codec,weights) if pair else loss_gradient(v,packed,codec,weights)
        loss,grad=objective();self.assertTrue(np.isfinite(loss))
        rng=np.random.default_rng(17)
        for k in NAMES:
            for index in rng.choice(v[k].size,min(4,v[k].size),replace=False):
                at=np.unravel_index(index,v[k].shape)
                if k in ('embedding','code_embedding') and at[0]==0:continue
                before=v[k][at];eps=1e-5
                v[k][at]=before+eps;a=objective()[0];v[k][at]=before-eps;b=objective()[0];v[k][at]=before
                self.assertAlmostEqual((a-b)/(2*eps),grad[k][at],delta=2e-6,msg=k+str(at))
    def test_teacher_gradients(self):self.gradients(False)
    def test_pair_gradients(self):self.gradients(True)
    def test_complete_legal_decode(self):
        result=decode(self.v,self.codec,'aabb',beam=24)
        self.assertTrue(result);self.assertLessEqual(len(result),20)
        self.assertEqual(len(result),len({t for t,s in result}))
        for text,score in result:self.assertIsNotNone(self.codec.align('aabb',text));self.assertTrue(np.isfinite(score))
        self.assertEqual(decode(self.v,self.codec,'123'),[])
        self.assertEqual(decode(self.v,self.codec,'zz'),[])
    def test_remaining_code_conditions_first_prediction(self):
        states=[]
        for code in ['aaaa','aabb']:
            e=code_states(self.v,np.array([[ord(c)-96 for c in code]]))[0,0]
            ids,lens=self.codec.edges(code,0)
            states.append((self.v['word_c'][ids]+self.v['length_c'].T[lens])@e)
        self.assertGreater(np.max(np.abs(states[0]-states[1])),1e-8)
    def test_hybrid_preserves_head_and_unsupported_slots(self):
        from evaluate import hybrid
        parent=['甲丙','乙丙','字丙']
        result=hybrid(self.v,self.codec,'aabb','',parent,decode(self.v,self.codec,'aabb'))
        self.assertEqual(result[0],parent[0]);self.assertEqual(result[2],parent[2])
        self.assertLessEqual(len(result),20);self.assertEqual(len(result),len(set(result)))
    def test_teacher_sequence_probability(self):
        row=self.rows[0];score,_=forward(self.v,batch([row],self.codec),self.codec)
        cs=code_states(self.v,np.array([[ord(c)-96 for c in row['code']]]))[0]
        h=np.zeros(2);total=0.;pos=0
        for token in [2]+[self.codec.vocab[c] for c in row['context']]:h=step(self.v,token,h)[0]
        for char,n in zip(row['text'],self.codec.align(row['code'],row['text'])):
            ids,lens=self.codec.edges(row['code'],pos)
            logits=(self.v['word_h'][ids]+self.v['length_h'].T[lens])@h+(self.v['word_c'][ids]+self.v['length_c'].T[lens])@cs[pos]+self.v['word_bias'][ids]+self.v['length_bias'][lens]
            target=np.flatnonzero((ids==self.codec.vocab[char])&(lens==n-1))[0]
            total+=logits[target]-np.logaddexp.reduce(logits);h=step(self.v,self.codec.vocab[char],h)[0];pos+=n
        self.assertAlmostEqual(score[0],total/len(row['code']),places=10)


if __name__=='__main__':unittest.main()
