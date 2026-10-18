"""Complete reporting after the strict prefix guard stopped the original reporter.

No prediction, source/model repair or changed gate: preserve the failed first
study, including its complete gain/loss and the short-list contract violation.
"""
import json
from shared import ROOT,DATA,WORK,REPORTS,BASELINE,write,verify
from expanded_model import load,Codec
from report_prefix_retrieval import compare

def main():
    verify();cases=ROOT/'tools/data/context_search/calibration1450.tsv'
    before=ROOT/'tools/reports/tail-supplement-2026-10-18/native-calibration1450.tsv'
    original=cases.read_text().splitlines();parents=before.read_text().splitlines()
    predictions=(WORK/'predictions.tsv').read_text().splitlines()
    if not len(original)==len(parents)==len(predictions)==1450:raise ValueError('Incomplete predictions')
    output=REPORTS/'completed1450.tsv';violations=[]
    with output.open('x') as out:
        for i,(case,parent,prediction) in enumerate(zip(original,parents,predictions)):
            f,b,p=case.split('\t'),parent.split('\t'),prediction.split('\t')
            if f[:3]!=p[:3]:raise ValueError('Prediction identity differs')
            values=p[3].split('|') if p[3] else [];old=b[5].split('|') if b[5] else []
            n=min(18,len(old))
            if values[:n]!=old[:n]:violations.append(dict(index=i,source=f[0],code=f[2],deployed_list_size=len(old)))
            rank=values.index(f[3])+1 if f[3] in values else 0
            out.write(case+'\t'+str(rank)+'\t'+p[3]+'\n')
    r=compare(cases,before,output);r['baseline_revision']=BASELINE
    r['gates']=dict(first18_identical=not violations,first_top5_unchanged=all(r['after'][k]==r['before'][k] for k in ('top1','top5')),
        aggregate_top20_gain=r['after']['top20']>r['before']['top20'],every_set_nondecreasing=r['no_per_set_count_loss'])
    r['qualified']=all(r['gates'].values());r['deployed_prefix_violations']=violations
    write(REPORTS/'completed1450.json',r)
    oldchars=load(ROOT/'tools/data/code_generator/models/teacher.npz')[1]
    oldcodec=Codec(oldchars,json.loads((ROOT/'tools/data/code_generator/codes.json').read_text()))
    chars=load(DATA/'models/expanded.npz')[1];codec=Codec(chars,json.loads((DATA/'codes.json').read_text()))
    support=dict(cases=1450,old_unsupported=sum(oldcodec.align(f[2],f[3]) is None for f in map(lambda s:s.split('\t'),original)),
        expanded_unsupported=sum(codec.align(f[2],f[3]) is None for f in map(lambda s:s.split('\t'),original)),
        scope='Static support only, not hit rate or selection. Alphabet fixed from TRAIN before these labels were assessed.')
    write(REPORTS/'static-support.json',support)
    write(DATA/'selection.json',dict(selected=None,before=r['before'],after=r['after'],paired=r['paired'],gates=r['gates'],
        original_fixed_trial_rejected=True,reserve_decoded=False,
        decision='Original vocabulary-only replacement rejected because one deployed first18 prefix differs. No original protocol, checkpoint or predictions changed.'))
    print(json.dumps({k:r[k] for k in ('before','after','paired','gates','qualified','deployed_prefix_violations')}));print(json.dumps(support))

if __name__=='__main__':main()
