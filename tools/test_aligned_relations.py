import base64
import gzip
import struct
import unittest
from train_aligned_relations import actual_margin,margin_derivatives,encode_aligned
from phrase_relation_features import encode

class AlignedRelationsTest(unittest.TestCase):
    def test_actual_gradient_matches_finite_difference_including_reference(self):
        for raw in [(.4,-.3,.1),(3,.2,0),(.2,-3,0),(4,-4,0)]:
            derivatives=margin_derivatives(*raw)
            for i,expected in enumerate(derivatives):
                left=list(raw);right=list(raw);left[i]-=1e-5;right[i]+=1e-5
                numerical=(actual_margin(-.7,*right)-actual_margin(-.7,*left))/2e-5
                self.assertAlmostEqual(expected,numerical,places=8)

    def test_clipped_objective_cannot_claim_an_unbounded_promotion(self):
        self.assertEqual(actual_margin(-7,100,-100,0),-3)
        self.assertEqual(margin_derivatives(100,-100,0),(0,0,0))
        self.assertEqual(actual_margin(-.5,.5,0,0),0)

    def test_new_format_retains_original_payload_and_reproducible_encoding(self):
        lex={'食':['V',2]};weights={'VO|食|F':.2}
        old=gzip.decompress(base64.b64decode(encode(lex,weights,.5)))
        new=gzip.decompress(base64.b64decode(encode_aligned(lex,weights,.5)))
        self.assertEqual(struct.unpack('>I',new[:4])[0],0x50525232)
        self.assertEqual(old[4:],new[4:])
        self.assertEqual(encode_aligned(lex,weights,.5),encode_aligned(lex,weights,.5))

if __name__=='__main__':unittest.main()
