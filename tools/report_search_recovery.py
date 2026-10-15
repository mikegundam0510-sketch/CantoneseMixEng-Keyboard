#!/usr/bin/env python3
"""Report the three frozen native500 arms; select only predeclared delivery arms."""
import argparse
import csv
import json
import math
from pathlib import Path
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes

DATA=ROOT/'tools/data/search_recovery'


def metrics(rows):
    ranks=[int(r[4]) for r in rows]
    return dict(cases=len(rows),top1=sum(r==1 for r in ranks),top5=sum(0<r<=5 for r in ranks),
                top20=sum(r>0 for r in ranks),mrr=sum(1/r for r in ranks if r)/len(ranks))


def paired(before,after):
    result={}
    for key,limit in [('first',1),('top5',5),('top20',20)]:
        gained=sum(not 0<int(b[4])<=limit and 0<int(a[4])<=limit for b,a in zip(before,after))
        lost=sum(0<int(b[4])<=limit and not 0<int(a[4])<=limit for b,a in zip(before,after))
        n=gained+lost
        p=min(1,2*sum(math.comb(n,k) for k in range(min(gained,lost)+1))/2**n)
        result[key]=dict(gained=gained,lost=lost,net=gained-lost,paired_exact_two_sided_p=p)
    return result


def report(base,search,combined,output):
    selected=json.loads((DATA/'selection.json').read_text())
    assert digest(DATA/'heldout.tsv')==selected['heldout_sha256']
    assert digest(DATA/'protocol.json')==selected['protocol_sha256']
    assert digest(DATA/'candidate-relation_ranker.b64')==selected['combined_model_sha256']
    assert digest(DATA/'search-only-relation_ranker.b64')==selected['search_model_sha256']
    cases=list(csv.reader((DATA/'heldout.tsv').open(),delimiter='\t'));reverse=reverse_codes()
    arms={}
    for name,path in [('baseline',base),('search',search),('combined',combined)]:
        rows=list(csv.reader(path.open(),delimiter='\t'));assert len(rows)==len(cases)==500
        for case,row in zip(cases,rows):
            assert len(row)==6 and row[:4]==case
            values=row[5].split('|') if row[5] else []
            assert len(values)<=20 and len(set(values))==len(values)
            assert all(matches(row[2],v,reverse) for v in values)
            assert int(row[4])==(values.index(row[3])+1 if row[3] in values else 0)
        arms[name]=rows
    scores={k:metrics(v) for k,v in arms.items()}
    no_loss=lambda a,b:all(scores[a][m]>=scores[b][m] for m in ['top1','top5','top20'])
    useful=lambda a,b:any(scores[a][m]>scores[b][m] for m in ['top1','top5','top20'])
    search_pass=no_loss('search','baseline') and useful('search','baseline')
    head_pass=no_loss('combined','baseline') and no_loss('combined','search') and scores['combined']['top1']>scores['search']['top1']
    delivery='combined' if head_pass else 'search' if search_pass else 'baseline'
    comparisons={f'{a}_vs_{b}':paired(arms[b],arms[a]) for a,b in [('search','baseline'),('combined','search'),('combined','baseline')]}
    result=dict(baseline_revision=selected['baseline_revision'],metrics=scores,comparisons=comparisons,
                search_qualifies_alone=search_pass,head_qualifies=head_pass,delivery=delivery,
                selection_sha256=digest(DATA/'selection.json'),case_sha256=digest(DATA/'heldout.tsv'),
                output_sha256={name:digest(path) for name,path in [('baseline',base),('search',search),('combined',combined)]},
                no_post_reserve_accuracy_tuning=True,exact_codes_and_display_bounds=True,
                limitations='Public dictionary example500, now observed. Small paired changes are not population typing accuracy, physical Fold7 evidence or1.0 qualification.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','search','combined','output']:p.add_argument(name,type=Path)
    a=p.parse_args();report(a.baseline,a.search,a.combined,a.output)
