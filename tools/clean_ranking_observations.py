#!/usr/bin/env python3
"""Reuse identical TRAIN inputs; observe only new clean inputs with native Java."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
from observe_joint_ranking import prepare as prepare_pool
from observe_structured_training import prepare as prepare_shadow
from pilot_final_hard_negatives import records
from prepare_clean_ranking import DATA
from prepare_joint_ranking import DATA as OLD
from prepare_tatoeba_corpus import digest
from prepare_joint_ranking import BASELINE

def cases(data=DATA):
    manifest=json.loads((data/'manifest.json').read_text())
    for name,sha in manifest['file_sha256'].items():
        if digest(data/name)!=sha:raise ValueError('Frozen clean data changed')
    rows=[tuple(s.split('\t')) for s in (data/'train.tsv').read_text().splitlines()]
    if any(len(r)!=4 or not r[0].startswith('train:') for r in rows) or len(rows)!=len(set(rows)):
        raise ValueError('Unique four-column TRAIN-only data required')
    return rows

def check_subset(path,data=DATA):
    rows=[tuple(s.split('\t')) for s in path.read_text().splitlines()]
    if not rows or len(rows)!=len(set(rows)) or not set(rows)<=set(cases(data)):raise ValueError('Non-TRAIN or duplicate clean observation')
    return rows

def split(work,old_observations,data=DATA):
    rows=cases(data)
    old_allowed=[tuple(s.split('\t')) for s in (OLD/'train.tsv').read_text().splitlines()]
    pools=[s.split('\t') for s in (old_observations/'pools.tsv').read_text().splitlines()]
    if [tuple(r[:4]) for r in pools]!=old_allowed:raise ValueError('Complete historical TRAIN pools required')
    previous=json.loads((OLD/'model015/training-report.json').read_text())
    for name,field in (('pools.tsv','pools_sha256'),('prefix.tsv','prefix_sha256')):
        if digest(old_observations/name)!=previous[field]:raise ValueError('Historical TRAIN observation changed')
    old_pools={tuple(r[:4]):'\t'.join(r) for r in pools};by_input={tuple(r[1:4]):tuple(r[:4]) for r in pools}
    old_visible={tuple(f[:4]):s for s in (old_observations/'visible.tsv').read_text().splitlines() if (f:=s.split('\t'))}
    old_prefix=defaultdict(list)
    for s in (old_observations/'prefix.tsv').read_text().splitlines():old_prefix[tuple(s.split('\t')[:4])].append(s)
    if work.exists() and any(work.iterdir()):raise ValueError('Preserve existing observation work')
    work.mkdir(parents=True,exist_ok=True);reused=work/'reused';reused.mkdir();outputs={n:[] for n in ('pools.tsv','visible.tsv','prefix.tsv')};todo=[];mapping=[]
    for row in rows:
        old_key=by_input.get(row[1:])
        if old_key is None:todo.append(row);continue
        for name,values in (('pools.tsv',[old_pools[old_key]]),('visible.tsv',[old_visible[old_key]]),('prefix.tsv',old_prefix[old_key])):
            outputs[name].extend(row[0]+s[s.index('\t'):] for s in values)
        mapping.append(dict(current=row,previous=old_key))
    for name,lines in outputs.items():(reused/name).write_text(''.join(s+'\n' for s in lines))
    for i in range(3):(work/f'train-{i}.tsv').write_text(''.join('\t'.join(r)+'\n' for r in todo[i::3]))
    note=dict(reused=len(mapping),new=len(todo),training_sha256=digest(data/'train.tsv'),
        previous_sha256={name:digest(old_observations/name) for name in outputs},mapping=mapping,
        policy='Cache reuse only for identical context, code and gold under exactly unchanged baseline assets. Source IDs only label observations and are re-keyed while original TRAIN family attribution is preserved. No evaluation cache.')
    (work/'reuse.json').write_text(json.dumps(note,ensure_ascii=False,indent=2)+'\n');print('reused',len(mapping),'new',len(todo))

def run(work,input_cases,output,kind='pool',data=DATA):
    check_subset(input_cases,data)
    if output.exists():raise ValueError('Preserve existing native output')
    pending=output.with_name(output.name+'.pending');pending.mkdir(parents=True,exist_ok=False)
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RelationEvaluation',
        str(work/'app/src/main/assets'),str(input_cases.resolve()),str(pending.resolve())],check=True)
    for name in (('pools.tsv','visible.tsv') if kind=='pool' else ('audit.tsv','visible.tsv')):
        lines=(pending/name).read_text().splitlines()
        if [tuple(s.split('\t')[:4]) for s in lines]!=check_subset(input_cases,data):raise ValueError('Partial native TRAIN output')
    pending.rename(output)

def merge(work,output,data=DATA):
    expected=cases(data);allowed=set(expected)
    if output.exists():raise ValueError('Preserve completed TRAIN observations')
    reuse=json.loads((work/'reuse.json').read_text())
    if reuse['training_sha256']!=digest(data/'train.tsv'):raise ValueError('Cache mapping from another TRAIN dataset')
    output.mkdir(parents=True,exist_ok=False)
    for name in ('pools.tsv','visible.tsv','prefix.tsv'):
        groups={row:[] for row in expected}
        for folder in [work/'reused']+[work/f'train-{i}' for i in range(3)]:
            for line in (folder/name).read_text().splitlines():
                key=tuple(line.split('\t')[:4])
                if key not in allowed:raise ValueError('Unexpected training observation')
                groups[key].append(line)
        if name!='prefix.tsv' and any(len(v)!=1 for v in groups.values()):raise ValueError('Partial/duplicate training pool')
        (output/name).write_text(''.join(s+'\n' for key in expected for s in groups[key]))
    missing=[tuple(r[k] for k in ('source','context','code','gold')) for r in records(output/'pools.tsv') if r['gold'] not in r['values']]
    for i in range(3):(work/f'repair-{i}.tsv').write_text(''.join('\t'.join(r)+'\n' for r in missing[i::3]))
    note=dict(baseline_revision=BASELINE,training_sha256=digest(data/'train.tsv'),reused=reuse['reused'],new=reuse['new'],
        missing=len(missing),output_sha256={n:digest(output/n) for n in ('pools.tsv','visible.tsv','prefix.tsv')})
    (output/'observation.json').write_text(json.dumps(note,indent=2)+'\n');print(json.dumps(note))

def resplit(work,previous,previous_data,data=DATA):
    """Reuse complete same-baseline observations after a source-parser correction."""
    rows=cases(data);old_rows=cases(previous_data);meta=json.loads((previous/'observation.json').read_text())
    if meta['baseline_revision']!=BASELINE or meta['training_sha256']!=digest(previous_data/'train.tsv'):raise ValueError('Wrong prior dataset/baseline')
    for name,sha in meta['output_sha256'].items():
        if digest(previous/name)!=sha:raise ValueError('Previous observations changed')
    pools={tuple(f[:4]):s for s in (previous/'pools.tsv').read_text().splitlines() if (f:=s.split('\t'))}
    if set(pools)!=set(old_rows):raise ValueError('Incomplete prior TRAIN observations')
    visible={tuple(f[:4]):s for s in (previous/'visible.tsv').read_text().splitlines() if (f:=s.split('\t'))}
    prefix=defaultdict(list)
    for s in (previous/'prefix.tsv').read_text().splitlines():prefix[tuple(s.split('\t')[:4])].append(s)
    by_input={r[1:]:r for r in old_rows};outputs={n:[] for n in ('pools.tsv','visible.tsv','prefix.tsv')};todo=[];mapping=[]
    if work.exists():raise ValueError('Preserve existing re-keyed observations')
    work.mkdir(parents=True);(work/'reused').mkdir()
    for row in rows:
        old=by_input.get(row[1:])
        if old is None:todo.append(row);continue
        for name,values in (('pools.tsv',[pools[old]]),('visible.tsv',[visible[old]]),('prefix.tsv',prefix[old])):
            outputs[name].extend(row[0]+s[s.index('\t'):] for s in values)
        mapping.append(dict(current=row,previous=old))
    for name,values in outputs.items():(work/'reused'/name).write_text(''.join(s+'\n' for s in values))
    for i in range(3):(work/f'train-{i}.tsv').write_text(''.join('\t'.join(r)+'\n' for r in todo[i::3]))
    (work/'reuse.json').write_text(json.dumps(dict(reused=len(mapping),new=len(todo),training_sha256=digest(data/'train.tsv'),mapping=mapping,
        previous_sha256=meta['output_sha256'],policy='Same context/code/gold after parser boundary correction; source attribution re-keyed; no model or evaluation change.'),ensure_ascii=False,indent=2)+'\n')
    print('reused',len(mapping),'new',len(todo))

def merge_shadow(work,pools,output,data=DATA):
    expected=[tuple(r[k] for k in ('source','context','code','gold')) for r in records(pools/'pools.tsv') if r['gold'] not in r['values']]
    ordinary={tuple(f[:4]):s for s in (pools/'visible.tsv').read_text().splitlines() if (f:=s.split('\t'))}
    if output.exists():raise ValueError('Preserve existing shadow observations')
    output.mkdir(parents=True,exist_ok=False);all_pairs=[];counts={}
    for name in ('audit.tsv','visible.tsv','pairs.tsv'):
        groups={key:[] for key in expected}
        for i in range(3):
            for s in (work/f'repair-{i}'/name).read_text().splitlines():
                key=tuple(s.split('\t')[:4])
                if key not in groups:raise ValueError('Unexpected reconstructed target')
                groups[key].append(s)
        if name!='pairs.tsv' and any(len(v)!=1 for v in groups.values()):raise ValueError('Partial/duplicate shadow traces')
        if name=='visible.tsv' and any(groups[key][0]!=ordinary[key] for key in expected):raise ValueError('Gold reconstruction changed inference')
        (output/name).write_text(''.join(s+'\n' for key in expected for s in groups[key]))
    for s in (output/'audit.tsv').read_text().splitlines():
        f=s.split('\t')
        if len(f)!=14 or f[5]!='true' or f[13]!='true':raise ValueError('Unexpected un-emittable clean training target')
    report=dict(missing_targets=len(expected),ordinary_inference_exact_parity=len(expected),
        pairs=len((output/'pairs.tsv').read_text().splitlines()),output_sha256={n:digest(output/n) for n in ('audit.tsv','visible.tsv','pairs.tsv')})
    (output/'observation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('split','resplit','prepare-pool','prepare-shadow','run','merge','merge-shadow'))
    p.add_argument('work',type=Path);p.add_argument('--old',type=Path);p.add_argument('--cases',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--kind',choices=('pool','shadow'),default='pool');p.add_argument('--previous-data',type=Path);a=p.parse_args()
    if a.mode=='split':split(a.work,a.old)
    elif a.mode=='resplit':resplit(a.work,a.old,a.previous_data)
    elif a.mode=='prepare-pool':prepare_pool(a.work)
    elif a.mode=='prepare-shadow':prepare_shadow(a.work)
    elif a.mode=='run':run(a.work,a.cases,a.output,a.kind)
    elif a.mode=='merge':merge(a.work,a.output)
    else:merge_shadow(a.work,a.old,a.output)
