import unittest
import base64
import gzip
from encode_head_promotion import encode
from train_aligned_relations import encode_aligned
from evaluate_head_promotion import evidence, trusted, simulate
from train_head_promotion import gate_margin


class HeadPromotionTest(unittest.TestCase):
    def test_head_encoding_preserves_tail_weights_and_rejects_invalid_parameters(self):
        base=encode_aligned({'交':['V',2]},{'VO|交|D':.2},1)
        old=gzip.decompress(base64.b64decode(base))
        new=gzip.decompress(base64.b64decode(encode(base,.5,.5,{'SV|你|交':.3},1.5)))
        self.assertEqual(old[4:20],new[4:20])
        self.assertEqual(old[20:],new[28:28+len(old)-20])
        for margin,lift,strength in [(float('nan'),.5,1),(.5,1.1,1),(.5,.5,1.6)]:
            with self.assertRaises(ValueError):encode(base,margin,lift,{},strength)
        with self.assertRaises(ValueError):encode(base,.5,.5,{'VO|交|D':float('nan')},1)
    def test_actual_gate_gradient_includes_raw_and_clipped_score_thresholds(self):
        for d,g,label in [(.2,1,1),(.3,-1,1),(3,-4,1),(-3,1,-1),(.2,2,-1)]:
            _,expected=gate_margin(d,g,label)
            numerical=(gate_margin(d+1e-6,g,label)[0]-gate_margin(d-1e-6,g,label)[0])/2e-6
            self.assertAlmostEqual(expected,numerical,places=7)
    def test_negation_alone_does_not_override_an_equally_supported_head(self):
        head=(0,{'a','b'},set(),{'subject','object'})
        negative=(2,{'a','b','n'},set(),{'subject','object','negation'})
        self.assertFalse(trusted(negative,head,.5))
        self.assertFalse(trusted((2,{'x'},set(),{'subject'}),head,.5))

    def test_supported_swap_preserves_membership_and_personal_reference_order(self):
        values=['係交功課未','你交功課未','我交功課未','你未交功課','佢未交功課','佢交功課未']
        row=dict(source='calibration',context='',code='unused',gold=values[1],values=values,
                 adjusted={v:float(10-i) for i,v in enumerate(values)})
        row['adjusted'][values[1]]=12
        weights={'SV|你|交':1,'VO|交|D':1,'VQ|交|Y':1}
        lex={'交':['V',2],'功課':['N',2]}
        result,changes=simulate([row],weights,lex,.5,.5,{})
        self.assertEqual(result['calibration']['top1'],1)
        self.assertEqual(changes[0]['new_head'],values[1])
        # Gold text audits the result and never selects the promoted text.
        row['gold']=values[-1]
        _,other=simulate([row],weights,lex,.5,.5,{})
        self.assertEqual(other[0]['new_head'],values[1])
        row['values']=values[:1]+values[2:]+values[1:2];row['gold']=values[1];orders=[]
        result,_=simulate([row],weights,lex,.5,.5,{},orders=orders)
        self.assertEqual(result['calibration']['top1'],1)
        self.assertEqual(orders[0][:2],[values[1],values[0]])
        self.assertEqual(set(orders[0]),set(values))

    def test_unknown_word_role_is_not_adverse_evidence(self):
        _,_,negative,_=evidence('','龘龘',{'G|OO':-1}, {})
        self.assertFalse(negative)

    def test_numeral_intent_is_preserved_despite_stronger_structural_evidence(self):
        values=['三流','你交功課未']
        row=dict(source='calibration',context='',code='unused',gold=values[0],values=values,adjusted={values[0]:0,values[1]:100})
        result,changes=simulate([row],{'SV|你|交':1,'VO|交|D':1,'VQ|交|Y':1},{'交':['V',2],'功課':['N',2]},.5,.5,{})
        self.assertEqual(result['calibration']['top1'],1);self.assertFalse(changes)


if __name__=='__main__':unittest.main()
