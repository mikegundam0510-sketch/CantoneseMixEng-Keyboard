#!/usr/bin/env python3
"""Current-parent shared endpoint score: frozen two-strength ordinary trials."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from native_phrase_relations import build, run, DRIVER
from observe_current_search import BASELINE, DATA
from prepare_tatoeba_corpus import digest
from run_context_search import assess
from run_joint_ranking import source
from train_current_search import check
from train_phrase_model import ROOT


def prepare(work, model, mode='joint'):
    check()
    if work.exists(): raise ValueError('Use a fresh native archive')
    build(work, BASELINE, original=True)
    quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    quick.write_text(source(quick.read_text(),mode))
    shutil.copyfile(model,work/'app/src/main/assets/joint_ranker.b64')
    anchor='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if DRIVER.count(anchor)!=1: raise ValueError('Native constructor changed')
    driver=DRIVER.replace(anchor,anchor[:-2]+',\n   CandidateRanker.loadWords(Files.newInputStream(assets.resolve("joint_ranker.b64"))));')
    java=work/'RelationEvaluation.java';java.write_text(driver)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
    null=work/'CurrentSearchNull.java';null.write_text(DRIVER.replace('class RelationEvaluation','class CurrentSearchNull'))
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-d',str(work/'classes'),str(null)],check=True)


def report(folder):
    check();scores={}
    cases=ROOT/'tools/data/context_search/calibration1450.tsv'
    before=ROOT/'tools/reports/context-search-2026-10-16/baseline1450.tsv'
    for arm in ('half','full','short-control'):
        scores[arm]=assess(cases,before,folder/(arm+'.tsv'),folder/(arm+'.json'))
    eligible=[a for a in ('half','full') if scores[a]['qualified']]
    selected=max(eligible,key=lambda a:(scores[a]['selection_key'],a=='half')) if eligible else None
    value=dict(parent_revision=BASELINE,freeze_sha256=digest(DATA/'freeze.json'),selected=selected,
        trials={a:{k:scores[a][k] for k in ('new150','old1300','before','after','gate','qualified','selection_key')} for a in scores},
        short_control_eligible=False,fresh500_decoded=False,
        decision='Proceed to larger, learning, timing and independent gates' if selected else 'Reject both strengths; preserve production and unused500 reserve')
    (DATA/'selection.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path);a.add_argument('model',type=Path);a.add_argument('--policy',choices=('joint','final'),default='joint')
    a=s.add_parser('run');a.add_argument('work',type=Path);a.add_argument('cases',type=Path);a.add_argument('output',type=Path)
    a=s.add_parser('report');a.add_argument('folder',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work,a.model,a.policy)
    elif a.mode=='run':check();run(a.work,a.cases,a.output)
    else:report(a.folder)
