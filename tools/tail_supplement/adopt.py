"""Copy only the qualified, independently validated implementation into the app."""
import json
from pathlib import Path
import shutil
import subprocess
from study import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write
from independent import qualified


def main():
    qualified()
    decision=json.loads((DATA/'decision.json').read_text())
    if decision['qualification_sha256']!=sha(DATA/'qualification.json'):
        raise ValueError('Independent decision does not match qualification')
    old_files=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'app'],cwd=ROOT,text=True).splitlines()
    for name in old_files:
        expected=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
        if (ROOT/name).read_bytes()!=expected:raise ValueError('Preserve existing app modification: '+name)
    if not decision['qualified']:
        write(REPORTS/'adoption.json',dict(adopted=False,tracked_app_files_unchanged=len(old_files),
            decision_sha256=sha(DATA/'decision.json'),apk_produced=False,version='0.6.39',version_code=46))
        print('Rejected candidate; original app preserved');return
    package='app/src/main/java/hk/cantonesemixeng/keyboard/'
    names=[package+name+'.java' for name in ('QuickDecoder','CantoneseMixEngKeyboardService','TailSupplement','DirectCodeGenerator')]
    names+=['app/src/main/assets/code_generator.b64']
    for name in names:shutil.copyfile(WORK/'android'/name,ROOT/name)
    notice=ROOT/'app/src/main/assets/licenses/code-generator/README.md';notice.parent.mkdir(parents=True,exist_ok=True)
    with notice.open('x') as out:
        out.write('''# Direct code-conditioned generation weights

Modified model weights are offered under CC BY-SA 4.0. The full licence is
bundled at ../sentence-language/CC-BY-SA-4.0.txt. The code remains under the
repository GPL-3.0-or-later licence. Dictionary code facts retain the source
contribution terms in the bundled GPL/LGPL/MIT dictionary notices.

The 32-dimensional character GRU and16-dimensional code encoder derive from
the frozen teacher checkpoint in tools/data/code_generator/models/teacher.npz.
The teacher was initialized from the attributed sentence-language model,
then trained on legal code-conditioned TRAIN examples. No new text or fitting
is introduced by this binary export. It proposes strings only; existing
native scorers decide admission to at most two final candidate slots.

Credits: Kang Kwong Luke and May L. Y. Wong, HKCanCor (2015), CC BY4.0,
https://github.com/fcbond/hkcancor revision39aeadf920e0b5ca93d0ad7792c59e740e7bdd65;
Tatoeba contributors via Aaron H. K. Tan/Jyut Dictionary,2023-04-08 snapshot,
CC BY2.0 France; Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
UD Cantonese-HK (Depling2017), CC BY-SA4.0; Mozilla Common Voice Sentence
Collector contributors, donated read prompts under CC0; project-authored
synthetic examples. Authors do not endorse these modifications.

Full source URLs, terms, revisions and family exclusions remain in
tools/data/code_generator/NOTICE.md, tools/data/sentence_pretrain/NOTICE.md
and the bundled ../sentence-language/source-audit.json. No Common Voice
prompt cache, words.hk evaluation text or private phone learning record is
included in these assets. Editor/search history is local to each query.

Teacher SHA256:704eb0e81108f5a038621ba42bea8b9e925b64d30848235858b90f73709c3feb
Export SHA256:c1e552eafdb126acc28618e4fcb4e4e9debd4c7497ffb2a67c6a01c7a76c6914
The source, sealed evaluation and limitations are in
docs/CONSERVATIVE_TAIL_SUPPLEMENT.md and tools/data/tail_supplement/.
''')
    for name in names:
        if sha(ROOT/name)!=sha(WORK/'android'/name):raise ValueError('Adopted bytes differ from the tested Android candidate')
    changed=set(names)
    unchanged=0
    for name in old_files:
        if name in changed:continue
        expected=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT)
        if (ROOT/name).read_bytes()!=expected:raise ValueError('Unexpected app change: '+name)
        unchanged+=1
    write(REPORTS/'adoption.json',dict(adopted=True,exact_tested_android_bytes={name:sha(ROOT/name) for name in names},
        bundled_notice_sha256=sha(notice),all_other_original_app_files_unchanged=unchanged,
        decision_sha256=sha(DATA/'decision.json'),qualification_sha256=sha(DATA/'qualification.json'),
        version='0.6.39',version_code=46,apk_produced=False,
        limits='Tail coverage only; first18 preserved. Cloud timing is not Fold7 timing. No large/1.0 claim.'))
    print('Adopted exact independently validated bytes; no APK/version/signing/storage/layout change')


if __name__=='__main__':main()
