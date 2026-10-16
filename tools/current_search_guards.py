#!/usr/bin/env python3
"""Prepare explicitly model-enabled learning/timing harnesses and merge guards."""
import argparse
import json
from pathlib import Path
import subprocess

from observe_current_search import BASELINE
from report_prefix_retrieval import compare
from train_phrase_model import ROOT


def harnesses(work):
    java=(ROOT/'tools/ContextLearningEvaluation.java').read_text()
    anchor='? PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))) : null);'
    if java.count(anchor)!=1:raise ValueError('Learning constructor changed')
    java=java.replace(anchor,anchor[:-2]+',\n            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("joint_ranker.b64"))));')
    target=work/'ContextLearningEvaluation.java';target.write_text(java)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-d',str(work/'classes'),str(target)],check=True)
    java=(ROOT/'tools/PairedRankingPerformance.java').read_text()
    anchor='            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());'
    if java.count(anchor)!=1:raise ValueError('Performance constructor changed')
    java=java.replace(anchor,'''            if(Files.exists(assets.resolve("joint_ranker.b64"))) {
                types.add(rankerClass);
                values.add(rankerClass.getMethod("loadWords",InputStream.class)
                    .invoke(null,Files.newInputStream(assets.resolve("joint_ranker.b64"))));
            }
'''+anchor)
    target=work/'PairedRankingPerformance.java';target.write_text(java)
    subprocess.run(['javac','-encoding','UTF-8','-d',str(work/'classes'),str(target)],check=True)


def merge(shards,output):
    cases=ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv'
    baseline=ROOT/'tools/reports/clean-language-models-2026-10-16/guard3893.tsv'
    inputs=cases.read_text().splitlines();rows=[None]*len(inputs)
    if len(inputs)!=3893:raise ValueError('Expected fixed guard cases')
    for part in range(4):
        if (shards/f'cases-{part}.tsv').read_text().splitlines()!=inputs[part::4]:raise ValueError('Guard input changed')
        values=(shards/f'output-{part}.tsv').read_text().splitlines()
        if len(values)!=len(inputs[part::4]):raise ValueError('Partial guard output')
        for at,line in enumerate(values):rows[part+4*at]=line
    output.mkdir(parents=True,exist_ok=True)
    merged=output/'guard3893.tsv';merged.write_text(''.join(r+'\n' for r in rows))
    report=compare(cases,baseline,merged);report['parent_revision']=BASELINE
    report['guard_gate']=dict(
        aggregate_counts_nondecreasing=all(report['after'][k]>=report['before'][k] for k in ('top1','top5','top20')),
        per_set_first_top5_loss_within_one_pp=all(all(g['before'][k]-g['after'][k]<=g['before']['cases']*.01+1e-9
            for k in ('top1','top5')) for g in report['per_set'].values()))
    report['qualified']=all(report['guard_gate'].values())
    (output/'guard3893.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('before','after','guard_gate','qualified')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('harnesses');a.add_argument('work',type=Path)
    a=s.add_parser('merge');a.add_argument('shards',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='harnesses':harnesses(a.work)
    else:merge(a.shards,a.output)
