import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from clean_ranking_observations import cases,check_subset
from prepare_clean_ranking import DATA,BASE,rules,spans,hk_records,inventory,align
from prepare_daily_prefix_data import hashed
from prepare_phrase_relations import gram_index,overlap
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import ROOT
from train_clean_ranking import reconstructed

class CleanRankingTest(unittest.TestCase):
    def test_non_han_boundaries_are_not_deleted_or_joined(self):
        original='「我今晚要返工」，meeting room 你聽日要返工123佢後日去旅行。'
        values=list(spans(original,rules()))
        self.assertEqual([r[2] for r in values],['我今晚要返工','你聽日要返工','佢後日去旅行'])
        for start,end,text,changes in values:self.assertEqual(original[start:end],text);self.assertFalse(changes)
        self.assertEqual(list(spans('abc123，。',rules())),[])

    def test_only_verified_glyphs_and_canonical_unicode_change(self):
        values=list(spans('神僞爲檯𡃉𠻺𠸏𡁵',rules()))
        self.assertEqual(values[0][2],'神偽為枱𡃉𠻺𠸏𡁵')
        self.assertEqual([v['offset'] for v in values[0][3]],[0,1,2,3])
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);shutil.copytree(DATA/'orthography',p/'orthography')
            spec=json.loads((p/'orthography/rules.json').read_text());spec['pairs']['𡃉']='㗎'
            (p/'orthography/rules.json').write_text(json.dumps(spec))
            with self.assertRaises(ValueError):rules(p)

    def test_corpus_english_with_spaces_and_missing_speech_split_spans(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'corpus.zip'
            text='<sent>\n我今晚要返工/v/aa1/\nMr Bean/xnz/aa0/\n你聽日要返工/v/aa1/\n○/#/#/@\n佢後日去旅行/v/aa1/\n</sent_tag>\n'
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('utf8/example',text)
            records=list(hk_records(path,{'utf8/example'}));self.assertEqual(len(records),1)
            self.assertEqual([s for _,_,s,_ in spans(records[0][2],{})],['我今晚要返工','你聽日要返工','佢後日去旅行'])
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('utf8/example','<sent>\n未知漢字/#/#/@\n')
            with self.assertRaises(ValueError):list(hk_records(path,{'utf8/example'}))

    def test_all_frozen_targets_have_actual_cold_top24_alignment(self):
        code_for,ranks=inventory(DATA/'character-codes.tsv');eligible={}
        for (c,part),rank in ranks.items():
            if rank<=24:eligible.setdefault(c,set()).add(part)
        rows=cases();self.assertEqual(len(rows),7891)
        self.assertEqual(len({r[3] for r in rows}),len(rows))
        for source,context,code,gold in rows:
            self.assertTrue(matches(code,gold,eligible));self.assertLessEqual(len(code),48)
            self.assertTrue(all(ranks[c,part]<=24 for c,part in align(code,gold,eligible)))

    def test_provenance_replays_to_original_train_sources(self):
        mapping=rules();manifest=json.loads((DATA/'manifest.json').read_text())
        raw_path=ROOT/'.native/search-alignment-20261014/hkcancor-utf8.zip'
        if not raw_path.exists():self.skipTest('Pinned raw TRAIN archive unavailable for provenance replay')
        raw={(name,index):original for name,index,original in hk_records(raw_path,set(manifest['training_conversations']))}
        tatoeba={(str(row['id']),str(row['group'])):row['text'] for s in (ROOT/'tools/data/tatoeba_corpus/train.jsonl').read_text().splitlines() if (row:=json.loads(s))}
        retained=BASE.read_text().splitlines();provenance=[json.loads(s) for s in (DATA/'provenance.jsonl').read_text().splitlines()]
        self.assertEqual([tuple(r[k] for k in ('source','context','code','gold')) for r in provenance],cases())
        for r in provenance:
            origin=r['origin'];kind=origin['kind']
            if kind=='HKCanCor':self.assertEqual(raw[origin['file'],origin['utterance']],r['original'])
            elif kind=='Tatoeba':self.assertEqual(tatoeba[origin['id'],origin['group']],r['original'])
            else:
                f=retained[origin['row']].split('\t');self.assertEqual((f[0],f[1],f[3]),(r['source'],r['context'],r['original']))
            self.assertIn((r['start'],r['end'],r['gold'],r['changes']),list(spans(r['original'],mapping)))
            self.assertLessEqual(r['maximum_character_rank'],24)

    def test_reserved500_stays_disjoint_after_training_normalization(self):
        mapping=rules();targets={f[3] for s in (ROOT/'tools/data/joint_ranking/heldout.tsv').read_text().splitlines() if (f:=s.split('\t'))}
        targets.update(s for text in list(targets) for _,_,s,_ in spans(text,mapping))
        forbidden=gram_index(targets)
        for row in cases():self.assertFalse(overlap(row[3],forbidden))

    def test_observer_rejects_evaluation_and_duplicate_inputs(self):
        row='\t'.join(cases()[0])
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'cases.tsv'
            for value in ('joint:heldout\t\tofvd\t你好\n',row+'\n'+row+'\n',''):
                p.write_text(value)
                with self.assertRaises(ValueError):check_subset(p)

    def test_supervised_shadow_paths_leave_actual_inference_unchanged(self):
        folder=DATA/'repair';meta=json.loads((folder/'observation.json').read_text())
        self.assertEqual(meta['missing_targets'],122);self.assertEqual(meta['ordinary_inference_exact_parity'],122)
        pairs=reconstructed(folder);self.assertEqual(len(pairs),771)
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            for name in ('observation.json','audit.tsv','visible.tsv','pairs.tsv'):shutil.copyfile(folder/name,out/name)
            lines=(out/'pairs.tsv').read_text().splitlines();row=lines[0].split('\t');row[0]='joint:heldout';lines[0]='\t'.join(row)
            (out/'pairs.tsv').write_text('\n'.join(lines)+'\n');meta['output_sha256']['pairs.tsv']=digest(out/'pairs.tsv')
            (out/'observation.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):reconstructed(out)

    def test_models_pin_clean_data_and_keep_linear_endpoint_bounds(self):
        for name in ('model003','model015'):
            folder=DATA/name;report=json.loads((folder/'training-report.json').read_text())
            for field,path in (('training_sha256',DATA/'train.tsv'),('protocol_sha256',DATA/'protocol.json'),
                               ('shadow_sha256',DATA/'repair/pairs.tsv'),('weights_sha256',folder/'weights.json')):
                self.assertEqual(report[field],digest(path))
            self.assertEqual(report['pairs'],35376)
            weights=json.loads((folder/'weights.json').read_text());self.assertTrue(weights)
            for key,value in weights.items():
                self.assertIn(len(key),(2,3));self.assertTrue(math.isfinite(value));self.assertLessEqual(abs(value),.5)
            self.assertLessEqual(2*max(map(abs,weights.values())),1.5)

if __name__=='__main__':unittest.main()
