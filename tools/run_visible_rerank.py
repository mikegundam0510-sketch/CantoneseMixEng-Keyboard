#!/usr/bin/env python3
"""Evaluate fixed pretrained models after preserving the parent's visible display."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from native_phrase_relations import build, DRIVER
from prepare_tatoeba_corpus import digest
from prepare_sentence_pretrain import write
from run_context_search import assess
from train_phrase_model import ROOT
from visible_rerank_policy import quick_source, candidate_source, translation_source

DATA=ROOT/'tools/data/visible_rerank'
BASELINE='523d133'
MODELS=ROOT/'tools/data/sentence_pretrain/models'


def check():
    seal=json.loads((DATA/'seal.json').read_text())
    if digest(DATA/'protocol.json')!=seal['protocol_sha256']:raise ValueError('Visible protocol changed')
    p=json.loads((DATA/'protocol.json').read_text())
    for name,value in {**p['source_sha256'],**p['evaluation_sha256']}.items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen visible input/source changed: '+name)
    tree=subprocess.check_output(['git','rev-parse',BASELINE+':app'],cwd=ROOT,text=True).strip()
    if tree!=p['parent_app_tree']:raise ValueError('Parent app tree changed')
    return p


def preserve(cases,before,after):
    inputs=[s.split('\t') for s in cases.read_text().splitlines() if s and not s.startswith('#')]
    old=[s.split('\t') for s in before.read_text().splitlines()]
    new=[s.split('\t') for s in after.read_text().splitlines()]
    if not len(inputs)==len(old)==len(new):raise ValueError('Partial coverage output')
    changed=0
    for case,b,a in zip(inputs,old,new):
        if len(b)!=6 or len(a)!=6 or b[:4]!=case or a[:4]!=case:raise ValueError('Coverage order changed')
        bv=b[5].split('|') if b[5] else [];av=a[5].split('|') if a[5] else []
        if len(av)>20 or len(av)!=len(bv) or len(set(av))!=len(av) or set(av)!=set(bv):
            raise ValueError('Original visible candidates lost or added: '+str(case[:3]))
        changed+=av!=bv
    return dict(cases=len(inputs),all_visible_sets_identical=True,ranked_lists_changed=changed)


def prepare(work):
    check()
    if work.exists():raise ValueError('Use a fresh visible native archive')
    build(work/'baseline',BASELINE,original=True)
    anchor='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if DRIVER.count(anchor)!=1:raise ValueError('Native constructor changed')
    driver=DRIVER.replace(anchor,anchor[:-2]+',\n   SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));')
    anchor='  int count=0;try(BufferedWriter out='
    if driver.count(anchor)!=1:raise ValueError('Native loop changed')
    driver=driver.replace(anchor,'''  List<String> reference=Files.readAllLines(Path.of(args[3]));
  int count=0;try(BufferedWriter out=''')
    anchor='    for(String text:values)if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact candidate");'
    if driver.count(anchor)!=1:raise ValueError('Native code check changed')
    driver=driver.replace(anchor,anchor+r'''
    String[] old=reference.get(count).split("\\t",-1);
    if(!Arrays.equals(Arrays.copyOf(old,4),f))throw new AssertionError("Baseline row mismatch");
    List<String> original=old[5].isEmpty()?Collections.emptyList():Arrays.asList(old[5].split("\\|"));
    if(original.size()!=values.size()||!new HashSet<>(original).equals(new HashSet<>(values)))
      throw new AssertionError("Visible set changed");''')
    parent=Path('app/src/main/java/hk/cantonesemixeng/keyboard')
    patches={'QuickDecoder':quick_source,'CandidateEngine':candidate_source,'EnglishChineseEngine':translation_source}
    for arm in ('language','adapted'):
        stage=work/arm;shutil.copytree(work/'baseline',stage)
        for name,patch in patches.items():
            p=stage/parent/(name+'.java');p.write_text(patch(p.read_text()))
        for name in ('SentenceLanguageRanker','VisibleCandidateReranker'):
            shutil.copyfile(ROOT/'tools'/(name+'.java'),stage/parent/(name+'.java'))
        shutil.copyfile(MODELS/(arm+'.b64'),stage/'app/src/main/assets/sentence_language.b64')
        java=stage/'RelationEvaluation.java';java.write_text(driver)
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-d',str(stage/'classes'),str(java)],check=True)
        null=stage/'VisibleNullEvaluation.java';null.write_text(DRIVER.replace('class RelationEvaluation','class VisibleNullEvaluation'))
        subprocess.run(['javac','-encoding','UTF-8','-cp',str(stage/'classes'),'-d',str(stage/'classes'),str(null)],check=True)


def run(work,arm,cases,before,output):
    check();stage=work/arm;output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    pending=output.with_suffix('.pending.tsv')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.RelationEvaluation',
        str(stage/'app/src/main/assets'),str(cases.resolve()),str(pending),str(before.resolve())],check=True)
    preserve(cases,before,pending)
    pending.replace(output)


def report(folder):
    check();scores={};cases=ROOT/'tools/data/context_search/calibration1450.tsv'
    before=ROOT/'tools/reports/context-search-2026-10-16/baseline1450.tsv'
    for arm in ('language','adapted'):
        coverage=preserve(cases,before,folder/(arm+'.tsv'))
        r=assess(cases,before,folder/(arm+'.tsv'),folder/(arm+'.json'))
        r['baseline_revision']=BASELINE;r['coverage']=coverage
        write(folder/(arm+'.json'),r);scores[arm]=r
    eligible=[a for a in scores if scores[a]['qualified']]
    selected=max(eligible,key=lambda a:(scores[a]['selection_key'],a=='language')) if eligible else None
    result=dict(parent_revision=BASELINE,protocol_sha256=digest(DATA/'protocol.json'),selected=selected,
        trials={a:{k:r[k] for k in ('before','after','new150','old1300','gate','coverage','qualified','selection_key')} for a,r in scores.items()},
        independent500_decoded=False,decision='Proceed to3893/learning/Android/timing guards' if selected else 'Reject both fixed rerankers; preserve production and unused500')
    write(DATA/'selection.json',result);print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path)
    a=s.add_parser('run');a.add_argument('work',type=Path);a.add_argument('arm',choices=('baseline','language','adapted'));a.add_argument('cases',type=Path);a.add_argument('before',type=Path);a.add_argument('output',type=Path)
    a=s.add_parser('report');a.add_argument('folder',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work)
    elif a.mode=='run':run(a.work,a.arm,a.cases,a.before,a.output)
    else:report(a.folder)
