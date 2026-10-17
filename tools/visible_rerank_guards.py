#!/usr/bin/env python3
"""Guard candidate preservation, learning, timing and Android wiring."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

from prepare_sentence_pretrain import write
from report_prefix_retrieval import compare
from run_visible_rerank import BASELINE, check, preserve
from train_phrase_model import ROOT


def harnesses(work):
    check()
    java=(ROOT/'tools/ContextLearningEvaluation.java').read_text()
    anchor='? PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))) : null);'
    if java.count(anchor)!=1:raise ValueError('Learning constructor changed')
    java=java.replace(anchor,anchor[:-2]+',\n            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));')
    java=java.replace('List<String> old=decoder.decode(fields[1],learned,fields[0]);',
        'List<String> old=decoder.decode(fields[1],learned,fields[0]);\n                '
        'if(!new HashSet<>(old).equals(new HashSet<>(decoder.decodeBaseline(fields[1],learned,fields[0],null)))) '
        'throw new AssertionError("Legacy learned visible set changed");')
    java=java.replace('List<String> updated=decoder.decode(fields[1],learned,fields[0],preferences);',
        'List<String> updated=decoder.decode(fields[1],learned,fields[0],preferences);\n                '
        'if(!new HashSet<>(updated).equals(new HashSet<>(decoder.decodeBaseline(fields[1],learned,fields[0],preferences)))) '
        'throw new AssertionError("Context learned visible set changed");')
    target=work/'ContextLearningEvaluation.java';target.write_text(java)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-cp',str(work/'classes'),'-d',str(work/'classes'),str(target)],check=True)
    java=(ROOT/'tools/PairedRankingPerformance.java').read_text()
    anchor='            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());'
    if java.count(anchor)!=1:raise ValueError('Performance constructor changed')
    java=java.replace(anchor,'''            if(Files.exists(assets.resolve("sentence_language.b64"))) {
                Class<?> slm=classes.loadClass(pkg+"SentenceLanguageRanker");
                types.add(slm);
                values.add(slm.getMethod("load",InputStream.class)
                    .invoke(null,Files.newInputStream(assets.resolve("sentence_language.b64"))));
            }
'''+anchor)
    target=work/'PairedRankingPerformance.java';target.write_text(java)
    subprocess.run(['javac','-encoding','UTF-8','-d',str(work/'classes'),str(target)],check=True)


def android(work, native):
    check()
    if work.exists():raise ValueError('Preserve existing Android archive')
    work.mkdir(parents=True)
    blob=subprocess.check_output(['git','archive',BASELINE],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:archive.extractall(work,filter='data')
    for relative in ('app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java',
                     'app/src/main/java/hk/cantonesemixeng/keyboard/SentenceLanguageRanker.java',
                     'app/src/main/java/hk/cantonesemixeng/keyboard/VisibleCandidateReranker.java',
                     'app/src/main/java/hk/cantonesemixeng/keyboard/CandidateEngine.java',
                     'app/src/main/java/hk/cantonesemixeng/keyboard/EnglishChineseEngine.java',
                     'app/src/main/assets/sentence_language.b64'):
        shutil.copyfile(native/relative,work/relative)
    p=work/'app/src/main/java/hk/cantonesemixeng/keyboard/CantoneseMixEngKeyboardService.java'
    java=p.read_text();anchor='                QuickDecoder phrases = new QuickDecoder('
    if java.count(anchor)!=1:raise ValueError('Android loader anchor changed')
    java=java.replace(anchor,'''                SentenceLanguageRanker sentenceLanguageRanker;
                try {
                    sentenceLanguageRanker = SentenceLanguageRanker.load(getAssets().open("sentence_language.b64"));
                } catch (IOException optionalModelUnavailable) {
                    sentenceLanguageRanker = null;
                }
'''+anchor)
    anchor='candidateRanker, wordRanker, sentenceRanker, prefixRanker, relationRanker);'
    if java.count(anchor)!=1:raise ValueError('Android constructor changed')
    p.write_text(java.replace(anchor,anchor[:-2]+', sentenceLanguageRanker);'))
    shutil.copyfile(ROOT/'app/src/main/assets/stroke.tsv',work/'app/src/main/assets/stroke.tsv')
    shutil.copytree(ROOT/'app/src/main/assets/licenses/stroke',work/'app/src/main/assets/licenses/stroke')


def merge(shards, output):
    check()
    cases=ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv'
    baseline=ROOT/'tools/reports/clean-language-models-2026-10-16/guard3893.tsv'
    inputs=cases.read_text().splitlines();rows=[None]*len(inputs)
    if len(inputs)!=3893:raise ValueError('Expected fixed3893 cases')
    for part in range(4):
        if (shards/f'cases-{part}.tsv').read_text().splitlines()!=inputs[part::4]:raise ValueError('Guard inputs changed')
        values=(shards/f'output-{part}.tsv').read_text().splitlines()
        if len(values)!=len(inputs[part::4]):raise ValueError('Partial guard output')
        for at,line in enumerate(values):rows[part+4*at]=line
    output.mkdir(parents=True,exist_ok=True)
    merged=output/'guard3893.tsv';merged.write_text(''.join(r+'\n' for r in rows))
    report=compare(cases,baseline,merged);report['baseline_revision']=BASELINE
    report['reference']='Pinned e209474 output; app tree equals523d133.'
    report['coverage']=preserve(cases,baseline,merged)
    report['guard_gate']=dict(
        aggregate_counts_nondecreasing=all(report['after'][k]>=report['before'][k] for k in ('top1','top5','top20')),
        per_set_first_top5_loss_within_one_pp=all(all(g['before'][k]-g['after'][k]<=g['before']['cases']*.01+1e-9
            for k in ('top1','top5')) for g in report['per_set'].values()))
    report['qualified']=all(report['guard_gate'].values());write(output/'guard3893.json',report)
    print(json.dumps({k:report[k] for k in ('before','after','guard_gate','qualified')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('harnesses');a.add_argument('work',type=Path)
    a=s.add_parser('android');a.add_argument('work',type=Path);a.add_argument('native',type=Path)
    a=s.add_parser('merge');a.add_argument('shards',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='harnesses':harnesses(a.work)
    elif a.mode=='android':android(a.work,a.native)
    else:merge(a.shards,a.output)
