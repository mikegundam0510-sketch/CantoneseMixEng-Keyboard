import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from observe_structured_training import check_cases,gap_cases
from prepare_joint_ranking import DATA,input_target,prepare
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes
from train_structured_ranking import RESEARCH,read_reconstructed

class StructuredTrainingTest(unittest.TestCase):
    def test_new_training_admission_rejects_dictionary_coded_punctuation(self):
        reverse=reverse_codes();old=[s.split('\t') for s in (DATA/'additional-training.tsv').read_text().splitlines()]
        tatoeba=[f[3] for f in old if f[0].startswith('train:tatoeba:')]
        self.assertEqual(len(tatoeba),600)
        self.assertTrue(all(input_target(text,reverse,True) for text in tatoeba))
        self.assertFalse(any(input_target(text,reverse) for text in tatoeba))
        self.assertTrue(input_target('你交咗功課畀老細未',reverse))
        self.assertFalse(input_target('你交咗功課畀老細未。',reverse))
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);sentinel=out/'preserve.txt';sentinel.write_text('existing data')
            with self.assertRaises(ValueError):prepare(Path('missing'),Path('missing'),Path('missing'),out)
            self.assertEqual(sentinel.read_text(),'existing data')

    def test_evaluation_duplicates_and_malformed_cases_rejected(self):
        row=(DATA/'train.tsv').read_text().splitlines()[0]
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'cases.tsv'
            for text in ('joint:heldout\t\tofvd\t你好\n',row+'\n'+row+'\n','broken\n',''):
                p.write_text(text)
                with self.assertRaises(ValueError):check_cases(p)
            p.write_text(row+'\n');self.assertEqual(len(check_cases(p)),1)

    def test_gap_has_no_score_learnable_complete_targets(self):
        folder=RESEARCH/'gap';report=json.loads((folder/'observation.json').read_text())
        for name,sha in report['output_sha256'].items():self.assertEqual(digest(folder/name),sha)
        self.assertEqual(report['ordinary_inference_parity'],1044)
        self.assertEqual(report['counts'],{'all':1044,'outside_static_option_caps':791,'no_legal_han_path':253})
        self.assertEqual(report['pairs'],0)

    def test_all_reconstructed_pairs_are_legal_and_training_only(self):
        pairs,protocol=read_reconstructed();self.assertTrue(pairs)
        reverse=reverse_codes()
        for stage,fam,context,code,positive,negative,offset in pairs:
            self.assertIn(stage,('prefix','final'));self.assertTrue(fam.startswith('train:'))
            self.assertTrue(matches(code,positive,reverse));self.assertTrue(matches(code,negative,reverse))
            self.assertTrue(math.isfinite(offset));self.assertNotEqual(positive,negative)
        self.assertEqual(len(protocol['trial_grid']),4)

    def test_static_cap_targets_never_supply_shadow_training_pairs(self):
        audits={tuple(f[:4]):f for s in (RESEARCH/'audit.tsv').read_text().splitlines() if (f:=s.split('\t'))}
        counts={tuple(f[:4]) for s in (RESEARCH/'reconstructed-pairs.tsv').read_text().splitlines() if (f:=s.split('\t'))}
        self.assertEqual(len(audits),1821)
        for ident in counts:self.assertEqual(audits[ident][5],'true')
        self.assertFalse(counts&{key for key,f in audits.items() if f[5]!='true'})

    def test_tampered_trace_cannot_admit_an_ineligible_or_nontraining_positive(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for name in ('protocol.json','observation.json','cases.tsv','audit.tsv','visible.tsv','reconstructed-pairs.tsv'):
                shutil.copyfile(RESEARCH/name,folder/name)
            original=(folder/'reconstructed-pairs.tsv').read_text()
            for alteration in ('source','inexact'):
                lines=original.splitlines();f=lines[0].split('\t')
                if alteration=='source':f[0]='joint:heldout'
                else:f[6]='錯誤測試答案'
                lines[0]='\t'.join(f);(folder/'reconstructed-pairs.tsv').write_text('\n'.join(lines)+'\n')
                manifest=json.loads((folder/'observation.json').read_text())
                manifest['output_sha256']['reconstructed-pairs.tsv']=digest(folder/'reconstructed-pairs.tsv')
                (folder/'observation.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):read_reconstructed(folder)

    def test_fitted_models_have_frozen_provenance_and_unclipped_endpoint_bounds(self):
        for name in ('model003','model015'):
            folder=RESEARCH/name;report=json.loads((folder/'training-report.json').read_text())
            weights=json.loads((folder/'weights.json').read_text())
            for field,path in (('protocol_sha256',RESEARCH/'protocol.json'),
                               ('reconstruction_sha256',RESEARCH/'reconstructed-pairs.tsv'),
                               ('weights_sha256',folder/'weights.json'),('pairs_sha256',folder/'pairs.tsv')):
                self.assertEqual(report[field],digest(path))
            self.assertEqual(report['pairs'],38556);self.assertLessEqual(len(weights),16000)
            for key,value in weights.items():
                self.assertIn(len(key),(2,3));self.assertTrue(math.isfinite(value));self.assertLessEqual(abs(value),.5)
            self.assertLessEqual(2*max(map(abs,weights.values())),1.5)

if __name__=='__main__':unittest.main()
