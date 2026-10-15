import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from prepare_prefix_retrieval import DATA,BASELINE,prepare
from prepare_phrase_relations import gram_index,overlap
from prepare_search_recovery import prepare as old_prepare,DATA as OLD_DATA
from prepare_tatoeba_corpus import digest
from prefix_survival_oracle import instrument
from report_prefix_retrieval import compare,survival_diagnosis
from sentence_features import han
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes

class PrefixRetrievalTest(unittest.TestCase):
    def test_frozen_cases_are_exact_and_exclude_prior_targets_and_families(self):
        manifest=json.loads((DATA/'manifest.json').read_text());reverse=reverse_codes()
        prior=set();groups=set()
        for name in manifest['known_input_sha256']:
            path=ROOT/name
            if name.endswith('.tsv'):
                prior.update(v for line in path.read_text().splitlines() if not line.startswith('#')
                             for v in line.split('\t') if len(v)>=6 and all(han(c) for c in v))
            elif name.endswith('-source.jsonl'):
                groups.update(json.loads(s)['group'] for s in path.read_text().splitlines())
        index=gram_index(prior);seen=set();all_groups=set()
        for split,count in [('validation',100),('heldout',500)]:
            rows=[s.split('\t') for s in (DATA/(split+'.tsv')).read_text().splitlines()]
            source=[json.loads(s) for s in (DATA/(split+'-source.jsonl')).read_text().splitlines()]
            self.assertEqual(len(rows),count);self.assertEqual(len(source),count)
            for row,origin in zip(rows,source):
                self.assertEqual(row[3],origin['text']);self.assertTrue(matches(row[2],row[3],reverse))
                self.assertNotIn(origin['group'],groups|all_groups);all_groups.add(origin['group'])
                self.assertFalse(overlap(row[3],index));self.assertFalse(overlap(row[3],gram_index(seen)))
            seen.update(r[3] for r in rows)
        for name,sha in manifest['file_sha256'].items():self.assertEqual(digest(DATA/name),sha)

    def test_new_and_historical_preparations_reproduce_without_changing_old_split(self):
        cache=ROOT/'.native/search-alignment-20261014'
        args=[cache/'wordshk.csv',cache/'hkcancor-utf8.zip',
              ROOT/'.native/search-recovery-20261015/yue_hk-ud-test.conllu']
        if not all(p.exists() for p in args):self.skipTest('Pinned public source cache unavailable')
        for generator,frozen in [(prepare,DATA),(old_prepare,OLD_DATA)]:
            with self.subTest(data=str(frozen)),tempfile.TemporaryDirectory() as directory:
                out=Path(directory);generator(*args,out)
                for name in ('manifest.json','validation.tsv','heldout.tsv','validation-source.jsonl','heldout-source.jsonl'):
                    self.assertEqual((out/name).read_bytes(),(frozen/name).read_bytes(),name)

    def test_comparison_validates_complete_exact_outputs_and_paired_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);case=d/'cases.tsv';before=d/'before.tsv';after=d/'after.tsv'
            row='fixture\t\tofvd\t你好'
            case.write_text(row+'\n');before.write_text(row+'\t0\t\n');after.write_text(row+'\t1\t你好\n')
            report=compare(case,before,after)
            self.assertEqual(report['paired']['first']['net'],1)
            self.assertTrue(report['no_per_set_count_loss'])
            for bad in ['',row+'\t2\t你好\n',row+'\t1\t你好|你好\n',row+'\t0\t哈哈\n',
                        row.replace('fixture','wrong')+'\t1\t你好\n']:
                after.write_text(bad)
                with self.subTest(output=bad),self.assertRaises(ValueError):compare(case,before,after)

    def test_oracle_only_instruments_an_archived_decoder_and_fails_if_hooks_change(self):
        relative='app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
        source=subprocess.check_output(['git','show',BASELINE+':'+relative],cwd=ROOT,text=True)
        observed=instrument(source)
        self.assertIn('oracleEnabled',observed)
        self.assertNotIn('oracleGold',(ROOT/relative).read_text())
        self.assertIn('dictionary.matchQuickCodes(oracleCode.substring(oraclePosition)',observed)
        self.assertIn('private List<Path> ordinaryPrune(',observed)
        with self.assertRaisesRegex(ValueError,'hook changed'):instrument(source.replace('BEAM = 48','BEAM = 49'))

    def test_survival_diagnosis_distinguishes_final_losses_and_rejects_inconsistent_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);cases=d/'cases.tsv';output=d/'output.tsv';diag=d/'diag.tsv'
            fixtures=[('displayed',1,'true\ttrue\ttrue'),('not_generated',0,'false\tfalse\tfalse'),
                      ('completed_pool_cut',0,'true\tfalse\tfalse'),('confidence_filtered',0,'true\ttrue\tfalse'),
                      ('outside_twenty',0,'true\ttrue\ttrue')]
            cases.write_text(''.join(f'{name}\t\tofvd\t你好\n' for name,_,_ in fixtures))
            output.write_text(''.join(f'{name}\t\tofvd\t你好\t{rank}\t'+('你好' if rank else '')+'\n' for name,rank,_ in fixtures))
            diag.write_text(''.join(f'{name}\t\tofvd\t你好\t1\t{flags}\n' for name,_,flags in fixtures))
            report=survival_diagnosis(cases,output,diag)
            self.assertEqual(report['outcomes'],{name:1 for name,_,_ in fixtures})
            self.assertEqual(report['added_prefixes'],5)
            with self.assertRaisesRegex(ValueError,'Inconsistent'):survival_diagnosis(cases,output,diag,False)
            diag.write_text(diag.read_text().replace('true\ttrue\ttrue','false\ttrue\ttrue',1))
            with self.assertRaisesRegex(ValueError,'Inconsistent'):survival_diagnosis(cases,output,diag)

if __name__=='__main__':unittest.main()
