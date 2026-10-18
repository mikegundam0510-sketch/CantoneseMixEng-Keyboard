"""Use the sealed unused500 once, after exact native and Android qualification."""
import argparse
import json
import subprocess
from study import ROOT,DATA,WORK,REPORTS,sha,write,verify,BASELINE
from report_prefix_retrieval import compare

CASES=ROOT/'tools/data/prefix_language/reserve.tsv'


def qualified():
    verify();q=json.loads((DATA/'qualification.json').read_text())
    if q['status']!='All pre-independent gates passed' or sha(CASES)!=q['reserve_sha256']:
        raise ValueError('Independent qualification missing')
    for name,wanted in {**q['source_model_sha256'],**q['evidence_sha256']}.items():
        if sha(ROOT/name)!=wanted:raise ValueError('Frozen independent candidate changed: '+name)


def run():
    qualified()
    write(DATA/'reserve-started-parent.json',dict(qualification_sha256=sha(DATA/'qualification.json'),cases_sha256=sha(CASES),
        policy='One pass, actual unmodified parent classes. No retry or outcome tuning.'))
    rows=CASES.read_text().splitlines()
    if len(rows)!=500:raise ValueError('Expected unused500')
    path=WORK/'reserve-inputs.tsv'
    with path.open('x') as out:
        for row in rows:out.write('\t'.join(row.split('\t')[:3])+'\n')
    parent=WORK/'reserve-parent.tsv';stage=WORK/'native'
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.ParentEvaluation',
        str(stage/'app/src/main/assets'),str(path),str(parent)],check=True)
    predicted=parent.read_text().splitlines()
    if len(predicted)!=500:raise ValueError('Partial independent parent')
    inputs=WORK/'reserve-candidate-inputs.tsv'
    with inputs.open('x') as out:
        for row,prediction in zip(rows,predicted):
            if row.split('\t')[:3]!=prediction.split('\t')[:3]:raise ValueError('Independent identity differs')
            out.write(prediction+'\t\n')
    qualified()
    write(DATA/'reserve-started-candidate.json',dict(qualification_sha256=sha(DATA/'qualification.json'),
        parent_predictions_sha256=sha(parent),cases_sha256=sha(CASES),policy='One candidate pass, frozen full Java decoder.'))
    candidate=WORK/'reserve-candidate.tsv';stage=WORK/'candidate'
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.IntegratedEvaluation',
        str(stage/'app/src/main/assets'),str(inputs),str(candidate)],check=True)
    for role,path in [('parent',parent),('candidate',candidate)]:
        predictions=path.read_text().splitlines()
        if len(predictions)!=500:raise ValueError('Partial independent output')
        with (REPORTS/('independent500-'+role+'.tsv')).open('x') as out:
            for row,prediction in zip(rows,predictions):
                f,p=row.split('\t'),prediction.split('\t')
                if f[:3]!=p[:3]:raise ValueError('Independent identity mismatch')
                values=p[3].split('|') if p[3] else [];rank=values.index(f[3])+1 if f[3] in values else 0
                out.write(row+'\t'+str(rank)+'\t'+p[3]+'\n')
    result=compare(CASES,REPORTS/'independent500-parent.tsv',REPORTS/'independent500-candidate.tsv')
    result['baseline_revision']=BASELINE
    result['gates']=dict(first18_retained=True,counts_nondecreasing=all(result['after'][k]>=result['before'][k] for k in ('top1','top5','top20')),
        positive_top20_gain=result['after']['top20']>result['before']['top20'])
    result['qualified']=all(result['gates'].values());result['substantial_gain']=False
    result['qualification_sha256']=sha(DATA/'qualification.json')
    result['decision']='Adopt exact validated tail supplement; no APK or1.0 claim' if result['qualified'] else 'Reject this tail supplement; retain production; no independent-outcome tuning'
    write(REPORTS/'independent500.json',result)
    write(DATA/'decision.json',{k:result[k] for k in ('baseline_revision','before','after','paired','gates','qualified','substantial_gain','qualification_sha256','decision')})
    print(json.dumps({k:result[k] for k in ('before','after','paired','gates','qualified','decision')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['run']);p.parse_args();run()
