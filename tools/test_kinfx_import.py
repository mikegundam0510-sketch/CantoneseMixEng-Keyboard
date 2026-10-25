import json
from pathlib import Path
import tempfile
import unittest
from import_kinfx_words import collect, FILES, sha, ROOT


class KinfxImportTest(unittest.TestCase):
    def test_filter_supported_new_words_and_discard_upstream_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)
            for relative in FILES:
                path=source/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('---\nname: fixture\n...\n你好\twrongcode\t5000\n返工\txxxx\t2999\n香港\tzzzz\t6000\n無字\tzzzz\t6000\n你\txx\t99999\n')
            words,rows=collect(source,{'香港'},set('你好返工香港無'))
            self.assertEqual({'你好':5000},words)
            self.assertEqual(10,rows)

    def test_committed_selection_matches_manifest_and_has_no_code_column(self):
        manifest=json.loads((ROOT/'app/src/main/assets/licenses/kinfx/SOURCE.json').read_text())
        output=ROOT/'app/src/main/assets/kinfx_words.tsv'
        self.assertEqual(manifest['output_sha256'],sha(output))
        rows=[line.split('\t') for line in output.read_text().splitlines() if not line.startswith('#')]
        self.assertEqual(504,len(rows))
        self.assertEqual(len(rows),len({row[0] for row in rows}))
        self.assertTrue(all(len(row)==2 and int(row[1])>=3000 for row in rows))


if __name__=='__main__':unittest.main()
