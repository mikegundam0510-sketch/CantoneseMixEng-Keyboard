"""One prequalified actual-parent/candidate pass on the previously unused500."""
import argparse
import json
import subprocess
from study import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write,verify_inference
from report_prefix_retrieval import compare

CASES=ROOT/'tools/data/vocabulary_expansion/reserve.tsv'


def verify():
    verify_inference()
    q=json.loads((DATA/'qualification.json').read_text())
    if sha(CASES)!=q['reserve_sha256']:raise ValueError('Reserve changed')
    for group in ('source_model_sha256','evidence_sha256'):
        for name,wanted in q[group].items():
            if sha(ROOT/name)!=wanted:raise ValueError('Prequalified implementation/evidence changed: '+name)


def start():
    verify()
    write(DATA/'reserve-started.json',dict(qualification_sha256=sha(DATA/'qualification.json'),
        cases_sha256=sha(CASES),parent_revision=BASELINE,one_pass_each=True))
    rows=CASES.read_text().splitlines()
    if len(rows)!=500:raise ValueError('Independent input count changed')
    with (WORK/'independent-parent-inputs.tsv').open('x') as out:
        for row in rows:out.write('\t'.join(row.split('\t')[:3])+'\n')
    print('New500 marked consumed before first inference; no later tuning')


def parent():
    verify()
    if not (DATA/'reserve-started.json').exists():raise ValueError('Independent start not sealed')
    stage=WORK/'native';output=WORK/'independent-parent.tsv'
    if output.exists():raise ValueError('Preserve independent parent result')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.DeployedEvaluation',
        str(stage/'app/src/main/assets'),str(WORK/'independent-parent-inputs.tsv'),str(output)],check=True)
    rows=output.read_text().splitlines()
    if len(rows)!=500:raise ValueError('Partial independent parent results')
    with (WORK/'independent-candidate-inputs.tsv').open('x') as out:
        for row in rows:out.write(row+'\t\n')


def candidate():
    verify();stage=WORK/'candidate';output=WORK/'independent-candidate.tsv'
    if output.exists():raise ValueError('Preserve independent candidate result')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.FusionIntegratedEvaluation',
        str(stage/'app/src/main/assets'),str(WORK/'independent-candidate-inputs.tsv'),str(output),'candidate'],check=True)


def report():
    verify();cases=CASES.read_text().splitlines()
    paths=[]
    for label in ('parent','candidate'):
        rows=(WORK/('independent-'+label+'.tsv')).read_text().splitlines()
        if len(rows)!=500:raise ValueError('Partial independent results')
        output=REPORTS/('independent500-'+label+'.tsv');paths.append(output)
        with output.open('x') as out:
            for case,pred in zip(cases,rows):
                f,p=case.split('\t'),pred.split('\t')
                if f[:3]!=p[:3]:raise ValueError('Independent identity mismatch')
                values=p[3].split('|') if p[3] else []
                rank=values.index(f[3])+1 if f[3] in values else 0
                out.write(case+'\t'+str(rank)+'\t'+p[3]+'\n')
    r=compare(CASES,*paths)
    for old,new in zip(paths[0].read_text().splitlines(),paths[1].read_text().splitlines()):
        a,b=old.split('\t')[5],new.split('\t')[5];a=a.split('|') if a else [];b=b.split('|') if b else []
        n=min(18,len(a))
        if a[:n]!=b[:n]:raise ValueError('Independent deployed prefix changed')
    r.update(parent_revision=BASELINE,independent_once_after_qualification=True,
        gates=dict(deployed_first18_identical=True,
            no_first_top5_top20_count_loss=all(r['after'][k]>=r['before'][k] for k in ('top1','top5','top20')),
            aggregate_top20_gain=r['after']['top20']>r['before']['top20']))
    r['qualified']=all(r['gates'].values())
    write(REPORTS/'independent500.json',r)
    write(DATA/'decision.json',dict(adopt=r['qualified'],independent_consumed=True,
        reason='All fixed gates passed; adopt exact prequalified implementation' if r['qualified']
        else 'Independent gain/nonregression gate failed; keep deployed app. Preserve consumed500 and rejected frozen candidate, no outcome tuning.'))
    print(json.dumps({k:r[k] for k in ('before','after','paired','gates','qualified')},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['start','parent','candidate','report']);a=p.parse_args()
    globals()[a.mode]()
