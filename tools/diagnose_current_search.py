#!/usr/bin/env python3
"""Observe the fixed half-arm's old264 losses without changing normal inference."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess

import diagnose_context_search as observer
from observe_current_search import BASELINE, DATA
from prepare_tatoeba_corpus import digest
from run_joint_ranking import source
from train_current_search import check
from train_phrase_model import ROOT


def prepare(work):
    check()
    if work.exists():raise ValueError('Preserve previous diagnostic archive')
    observer.BASELINE=BASELINE
    observer.prepare(work)
    quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    quick.write_text(source(quick.read_text()))
    shutil.copyfile(DATA/'model/search-0.5.b64',work/'app/src/main/assets/joint_ranker.b64')
    java=work/'RelationEvaluation.java';text=java.read_text()
    anchor='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if text.count(anchor)!=1:raise ValueError('Diagnostic constructor changed')
    java.write_text(text.replace(anchor,anchor[:-2]+',\n   CandidateRanker.loadWords(Files.newInputStream(assets.resolve("joint_ranker.b64"))));'))
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
    rows=(ROOT/'tools/reports/context-search-2026-10-16/diagnosis/visible.tsv').read_text().splitlines()
    (work/'cases.tsv').write_text(''.join('\t'.join(s.split('\t')[:4])+'\n' for s in rows))


def report(observed,ordinary,output):
    before=(ROOT/'tools/reports/context-search-2026-10-16/diagnosis/audit.tsv').read_text().splitlines()
    after=(observed/'audit.tsv').read_text().splitlines()
    visible=(observed/'visible.tsv').read_text().splitlines()
    lookup={tuple(f[:4]):s for s in ordinary.read_text().splitlines() if (f:=s.split('\t'))}
    if len(after)!=264 or len(visible)!=264:raise ValueError('Incomplete diagnostic')
    transitions=Counter();stages=Counter();gained=0
    for old,new,actual in zip(before,after,visible):
        a=old.split('\t');b=new.split('\t');c=actual.split('\t')
        if a[:4]!=b[:4] or b[:4]!=c[:4] or lookup[tuple(c[:4])]!=actual:raise ValueError('Diagnostic changed ordinary output')
        # Baseline categorizer calls the final bucket outside_display20 even
        # for newly visible targets; use actual ordinary rank for that bucket.
        stage='visible' if int(c[4])>0 else b[4]
        transitions[a[4]+' -> '+stage]+=1;stages[stage]+=1;gained+=int(int(c[4])>0)
    output.mkdir(parents=True,exist_ok=True)
    for name in ('audit.tsv','visible.tsv'):shutil.copyfile(observed/name,output/name)
    value=dict(parent_revision=BASELINE,arm='half',cases=264,all_ordinary_lists_match=True,
        before=dict(Counter(s.split('\t')[4] for s in before)),after=dict(stages),transitions=dict(transitions),
        newly_visible_in_observed_missing_subset=gained,
        output_sha256={n:digest(output/n) for n in ('audit.tsv','visible.tsv')},
        limitation='Fixed exposed missing subset only; excludes regressions among originally visible targets. Selected-option reachability is an upper bound; stage changes are observations, not unique causal attribution. Does not override full1450 adoption gates.')
    (output/'summary.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path)
    a=s.add_parser('report');a.add_argument('observed',type=Path);a.add_argument('ordinary',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work)
    else:report(a.observed,a.ordinary,a.output)
