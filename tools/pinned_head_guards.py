#!/usr/bin/env python3
"""Reuse fixed enabled-model guards, adding strict per-case first preservation."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import visible_rerank_guards as old
from prepare_sentence_pretrain import write
from run_pinned_head import BASELINE,ROOT,check,preserve


def harnesses(work):
    check();old.harnesses(work)
    p=work/'ContextLearningEvaluation.java';text=p.read_text()
    for name,call in [('old','decoder.decodeBaseline(fields[1],learned,fields[0],null)'),
                      ('updated','decoder.decodeBaseline(fields[1],learned,fields[0],preferences)')]:
        anchor='                List<String> '+name+'=decoder.decode(fields[1],learned,fields[0]'+(');' if name=='old' else ',preferences);')
        if text.count(anchor)!=1:raise ValueError('Learning head check anchor changed')
        text=text.replace(anchor,anchor+'\n                if(!'+name+'.isEmpty()&&!'+name+'.get(0).equals('+call+'.get(0))) throw new AssertionError("Learned first changed");')
    p.write_text(text)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-cp',str(work/'classes'),'-d',str(work/'classes'),str(p)],check=True)


def android(work,native):
    check();old.BASELINE=BASELINE;old.android(work,native)
    relative='app/src/main/java/hk/cantonesemixeng/keyboard/PinnedHeadReranker.java'
    shutil.copyfile(native/relative,work/relative)


def merge(shards,output):
    check();old.BASELINE=BASELINE;old.merge(shards,output)
    r=json.loads((output/'guard3893.json').read_text())
    r['coverage']=preserve(ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv',ROOT/'tools/reports/clean-language-models-2026-10-16/guard3893.tsv',output/'guard3893.tsv')
    r['guard_gate']['all_original_first_choices_identical']=True
    r['reference']='Pinned e209474 output; same parent app tree as61e62e5.'
    r['qualified']=all(r['guard_gate'].values());write(output/'guard3893.json',r)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('harnesses');a.add_argument('work',type=Path)
    a=s.add_parser('android');a.add_argument('work',type=Path);a.add_argument('native',type=Path)
    a=s.add_parser('merge');a.add_argument('shards',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='harnesses':harnesses(a.work)
    elif a.mode=='android':android(a.work,a.native)
    else:merge(a.shards,a.output)
