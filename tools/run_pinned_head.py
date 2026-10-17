#!/usr/bin/env python3
"""Preserve every original first choice and rerank its existing tail only."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from pinned_head_policy import quick_source
from native_phrase_relations import build,DRIVER
from prepare_sentence_pretrain import write
from prepare_tatoeba_corpus import digest
from run_context_search import assess
from run_visible_rerank import preserve as old_preserve,run as visible_run
from train_phrase_model import ROOT
from visible_rerank_policy import candidate_source,translation_source

BASELINE='61e62e5'
DATA=ROOT/'tools/data/pinned_head'
REPORTS=ROOT/'tools/reports/pinned-head-2026-10-17'


def check():
    p=json.loads((DATA/'protocol.json').read_text())
    if digest(DATA/'protocol.json')!=json.loads((DATA/'seal.json').read_text())['protocol_sha256']:
        raise ValueError('Pinned-head protocol changed')
    for name,value in {**p['source_sha256'],**p['input_sha256']}.items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen pinned-head source/input changed: '+name)
    if subprocess.check_output(['git','rev-parse',BASELINE+':app'],cwd=ROOT,text=True).strip()!=p['parent_app_tree']:
        raise ValueError('Parent app changed')
    return p


def preserve(cases,before,after):
    result=old_preserve(cases,before,after)
    old=[s.split('\t') for s in before.read_text().splitlines()]
    new=[s.split('\t') for s in after.read_text().splitlines()]
    if any(b[5].split('|')[0]!=a[5].split('|')[0] for b,a in zip(old,new)):
        raise ValueError('Original first choice changed')
    result['all_original_first_choices_identical']=True
    return result


def prepare(work):
    check()
    if work.exists():raise ValueError('Use a fresh pinned-head native archive')
    build(work/'baseline',BASELINE,original=True)
    stage=work/'candidate';shutil.copytree(work/'baseline',stage)
    java=stage/'app/src/main/java/hk/cantonesemixeng/keyboard'
    for name,patch in [('QuickDecoder',quick_source),('CandidateEngine',candidate_source),('EnglishChineseEngine',translation_source)]:
        p=java/(name+'.java');p.write_text(patch(p.read_text()))
    for name in ('SentenceLanguageRanker','VisibleCandidateReranker','PinnedHeadReranker'):
        shutil.copyfile(ROOT/'tools'/(name+'.java'),java/(name+'.java'))
    assets=stage/'app/src/main/assets'
    shutil.copyfile(ROOT/'tools/data/sentence_pretrain/models/adapted.b64',assets/'sentence_language.b64')
    anchor='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if DRIVER.count(anchor)!=1:raise ValueError('Driver constructor changed')
    driver=DRIVER.replace(anchor,anchor[:-2]+',\n   SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));')
    anchor='  int count=0;try(BufferedWriter out='
    driver=driver.replace(anchor,'  List<String> reference=Files.readAllLines(Path.of(args[3]));\n'+anchor)
    anchor='    for(String text:values)if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact candidate");'
    driver=driver.replace(anchor,anchor+r'''
    String[] old=reference.get(count).split("\\t",-1);
    if(!Arrays.equals(Arrays.copyOf(old,4),f))throw new AssertionError("Reference input mismatch");
    List<String> parent=old[5].isEmpty()?Collections.emptyList():Arrays.asList(old[5].split("\\|"));
    if(values.size()!=parent.size()||!new HashSet<>(parent).equals(new HashSet<>(values)))throw new AssertionError("Visible set changed");
    if(!values.isEmpty()&&!values.get(0).equals(parent.get(0)))throw new AssertionError("Original first changed");''')
    p=stage/'RelationEvaluation.java';p.write_text(driver)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-d',str(stage/'classes'),str(p)],check=True)
    p=stage/'PinnedNullEvaluation.java';p.write_text(DRIVER.replace('class RelationEvaluation','class PinnedNullEvaluation'))
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(stage/'classes'),'-d',str(stage/'classes'),str(p)],check=True)


def run(work,cases,before,output):
    check();freeze_check(work);visible_run(work,'candidate',cases,before,output)
    preserve(cases,before,output)


def freeze_check(work=None):
    frozen=json.loads((DATA/'inference-freeze.json').read_text())
    for name,value in frozen['source_model_sha256'].items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen evaluation source/model changed: '+name)
    work=Path(frozen['native_root']) if work is None else work
    for arm,files in frozen['native_sha256'].items():
        for name,value in files.items():
            if digest(work/arm/name)!=value:raise ValueError('Frozen native inference changed: '+arm+'/'+name)


def report():
    check();freeze_check();cases=ROOT/'tools/data/context_search/calibration1450.tsv'
    before=ROOT/'tools/reports/context-search-2026-10-16/baseline1450.tsv';after=REPORTS/'calibration1450.tsv'
    coverage=preserve(cases,before,after)
    r=assess(cases,before,after,REPORTS/'calibration1450.json');r['baseline_revision']=BASELINE;r['coverage']=coverage
    write(REPORTS/'calibration1450.json',r)
    write(DATA/'selection.json',dict(selected='candidate' if r['qualified'] else None,
        calibration=r,independent500_decoded=False,decision='Proceed to fixed guards' if r['qualified'] else 'Reject; no policy/threshold change or reserve decode'))
    print(json.dumps({k:r[k] for k in ('before','after','new150','gate','coverage','qualified')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path)
    a=s.add_parser('run');a.add_argument('work',type=Path);a.add_argument('cases',type=Path);a.add_argument('before',type=Path);a.add_argument('output',type=Path)
    s.add_parser('report');a=p.parse_args()
    if a.mode=='prepare':prepare(a.work)
    elif a.mode=='run':run(a.work,a.cases,a.before,a.output)
    else:report()
