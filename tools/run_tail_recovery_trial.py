#!/usr/bin/env python3
"""Reproduce the frozen rejected model in an archive; never patch the app checkout."""
import argparse
from pathlib import Path
import shutil
import subprocess
from native_phrase_relations import build,run
from train_phrase_model import ROOT
from train_tail_recovery import DATA

def prepare(work):
    work=work.resolve()
    if work==ROOT or ROOT.is_relative_to(work):
        raise ValueError('Choose an archive directory outside the app checkout root')
    if work.exists() and any(work.iterdir()):
        raise ValueError('Choose a new or empty archive directory; existing files are preserved')
    build(work,'99708f9',original=True)
    (work/'app/src/test/java/hk/cantonesemixeng/keyboard').mkdir(parents=True,exist_ok=True)
    subprocess.run(['patch','--batch','-p1','-d',str(work),'-i',str(DATA/'selected-runtime.patch')],check=True)
    shutil.copyfile(DATA/'model015/tail_ranker.b64',work/'app/src/main/assets/tail_ranker.b64')
    java=work/'RelationEvaluation.java';source=java.read_text()
    old='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if source.count(old)!=1:raise ValueError('Frozen optional model constructor changed')
    source=source.replace(old,old[:-2]+',\n   TailRecoveryRanker.load(Files.newInputStream(assets.resolve("tail_ranker.b64"))));')
    java.write_text(source)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),
                    '-d',str(work/'classes'),str(java)],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','output','work'):p.add_argument(name,type=Path)
    a=p.parse_args();prepare(a.work);run(a.work,a.cases,a.output)
