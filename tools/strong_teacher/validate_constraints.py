"""Repair only upstream validator output decoding; keep sealed policy/tests intact."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_constraints import Constraints
from constraints import grammar
from prepare import ROOT,WORK,DATA,REPORTS,write,sha


class NativeGrammarChecks(Constraints):
    def valid(self,code,text):
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            folder=Path(temporary);g=folder/'code.gbnf';t=folder/'text.txt'
            g.write_text(grammar(code,self.codes));t.write_text(text)
            # The upstream validator inserts ANSI colours between UTF8 bytes
            # while describing rejected non-ASCII text. Check its ASCII result
            # marker in raw bytes; do not misreport that display bug as acceptance.
            result=subprocess.run([str(self.validator),str(g),str(t)],check=True,capture_output=True)
            return b'Input string is valid according to the grammar.' in result.stdout


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativeGrammarChecks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    write(REPORTS/'constraint-checks.json',dict(passed=True,tests=result.testsRun,
        actual_llama_grammar_parser=True,actual_native_dictionary=True,model_loaded=False,
        teacher_accuracy_evaluation_run=False))
    write(DATA/'validation-repair.json',dict(scope='No model inference, data/grammar/policy change. Only read upstream coloured rejection output as bytes.',
        preserved_original_test_sha256=sha(ROOT/'tools/strong_teacher/test_constraints.py'),
        preserved_failure_log_sha256=sha(WORK/'constraint-tests.log'),
        validation_driver_sha256=sha(Path(__file__))))
