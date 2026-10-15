#!/usr/bin/env python3
"""Validate actual native calibration lists against the predeclared joint gate."""
import argparse
import json
from pathlib import Path
from prepare_joint_ranking import BASELINE
from report_prefix_retrieval import compare
from report_search_recovery import metrics

def assess(cases,before,after,output):
    result=compare(cases,before,after);result['baseline_revision']=BASELINE
    old=[s.split('\t') for s in before.read_text().splitlines()];new=[s.split('\t') for s in after.read_text().splitlines()]
    joint=lambda r:r[0]=='joint:validation'
    if sum(map(joint,old))!=100 or len(old)!=800:raise ValueError('Expected frozen100 plus known700 calibration')
    bv,av=metrics([r for r in old if joint(r)]),metrics([r for r in new if joint(r)])
    bo,ao=metrics([r for r in old if not joint(r)]),metrics([r for r in new if not joint(r)])
    old_safe=all(all(d['before'][k]-d['after'][k]<=d['before']['cases']*.01+1e-9 for k in ('top1','top5'))
                 for source,d in result['per_set'].items() if source!='joint:validation')
    result['calibration_gate']=dict(new_counts_nondecreasing=all(av[k]>=bv[k] for k in ('top1','top5','top20')),
        old_aggregate_counts_nondecreasing=all(ao[k]>=bo[k] for k in ('top1','top5','top20')),
        old_per_set_head_top5_loss_within_one_percentage_point=old_safe,
        head_or_top5_net_gain=any(result['after'][k]>result['before'][k] for k in ('top1','top5')))
    result['qualified']=all(result['calibration_gate'].values())
    result['new100']={'before':bv,'after':av};result['old700']={'before':bo,'after':ao}
    groups=list(result['per_set'].values())
    result['selection_key']=[sum(g['after'][key]/g['after']['cases'] for g in groups)/len(groups)
                             for key in ('top1','top5','top20')]
    result['selection_key'].append(sum(g['after']['mrr'] for g in groups)/len(groups))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('before','after','new100','old700','qualified','calibration_gate','selection_key')}))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','before','after','output'):p.add_argument(name,type=Path)
    a=p.parse_args();assess(a.cases,a.before,a.after,a.output)
