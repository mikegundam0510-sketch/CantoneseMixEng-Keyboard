#!/usr/bin/env python3
"""Run fixed search-only ablations against parent-main assets and frozen cases."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from context_search_policy import source,ARMS
from native_phrase_relations import build,run
from prepare_tatoeba_corpus import digest
from report_prefix_retrieval import compare
from report_search_recovery import metrics
from train_phrase_model import ROOT

DATA=ROOT/'tools/data/context_search'
REPORTS=ROOT/'tools/reports/context-search-2026-10-16'
BASELINE='e209474'


def check():
    protocol=json.loads((DATA/'protocol.json').read_text())
    for name,value in protocol['source_sha256'].items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen policy source changed: '+name)
    for name,value in protocol['input_sha256'].items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen cases changed: '+name)
    return protocol


def prepare(work):
    check()
    if work.exists():raise ValueError('Use a fresh native archive')
    build(work/'baseline',BASELINE,original=True)
    relative='app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    text=(work/'baseline'/relative).read_text()
    for arm in ARMS:
        target=work/arm;shutil.copytree(work/'baseline',target)
        (target/relative).write_text(source(text,arm))
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(target/'app/src/main/java'),
            '-d',str(target/'classes'),str(target/'RelationEvaluation.java')],check=True)


def evaluate(work,arm,cases,output):
    check();run(work/arm,cases,output)


def assess(cases,before,after,output):
    r=compare(cases,before,after);r['baseline_revision']=BASELINE
    b=[s.split('\t') for s in before.read_text().splitlines()];a=[s.split('\t') for s in after.read_text().splitlines()]
    new=lambda rows:[x for x in rows if x[0]=='context-search:validation']
    old=lambda rows:[x for x in rows if x[0]!='context-search:validation']
    bn,an,bo,ao=metrics(new(b)),metrics(new(a)),metrics(old(b)),metrics(old(a))
    if bn['cases']!=150 or bo['cases']!=1300:raise ValueError('Expected frozen150+800+old500')
    r['gate']=dict(new_counts_nondecreasing=all(an[k]>=bn[k] for k in ('top1','top5','top20')),
        new_first_or_top5_gain=any(an[k]>bn[k] for k in ('top1','top5')),
        old_counts_nondecreasing=all(ao[k]>=bo[k] for k in ('top1','top5','top20')),
        old_per_set_loss_within_one_pp=all(all(g['before'][k]-g['after'][k]<=g['before']['cases']*.01+1e-9 for k in ('top1','top5'))
            for name,g in r['per_set'].items() if name!='context-search:validation'))
    r['qualified']=all(r['gate'].values());r['new150']=dict(before=bn,after=an);r['old1300']=dict(before=bo,after=ao)
    groups=list(r['per_set'].values());r['selection_key']=[sum(g['after'][k]/g['after']['cases'] for g in groups)/len(groups) for k in ('top1','top5','top20')]
    r['selection_key'].append(sum(g['after']['mrr'] for g in groups)/len(groups))
    output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    return r


def report(results):
    check();scores={}
    for arm in ARMS:scores[arm]=assess(DATA/'calibration1450.tsv',results/'baseline1450.tsv',results/(arm+'.tsv'),results/(arm+'.json'))
    eligible=[a for a in ARMS if scores[a]['qualified']]
    order=list(ARMS)
    selected=max(eligible,key=lambda a:(scores[a]['selection_key'],-order.index(a))) if eligible else None
    value=dict(protocol_sha256=digest(DATA/'protocol.json'),selected=selected,fresh500_decoded=False,
        trials={a:{k:scores[a][k] for k in ('before','after','new150','old1300','gate','qualified','selection_key')} for a in ARMS},
        decision='Proceed to3893/learning/Android/speed guards' if selected else 'Reject all four; retain parent-main production and leave fresh500 untested')
    (DATA/'selection.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path)
    a=s.add_parser('run');a.add_argument('work',type=Path);a.add_argument('arm',choices=('baseline',*ARMS));a.add_argument('cases',type=Path);a.add_argument('output',type=Path)
    a=s.add_parser('report');a.add_argument('results',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work)
    elif a.mode=='run':evaluate(a.work,a.arm,a.cases,a.output)
    else:report(a.results)
