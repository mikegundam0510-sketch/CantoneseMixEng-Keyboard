#!/usr/bin/env python3
"""Reuse fixed guards, explicitly connecting the fitted first-choice gate."""
import argparse
from pathlib import Path
import shutil
import subprocess

import visible_rerank_guards as old
from head_change_training import check
from run_head_change import model,BASELINE
from train_phrase_model import ROOT


def harnesses(work):
    model();old.harnesses(work)
    p=work/'ContextLearningEvaluation.java';text=p.read_text()
    anchor='SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));'
    if text.count(anchor)!=1:raise ValueError('Learning model hook changed')
    p.write_text(text.replace(anchor,anchor[:-2]+',\n            HeadChangeGate.load(Files.newInputStream(assets.resolve("head_change.b64"))));'))
    p=work/'PairedRankingPerformance.java';text=p.read_text()
    anchor='            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());'
    if text.count(anchor)!=1:raise ValueError('Timing model hook changed')
    p.write_text(text.replace(anchor,'''            if(Files.exists(assets.resolve("head_change.b64"))) {
                Class<?> gate=classes.loadClass(pkg+"HeadChangeGate");types.add(gate);
                values.add(gate.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("head_change.b64"))));
            }
'''+anchor))
    for name in ('ContextLearningEvaluation','PairedRankingPerformance'):
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-cp',str(work/'classes'),'-d',str(work/'classes'),str(work/(name+'.java'))],check=True)


def android(work,native):
    model();old.android(work,native)
    for relative in ('app/src/main/java/hk/cantonesemixeng/keyboard/HeadChangeGate.java','app/src/main/assets/head_change.b64'):
        shutil.copyfile(native/relative,work/relative)
    p=work/'app/src/main/java/hk/cantonesemixeng/keyboard/CantoneseMixEngKeyboardService.java';text=p.read_text()
    anchor='                QuickDecoder phrases = new QuickDecoder('
    text=text.replace(anchor,'''                HeadChangeGate headChangeGate;
                try { headChangeGate=HeadChangeGate.load(getAssets().open("head_change.b64")); }
                catch(IOException optionalGateUnavailable) { headChangeGate=null; }
'''+anchor)
    anchor='relationRanker, sentenceLanguageRanker);'
    if text.count(anchor)!=1:raise ValueError('Service gate hook changed')
    p.write_text(text.replace(anchor,'relationRanker, sentenceLanguageRanker, headChangeGate);'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('harnesses');a.add_argument('work',type=Path)
    a=s.add_parser('android');a.add_argument('work',type=Path);a.add_argument('native',type=Path)
    a=s.add_parser('merge');a.add_argument('shards',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='harnesses':harnesses(a.work)
    elif a.mode=='android':android(a.work,a.native)
    else:check();old.BASELINE=BASELINE;old.merge(a.shards,a.output)
