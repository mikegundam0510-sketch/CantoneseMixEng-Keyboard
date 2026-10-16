#!/usr/bin/env python3
"""Independent-family checks and selection-gate integrity, not accuracy fixtures."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from prepare_clean_ranking import rules,spans
from prepare_phrase_relations import gram_index,overlap
from prepare_tatoeba_corpus import digest
from run_context_search import DATA,assess
from sentence_features import han
from train_phrase_model import ROOT,reverse_codes
from train_candidate_ranker import matches


class ContextSearchData(unittest.TestCase):
    def test_families_and_training_exclusions(self):
        m=json.loads((DATA/'manifest.json').read_text());old=set();groups=set();mapping=rules()
        for name,value in m['known_input_sha256'].items():
            p=ROOT/name;self.assertEqual(digest(p),value)
            if name.endswith('.tsv'):
                for line in p.read_text().splitlines():
                    if line.startswith('#'):continue
                    old.update(t for t in line.split('\t') if len(t)>=6 and all(han(c) for c in t))
            elif name.endswith('.jsonl'):
                for line in p.read_text().splitlines():
                    r=json.loads(line)
                    if 'group' in r and 'lemmas' in r:groups.add(str(r['group']))
        for line in gzip.decompress((ROOT/'tools/data/clean_language_models/corpus.jsonl.gz').read_bytes()).decode().splitlines():
            old.add(json.loads(line)['text'])
        old.update(t for text in list(old) for _,_,t,_ in spans(text,mapping) if len(t)>=6)
        index=gram_index(old);used=set();reverse=reverse_codes();vtexts=set()
        for split,count in (('validation',150),('heldout',500)):
            path=DATA/(split+'.tsv');source=DATA/(split+'-source.jsonl')
            self.assertEqual(digest(path),m['file_sha256'][path.name])
            rows=[s.split('\t') for s in path.read_text().splitlines()]
            infos=[json.loads(s) for s in source.read_text().splitlines()]
            self.assertEqual(len(rows),count)
            for row,info in zip(rows,infos):
                self.assertNotIn(info['group'],groups|used);used.add(info['group'])
                self.assertEqual(row[3],info['text']);self.assertTrue(matches(row[2],row[3],reverse))
                self.assertFalse(overlap(row[3],index))
                for _,_,t,_ in spans(row[3],mapping):self.assertFalse(overlap(t,index))
                if split=='validation':vtexts.add(row[3])
                else:self.assertFalse(overlap(row[3],gram_index(vtexts)))

    def fixture(self,before_gold=(),after_gold=(),partial=False,inexact=False):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name)
        cases=DATA/'calibration1450.tsv';rows=[s.split('\t') for s in cases.read_text().splitlines()]
        # Synthetic complete lists test evaluator integrity only; never prediction evidence.
        def output(indices):
            return ['\t'.join(row+(['1',row[3]] if i in indices else ['0',''])) for i,row in enumerate(rows)]
        before=root/'before.tsv';before.write_text('\n'.join(output(before_gold))+'\n')
        values=output(after_gold)
        if partial:values=values[:-1]
        if inexact:values[0]='\t'.join(rows[0]+['0','abc'])
        after=root/'after.tsv';after.write_text('\n'.join(values)+'\n')
        return assess(cases,before,after,root/'report.json')

    def test_unchanged_lists_do_not_qualify(self):self.assertFalse(self.fixture()['qualified'])
    def test_old_only_gain_does_not_qualify(self):self.assertFalse(self.fixture(after_gold=(150,))['qualified'])
    def test_new_gain_with_old_preserved_qualifies(self):self.assertTrue(self.fixture(after_gold=(0,))['qualified'])
    def test_new_loss_is_not_hidden_by_old_gain(self):self.assertFalse(self.fixture(before_gold=(0,),after_gold=(150,151))['qualified'])
    def test_partial_and_inexact_outputs_are_rejected(self):
        with self.assertRaises(ValueError):self.fixture(partial=True)
        with self.assertRaises(ValueError):self.fixture(inexact=True)


if __name__=='__main__':unittest.main()
