import json
import math
from pathlib import Path
import tempfile
import unittest
from prepare_joint_ranking import DATA
from prepare_phrase_relations import gram_index,overlap,hkcancor
from prepare_tatoeba_corpus import digest
from train_joint_ranking import read_pairs
from train_phrase_model import ROOT

class JointRankingTest(unittest.TestCase):
    def test_frozen_data_and_added_rows_have_licensed_training_origins(self):
        manifest=json.loads((DATA/'manifest.json').read_text())
        for name,sha in manifest['file_sha256'].items():self.assertEqual(digest(DATA/name),sha,name)
        old=(ROOT/'tools/data/phrase_relations/train.tsv').read_text()
        self.assertTrue((DATA/'train.tsv').read_text().startswith(old))
        rows=[s.split('\t') for s in (DATA/'additional-training.tsv').read_text().splitlines()]
        self.assertEqual(len(rows),4600);self.assertEqual(len({r[3] for r in rows}),4600)
        allowed=json.loads((ROOT/'app/src/main/assets/PHRASE_MODEL_REPORT.json').read_text())['training_conversation_files']
        hk=ROOT/'.native/search-alignment-20261014/hkcancor-utf8.zip'
        if not hk.exists():self.skipTest('Pinned raw HKCanCor unavailable for provenance replay')
        text_by_file={}
        for name,_,words in hkcancor(hk):
            if name in allowed:text_by_file.setdefault(name,set()).add(''.join(w for w,_ in words))
        tatoeba={(str(r['group']),r['text']) for s in (ROOT/'tools/data/tatoeba_corpus/train.jsonl').read_text().splitlines() if (r:=json.loads(s))}
        for source,context,code,gold in rows:
            self.assertEqual(context,'')
            if source.startswith('train:hk:'):
                name=source[len('train:hk:'):].rsplit(':',1)[0];self.assertIn(name,allowed);self.assertIn(gold,text_by_file[name])
            else:
                self.assertTrue(source.startswith('train:tatoeba:'))
                self.assertIn((source[len('train:tatoeba:'):],gold),tatoeba)

    def test_reserve_families_are_new_and_split_before_decoding(self):
        groups=[]
        for split in ('validation','heldout'):
            groups.append({json.loads(s)['group'] for s in (DATA/(split+'-source.jsonl')).read_text().splitlines()})
        self.assertEqual(list(map(len,groups)),[100,500]);self.assertFalse(groups[0]&groups[1])
        old=set()
        manifest=json.loads((DATA/'manifest.json').read_text())
        for name in manifest['known_input_sha256']:
            if name.endswith('source.jsonl'):
                old.update(json.loads(s)['group'] for s in (ROOT/name).read_text().splitlines())
        self.assertFalse((groups[0]|groups[1])&old)
        targets={s.split('\t')[3] for split in ('validation','heldout') for s in (DATA/(split+'.tsv')).read_text().splitlines()}
        index=gram_index(targets)
        for line in (DATA/'additional-training.tsv').read_text().splitlines():self.assertFalse(overlap(line.split('\t')[3],index))

    def test_evaluation_and_partial_observer_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'evaluation.tsv';p.write_text('joint:heldout\t\tofvd\t你好\n')
            with self.assertRaises(ValueError):read_pairs(p,p)

    def test_shared_weights_have_exact_unclipped_endpoint_bounds(self):
        for name in ('model003','model015'):
            folder=DATA/name
            if not folder.exists():self.skipTest('Shared fits not generated yet')
            report=json.loads((folder/'training-report.json').read_text());weights=json.loads((folder/'weights.json').read_text())
            self.assertEqual(digest(folder/'weights.json'),report['weights_sha256'])
            self.assertEqual(digest(DATA/'train.tsv'),report['training_sha256'])
            self.assertEqual(digest(DATA/'protocol.json'),report['protocol_sha256'])
            self.assertLessEqual(len(weights),16000)
            for key,value in weights.items():
                self.assertIn(len(key),(2,3));self.assertTrue(math.isfinite(value));self.assertLessEqual(abs(value),.5)
            # Each character closes at most two keys, below the endpoint cap.
            self.assertLessEqual(2*max(map(abs,weights.values())),1.5)

if __name__=='__main__':unittest.main()
