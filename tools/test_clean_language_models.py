#!/usr/bin/env python3
"""Primary training checks: source replay, leakage, boundaries and probability mass."""
from collections import Counter
import gzip
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from prepare_clean_ranking import rules, spans
from prepare_phrase_relations import overlap
from prepare_tatoeba_corpus import digest, load_training
from train_clean_language_models import (DATA, ROOT, PHRASE, evaluation_exclusions, hk_utterances,
    token_spans, character_model, word_relations, phrase_model, add_counts)
from train_language_model import key


class CleanPrimaryTraining(unittest.TestCase):
    def test_token_boundaries_and_offsets(self):
        tokens=['香港','Mr Bean','檯面','○/#/#/@','衆人','。','神','𡃉']
        parts=list(token_spans(tokens,rules()))
        self.assertEqual([r[3] for r in parts],['香港','枱面','眾人','神𡃉'])
        self.assertEqual([r[4] for r in parts],[['香港'],['枱面'],['眾人'],['神','𡃉']])
        for original,start,end,text,words,changes in parts:
            self.assertEqual(list(spans(original[start:end],rules()))[0][2],text)
        self.assertEqual(parts[1][5][0]['offset'],9)

    def test_raw_parser_does_not_delete_spaced_english(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'source.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('utf8/train','<sent>\n香港/n/hoeng1/\nMr Bean/x//\n人/n/jan4/\n○/#/#/@\n檯/n/toi4/\n</sent_tag>')
                z.writestr('utf8/heldout','秘密/n//\n<sent>')
            rows=list(hk_utterances(p,{'utf8/train'}))
            self.assertEqual(len(rows),1)
            self.assertEqual([r[3] for r in token_spans(rows[0][2],rules())],['香港','人','枱'])

    def test_unparsed_han_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'source.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('utf8/train','香港/n/a/b/c/\n<sent>')
            with self.assertRaises(ValueError):list(hk_utterances(p,{'utf8/train'}))

    def test_pruning_escape_mass_and_probability(self):
        counts=[Counter() for _ in range(6)]
        add_counts(counts,'香港人',12);add_counts(counts,'香港好',1)
        payload,report=character_model(counts)
        _,_,count,unknown=struct.unpack_from('>IIIf',payload)
        rows={h:(p,b) for h,p,b in (struct.unpack_from('>qff',payload,16+16*i) for i in range(count))}
        self.assertNotIn(key('港好'),rows)
        self.assertAlmostEqual(rows[key('港')][1],1-12/(13+128*4),places=7)
        self.assertAlmostEqual(rows[key('香港人')][0],12/(13+128*8),places=7)
        # Pruned continuations escape to a normalized lower distribution.
        for context in ('','香','港','香港'):
            escape=unknown
            for n in range(2,min(5,len(context)+1)+1):
                ctx=rows.get(key(context[-(n-1):]))
                if ctx:escape*=ctx[1]
            mass=escape
            for c in counts[1]:
                p=rows[key(c)][0]
                for n in range(2,min(5,len(context)+1)+1):
                    gram=(context+c)[-n:];ctx=rows.get(key(gram[:-1]))
                    if ctx:p=rows.get(key(gram),(0,1))[0]+ctx[1]*p
                mass+=p
            self.assertAlmostEqual(mass,1,places=6)
        self.assertEqual(report['entries'],count)

    def test_model_bytes_do_not_depend_on_counter_order(self):
        a=[Counter() for _ in range(6)];b=[Counter() for _ in range(6)]
        for t in ('香港人','香港好','你好'):add_counts(a,t,12)
        for t in ('你好','香港好','香港人'):add_counts(b,t,12)
        self.assertEqual(character_model(a)[0],character_model(b)[0])
        self.assertEqual(phrase_model({'香港人':1,'你好':.5})[0],phrase_model({'你好':.5,'香港人':1})[0])

    def test_word_evidence_requires_supported_segmented_relation(self):
        uni=Counter({'返工':10,'未':8,'我':20})
        pairs=Counter({('返工','未'):3,('我','未'):5,('我','返工'):1})
        relations=word_relations(uni,pairs,Counter())
        self.assertIn('返工未',relations)
        self.assertNotIn('我未',relations)
        self.assertNotIn('我返工',relations)
        self.assertTrue(all(0<v<=3 for v in relations.values()))

    def test_only_reviewed_glyph_changes(self):
        mapping=rules()
        self.assertFalse(set('𡃉𠻺𠸏𡁵')&mapping.keys())
        self.assertEqual(list(spans('𡃉𠻺𠸏𡁵',mapping))[0][2],'𡃉𠻺𠸏𡁵')

    def test_frozen_corpus_provenance_and_disjointness(self):
        manifest=json.loads((DATA/'manifest.json').read_text())
        self.assertEqual(digest(DATA/'corpus.jsonl.gz'),manifest['corpus_sha256'])
        records=[json.loads(s) for s in gzip.decompress((DATA/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
        mapping=rules();excluded,hashes=evaluation_exclusions(mapping)
        tt,_=load_training(ROOT/'tools/data/tatoeba_corpus');tt={str(r['id']):r for r in tt}
        self.assertEqual(dict(Counter(r['domain'] for r in records)),manifest['records_by_domain'])
        self.assertEqual(len(set(manifest['training_conversations'])),46)
        self.assertFalse(set(manifest['training_conversations'])&set(PHRASE['excluded_conversation_files']))
        self.assertTrue(all('train' not in Path(n).name and 'pairs' not in Path(n).name for n in hashes))
        for r in records:
            self.assertFalse(overlap(r['text'],excluded))
            self.assertIn((r['start'],r['end'],r['text'],r['changes']),list(spans(r['original'],mapping)))
            if r['domain']=='Tatoeba':
                row=tt[r['origin']['id']]
                self.assertEqual(r['original'],row['text']);self.assertEqual(r['family'],str(row['group']))
                self.assertIsNone(r['words'])
            else:
                self.assertEqual(''.join(r['words']),r['text'])
                if r['domain']=='HK':self.assertIn(r['origin']['file'],manifest['training_conversations'])
        self.assertEqual(sum(len(r['changes']) for r in records),manifest['modifications'])

    def test_original_hk_word_and_span_replay(self):
        source=ROOT/'.native/search-alignment-20261014/hkcancor-utf8.zip'
        self.assertTrue(source.exists(),'Provide pinned HK source for full provenance verification')
        originals={(name,index):tokens for name,index,tokens in hk_utterances(source,set(PHRASE['training_conversation_files']))}
        mapping=rules()
        for line in gzip.decompress((DATA/'corpus.jsonl.gz').read_bytes()).decode().splitlines():
            r=json.loads(line)
            if r['domain']!='HK':continue
            tokens=originals[r['origin']['file'],r['origin']['utterance']]
            self.assertIn((r['original'],r['start'],r['end'],r['text'],r['words'],r['changes']),list(token_spans(tokens,mapping)))


if __name__=='__main__':unittest.main()
