#!/usr/bin/env python3
"""Validate and compare complete, ordered native outputs without fitting a model."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from prepare_prefix_retrieval import BASELINE
from prepare_tatoeba_corpus import digest
from report_search_recovery import metrics,paired
from train_candidate_ranker import matches
from train_phrase_model import reverse_codes

def compare(cases,before,after):
    inputs=[s.split('\t') for s in cases.read_text().splitlines() if s and not s.startswith('#')]
    if not inputs or any(len(r)!=4 for r in inputs):raise ValueError('Named four-column inputs required')
    reverse=reverse_codes();arms=[]
    for path in (before,after):
        rows=[s.split('\t') for s in path.read_text().splitlines()]
        if len(rows)!=len(inputs):raise ValueError('Partial evaluation output')
        for case,row in zip(inputs,rows):
            if len(row)!=6 or row[:4]!=case:raise ValueError('Native output order changed')
            values=row[5].split('|') if row[5] else []
            if len(values)>20 or len(set(values))!=len(values):raise ValueError('Invalid display bounds')
            if any(not matches(row[2],v,reverse) for v in values):raise ValueError('Inexact candidate')
            rank=values.index(row[3])+1 if row[3] in values else 0
            if int(row[4])!=rank:raise ValueError('Invalid target rank')
        arms.append(rows)
    old,new=arms;groups=defaultdict(lambda:([],[]))
    for b,a in zip(old,new):groups[b[0]][0].append(b);groups[b[0]][1].append(a)
    no_loss=lambda b,a:all(metrics(a)[k]>=metrics(b)[k] for k in ('top1','top5','top20'))
    return dict(baseline_revision=BASELINE,cases_sha256=digest(cases),
        output_sha256={'before':digest(before),'after':digest(after)},
        before=metrics(old),after=metrics(new),paired=paired(old,new),
        per_set={g:dict(before=metrics(b),after=metrics(a),no_count_loss=no_loss(b,a)) for g,(b,a) in groups.items()},
        no_per_set_count_loss=all(no_loss(b,a) for b,a in groups.values()),
        rank_changes=[dict(source=b[0],code=b[2],target=b[3],before=int(b[4]),after=int(a[4]))
                      for b,a in zip(old,new) if b[4]!=a[4]],
        exact_codes_and_display_bounds=True)

def survival_diagnosis(cases,after,diagnostics,intervention_enabled=True):
    inputs=[s.split('\t') for s in cases.read_text().splitlines() if s and not s.startswith('#')]
    results=[s.split('\t') for s in after.read_text().splitlines()]
    rows=[s.split('\t') for s in diagnostics.read_text().splitlines()]
    if len(inputs)!=len(results) or len(inputs)!=len(rows):raise ValueError('Partial survival diagnostics')
    counts=defaultdict(int);missing=[];additions=0;intervened=0
    for case,result,row in zip(inputs,results,rows):
        if len(row)!=8 or row[:4]!=case or result[:4]!=case:raise ValueError('Survival diagnostics order changed')
        if any(v not in ('true','false') for v in row[5:]):raise ValueError('Invalid survival flag')
        added=int(row[4]);generated,completed,eligible=(v=='true' for v in row[5:]);rank=int(result[4])
        if added<0 or (not intervention_enabled and added) or (completed and not generated) or (eligible and not completed) or (rank>0 and not eligible):
            raise ValueError('Inconsistent survival flags')
        additions+=added;intervened+=added>0
        reason=('displayed' if rank>0 else 'not_generated' if not generated else
                'completed_pool_cut' if not completed else 'confidence_filtered' if not eligible else 'outside_twenty')
        counts[reason]+=1
        if rank==0:missing.append(dict(source=case[0],code=case[2],target=case[3],reason=reason))
    return dict(cases=len(rows),intervention_enabled=intervention_enabled,intervened_cases=intervened,added_prefixes=additions,
                outcomes=dict(counts),missing=missing,diagnostics_sha256=digest(diagnostics),
                warning=('Gold-assisted diagnostic intervention, not deployable accuracy or a formal maximum.' if intervention_enabled else
                         'Observer-only baseline; gold labels do not affect search decisions.')+
                        ' No statistical population claim. Missing generation can still reflect option limits or a different exact tokenization.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','before','after','output'):p.add_argument(name,type=Path)
    p.add_argument('--diagnostics',type=Path)
    p.add_argument('--control-diagnostics',action='store_true',help='Validate flags from an observer-only run')
    a=p.parse_args();result=compare(a.cases,a.before,a.after)
    if a.diagnostics:result['survival_diagnosis']=survival_diagnosis(a.cases,a.after,a.diagnostics,not a.control_diagnostics)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_set','rank_changes','survival_diagnosis')},ensure_ascii=False))
