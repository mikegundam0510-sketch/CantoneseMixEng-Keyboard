"""Adopt only the exact qualified candidate, otherwise verify production retention."""
import json
from pathlib import Path
import shutil
import subprocess
from study import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write
from independent import verify


def main():
    verify();decision=json.loads((DATA/'decision.json').read_text())
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'app'],cwd=ROOT,text=True).splitlines()
    for name in tracked:
        wanted=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
        if (ROOT/name).read_bytes()!=wanted:raise ValueError('Preserve preexisting app changes: '+name)
    adopted=decision['adopt']
    if adopted:
        names=['app/src/main/java/hk/cantonesemixeng/keyboard/'+n+'.java' for n in
            ('QuickDecoder','DirectCodeGenerator','NewCharacterSupplement','CantoneseMixEngKeyboardService')]
        names+=['app/src/main/assets/expanded_generator.b64']
        for name in names:
            source=WORK/'candidate'/name
            if sha(source)!=sha(WORK/'android'/name):raise ValueError('Tested Android differs')
            shutil.copyfile(source,ROOT/name)
        # Same source credits/terms as the teacher, with the new modification
        # identified explicitly. This notice does not affect inference.
        notice=ROOT/'app/src/main/assets/licenses/expanded-generator/README.md'
        notice.parent.mkdir()
        with notice.open('x') as out:
            out.write('# Expanded code-generator supplement\n\n'
                'Modified weights are CC BY-SA4.0, with full terms in '
                '../sentence-language/CC-BY-SA-4.0.txt. Preserve all original '
                'source credits, pinned revisions, dictionary contribution terms '
                'and bundled source-audit in ../code-generator/README.md and '
                '../sentence-language/. Contributors do not endorse this model.\n\n'
                'This export adds245 TRAIN-supported character rows to the '
                'original2248-character teacher, freezing all old/shared parameters. '
                'There is no additional fitting in the pool-retention experiment. '
                'The original generator stays active. Expanded offers must contain '
                'a new character and can compete for at most two final positions '
                'after retaining the deployed first18. No words.hk evaluation text, '
                'Common Voice prompt cache or private phone learning data is bundled.\n\n'
                'Checkpoint: tools/data/vocabulary_expansion/models/expanded.npz\n\n'
                'Checkpoint SHA256: '+sha(ROOT/'tools/data/vocabulary_expansion/models/expanded.npz')+'\n\n'
                'Export SHA256: '+sha(DATA/'expanded_generator.b64')+'\n\n'
                'Full modification/source notices: tools/data/retained_pool/NOTICE.md '
                'and tools/data/vocabulary_expansion/NOTICE.md. Evaluation and limits: '
                'docs/RETAINED_POOL_SUPPLEMENT.md.\n')
    else:
        names=[]
    # Every unrelated app file, including signing/version/storage/layout, is
    # checked after any adoption as well. Initial ignored user files are untouched.
    unchanged=0
    for name in tracked:
        if name not in names:
            wanted=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
            if (ROOT/name).read_bytes()!=wanted:raise ValueError('Unrelated app change: '+name)
            unchanged+=1
    write(REPORTS/'delivery-verification.json',dict(adopted=adopted,
        parent_revision=BASELINE,unchanged_preexisting_tracked_app_files=unchanged,
        copied_exact_qualified_inference_files=names,independent500_consumed=True,
        version='0.6.39',version_code=46,apk_produced=False,
        limitation='Cloud JVM/Android checks; no Fold7 device verification or1.0 claim'))
    print('adopted',adopted,'unchanged tracked app files',unchanged,'no APK')


if __name__=='__main__':main()
