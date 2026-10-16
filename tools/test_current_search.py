import base64
from collections import defaultdict
import gzip
import json
import math
import struct
import unittest

from clean_ranking_observations import cases
from observe_current_search import DATA
from train_aligned_relations import family
from train_candidate_ranker import matches
from train_current_search import encoded, features
from train_phrase_model import reverse_codes


class SharedEndpointEvidence(unittest.TestCase):
    def test_longer_order_is_distinguished(self):
        self.assertEqual(features('你交咗功','課')['你交咗功課'],1)
        self.assertNotIn('你交咗功課',features('你功咗交','課'))
        self.assertNotIn('你交咗功課',features('你交咗功','課',3))

    def test_all_token_splits_preserve_features(self):
        for context in ('','甲乙丙丁戊己','中文。香港'):
            for text in ('你交咗功課畀老細未','𠮩𠹌香港','香港。abc你好','甲'*25):
                expected=features(context,text)
                for i in range(len(text)+1):
                    self.assertEqual(expected,features(context,text[:i])+features(context+text[:i],text[i:]))

    def test_boundaries_clear_history(self):
        self.assertEqual(features('甲乙丙丁。','香港'),features('','香港'))
        self.assertNotIn('甲乙',features('甲','a乙'))

    def test_loader_header_and_weight_bounds(self):
        blob,nodes,edges=encoded({'你好':.25,'你交咗功課':-.25},.5)
        raw=gzip.decompress(base64.b64decode(blob))
        magic,length,n,e,strength,cap=struct.unpack_from('>IIIIff',raw)
        self.assertEqual((magic,length,n,e,strength),(0x57524b31,5,nodes,edges,.5))
        self.assertEqual(cap,1.5)
        self.assertLessEqual(4*.25,cap)
        for weights in ({'甲乙丙丁戊己':.1},{'你好':.26},{'你好':float('nan')}):
            with self.assertRaises(ValueError):encoded(weights,1)

    def test_only_exact_clean_training_comparisons(self):
        # This fails, rather than skipping, until the complete collection exists.
        rows=[json.loads(s) for s in gzip.decompress((DATA/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
        by_family=defaultdict(list)
        for source,context,code,gold in cases():by_family[family(source)].append((context,code,gold))
        reverse=reverse_codes();seen=set()
        for stage,fam,context,code,positive,negative,margin,origin in rows:
            self.assertIn(stage,('prefix','final'));self.assertTrue(math.isfinite(margin))
            self.assertIn(origin,('lost','survived','ordinary','shadow'))
            self.assertTrue(matches(code,positive,reverse));self.assertTrue(matches(code,negative,reverse))
            self.assertNotEqual(positive,negative)
            key=(stage,fam,context,code,positive,negative)
            self.assertNotIn(key,seen);seen.add(key)
            if stage=='final':self.assertIn((context,code,positive),by_family[fam])
            else:
                self.assertTrue(any(c==context and fullcode.startswith(code) and len(fullcode)>len(code)
                    and gold.startswith(positive) and matches(fullcode[len(code):],gold[len(positive):],reverse)
                    for c,fullcode,gold in by_family[fam]))

    def test_fitted_features_have_independent_support_and_bounded_endpoints(self):
        rows=[json.loads(s) for s in gzip.decompress((DATA/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
        support=defaultdict(set)
        for stage,fam,context,code,positive,negative,margin,origin in rows:
            a,b=features(context,positive),features(context,negative)
            for k in a.keys()|b.keys():
                if a[k]!=b[k]:support[k].add(fam)
        weights=json.loads((DATA/'model/weights.json').read_text())
        self.assertTrue(any(len(k)>3 for k in weights))
        for key,value in weights.items():
            self.assertGreaterEqual(len(support[key]),3)
            self.assertTrue(2<=len(key)<=5)
            self.assertTrue(math.isfinite(value) and abs(value)<=.25)


if __name__=='__main__':unittest.main()
