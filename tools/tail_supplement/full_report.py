"""Validate the complete Java decoder separately from cached-proposal screening."""
import json
from study import ROOT,DATA,WORK,REPORTS,CASES,BEFORE,BASELINE,verify,write
from report_prefix_retrieval import compare


def main():
    verify()
    inputs=(WORK/'inputs.tsv').read_text().splitlines()+(WORK/'guard-inputs.tsv').read_text().splitlines()
    rows=[None]*len(inputs)
    for part in range(4):
        shard=(WORK/f'full-output-{part}.tsv').read_text().splitlines()
        if len(shard)!=len(inputs[part::4]):raise ValueError('Partial full Java output')
        rows[part::4]=shard
    if len(inputs)!=5343:raise ValueError('Expected known1450+3893')
    records={}
    specs=[('calibration1450',CASES,BEFORE,rows[:1450],WORK/'predictions.tsv'),
           ('guard3893',ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv',
            ROOT/'tools/reports/pinned-head-2026-10-17/guard3893.tsv',rows[1450:],WORK/'guard-predictions.tsv')]
    for name,cases,before,predictions,screened in specs:
        original=cases.read_text().splitlines();parents=before.read_text().splitlines()
        if len(original)!=len(predictions):raise ValueError('Full evaluation size differs')
        output=REPORTS/('native-'+name+'.tsv')
        with output.open('x') as out:
            for case,prediction,parent in zip(original,predictions,parents):
                f,p,b=case.split('\t'),prediction.split('\t'),parent.split('\t')
                if f[:3]!=p[:3]:raise ValueError('Full input identity differs')
                values=p[3].split('|') if p[3] else [];old=b[5].split('|') if b[5] else []
                n=min(18,len(old))
                if old[:n]!=values[:n] or len(set(values)-set(old))>2:raise ValueError('Full first18/new-slot contract differs')
                rank=values.index(f[3])+1 if f[3] in values else 0
                out.write(case+'\t'+str(rank)+'\t'+p[3]+'\n')
        result=compare(cases,before,output);result['baseline_revision']=BASELINE
        result['screening_list_differences']=sum(a!=b for a,b in zip(predictions,screened.read_text().splitlines()))
        result['gates']=dict(first18_identical=True,
            aggregate_counts_nondecreasing=all(result['after'][k]>=result['before'][k] for k in ('top1','top5','top20')),
            every_set_counts_nondecreasing=result['no_per_set_count_loss'])
        if name=='calibration1450':result['gates']['aggregate_top20_gain']=result['after']['top20']>result['before']['top20']
        result['qualified']=all(result['gates'].values());records[name]=result
        write(REPORTS/('native-'+name+'.json'),result)
        print(name,json.dumps({k:result[k] for k in ('before','after','paired','screening_list_differences','qualified')}))
    write(DATA/'native-selection.json',dict(selected='candidate' if all(v['qualified'] for v in records.values()) else None,
        gates={k:v['gates'] for k,v in records.items()},independent500_decoded=False,
        decision='Proceed to remaining learning/Android/timing guards' if all(v['qualified'] for v in records.values()) else 'Reject; preserve production and unused500'))


if __name__=='__main__':main()
