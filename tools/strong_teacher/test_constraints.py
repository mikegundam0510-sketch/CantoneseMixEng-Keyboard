"""Compare actual llama.cpp grammar acceptance with native Quick facts, no model."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from constraints import read_facts,accept,grammar
from prepare import ROOT,WORK,DATA,REPORTS,ENV,write


class Constraints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codes=read_facts(WORK/'native-facts.tsv')
        cls.validator=ENV/'build/bin/test-gbnf-validator'
        cls.rows=[line.split('\t') for line in (DATA/'cases.tsv').read_text().splitlines()]

    def valid(self,code,text):
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            folder=Path(temporary);g=folder/'code.gbnf';t=folder/'text.txt'
            g.write_text(grammar(code,self.codes));t.write_text(text)
            result=subprocess.run([str(self.validator),str(g),str(t)],check=True,capture_output=True,text=True)
            return 'Input string is valid according to the grammar.' in result.stdout

    def test_actual_complete_codes(self):
        for f in self.rows[::8]:
            code,text=f[3],f[4]
            self.assertTrue(accept(code,text,self.codes));self.assertTrue(self.valid(code,text))

    def test_incomplete_and_extra_text_rejected(self):
        for f in self.rows[::16]:
            code,text=f[3],f[4]
            for wrong in (text+'人','',text+'。',text+'a'):
                self.assertEqual(self.valid(code,wrong),accept(code,wrong,self.codes))
                if wrong in ('',text+'。',text+'a'):self.assertFalse(accept(code,wrong,self.codes))

    def test_non_bmp(self):
        code,char=next((code,c) for code,chars in sorted(self.codes.items()) for c in sorted(chars) if ord(c)>0xffff)
        self.assertTrue(self.valid(code,char));self.assertTrue(accept(code,char,self.codes))

    def test_invalid_code_limits(self):
        for code in ('','ABC','a'*49,'a1'):
            with self.assertRaises(ValueError):grammar(code,self.codes)

    def test_one_and_two_key_ambiguity(self):
        codes={'a':{'一'},'aa':{'二'}}
        self.assertTrue(accept('aa','一一',codes));self.assertTrue(accept('aa','二',codes))
        self.assertFalse(accept('aa','一',codes));self.assertFalse(accept('a','二',codes))

    def test_gold_absent_from_inference_fields(self):
        manifest=(WORK/'rerank-manifest.txt').read_text().splitlines()
        self.assertEqual(len(manifest),92)
        for f,path in zip(self.rows,manifest):
            lines=Path(path).read_text().splitlines()
            self.assertEqual(lines,[f[2]]+f[6].split('|'))
        for path in (WORK/'grammars').glob('*.gbnf'):
            text=path.read_text();self.assertNotIn('target',text);self.assertNotIn('rank',text)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Constraints)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    write(REPORTS/'constraint-checks.json',dict(passed=True,tests=result.testsRun,
        actual_llama_grammar_parser=True,actual_native_dictionary=True,model_loaded=False,
        teacher_accuracy_evaluation_run=False))
