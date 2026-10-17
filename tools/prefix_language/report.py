"""Predeclared ordinary-output comparison, never oracle-assisted decoding."""
import json
from experiment import ROOT,DATA,REPORTS,BASELINE,frozen,write
from report_prefix_retrieval import compare
from report_search_recovery import metrics


def report():
    frozen();scores={}
    cases=ROOT/'tools/data/context_search/calibration1450.tsv'
    before=ROOT/'tools/reports/pinned-head-2026-10-17/calibration1450.tsv'
    for arm in ('language','trained'):
        r=compare(cases,before,REPORTS/(arm+'-1450.tsv'));r['baseline_revision']=BASELINE
        b=[s.split('\t') for s in before.read_text().splitlines()]
        a=[s.split('\t') for s in (REPORTS/(arm+'-1450.tsv')).read_text().splitlines()]
        new=lambda rows:metrics([x for x in rows if x[0]=='context-search:validation'])
        old=lambda rows:metrics([x for x in rows if x[0]!='context-search:validation'])
        bn,an,bo,ao=new(b),new(a),old(b),old(a)
        r['new150']=dict(before=bn,after=an);r['old1300']=dict(before=bo,after=ao)
        r['gates']=dict(new_and_old_counts_nondecreasing=all(y[k]>=x[k] for x,y in ((bn,an),(bo,ao)) for k in ('top1','top5','top20')),
            aggregate_coverage_gain=r['after']['top20']>r['before']['top20'],
            per_set_first_top5_loss_within_one_pp=all(all(g['before'][k]-g['after'][k]<=g['before']['cases']*.01+1e-9 for k in ('top1','top5')) for g in r['per_set'].values()))
        r['qualified']=all(r['gates'].values());scores[arm]=r;write(REPORTS/(arm+'-1450.json'),r)
    eligible=[a for a,r in scores.items() if r['qualified']]
    def key(a):
        groups=list(scores[a]['per_set'].values())
        return tuple(sum(g['after'][k]/g['after']['cases'] for g in groups)/len(groups) for k in ('top20','top1','top5'))+(sum(g['after']['mrr'] for g in groups)/len(groups),a=='language')
    selected=max(eligible,key=key) if eligible else None
    value=dict(selected=selected,reserve_decoded=False,trials={a:{k:r[k] for k in ('before','after','new150','old1300','gates','qualified')} for a,r in scores.items()},
        decision='Proceed to fixed guards' if selected else 'Reject both; retain adopted28dfb69; preserve unused new500')
    write(DATA/'selection.json',value);print(json.dumps(value))


if __name__=='__main__':report()
