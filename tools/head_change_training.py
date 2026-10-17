#!/usr/bin/env python3
"""Prepare family-disjoint TRAIN displays and fit one numeric first-choice gate."""
import argparse
import base64
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from pilot_final_hard_negatives import records
from prepare_sentence_pretrain import group,write
from prepare_tatoeba_corpus import digest
from train_aligned_relations import family
from train_phrase_model import ROOT

DATA=ROOT/'tools/data/head_change'
MODEL=ROOT/'tools/data/sentence_pretrain/models/adapted.b64'
POOLS=ROOT/'.native/current-search-20261016/pools'
CACHE=ROOT/'.native/sentence-pretrain-20261017/data/pairs.jsonl.gz'
MIX={'HK':.65,'Tatoeba':.2,'authored':.15}


def check():
    p=json.loads((DATA/'protocol.json').read_text())
    if digest(DATA/'protocol.json')!=json.loads((DATA/'seal.json').read_text())['protocol_sha256']:
        raise ValueError('Head-change protocol changed')
    for name,value in {**p['source_sha256'],**p['input_sha256']}.items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen head-change source/input changed: '+name)
    if subprocess.check_output(['git','rev-parse','f7cd44c:app'],cwd=ROOT,text=True).strip()!=p['parent_app_tree']:
        raise ValueError('Parent app tree changed')
    return p


def prepare(output):
    if output.exists():raise ValueError('Preserve existing head-change data')
    old=json.loads((POOLS/'observation.json').read_text())
    for name,value in old['output_sha256'].items():
        if digest(POOLS/name)!=value:raise ValueError('Original TRAIN observations changed')
    if subprocess.check_output(['git','rev-parse','3aa8870:app'],cwd=ROOT)!=subprocess.check_output(['git','rev-parse','f7cd44c:app'],cwd=ROOT):
        raise ValueError('Cached TRAIN observations are from a different app')
    manifest=json.loads((ROOT/'tools/data/sentence_pretrain/manifest.json').read_text())
    if digest(CACHE)!=manifest['pairs_sha256']:raise ValueError('Family-disjoint pairs changed')
    allowed={}
    for row in map(json.loads,gzip.decompress(CACHE.read_bytes()).decode().splitlines()):
        key=(row['family'],row['context'],row['code'],row['positive'])
        value=(row['split'],'HK' if row['domain']=='UD' else row['domain'])
        if key in allowed and allowed[key]!=value:raise ValueError('Conflicting original-family split')
        allowed[key]=value
    pools=list(records(POOLS/'pools.tsv'))
    visible=[s.split('\t') for s in (POOLS/'visible.tsv').read_text().splitlines()]
    expected=[s.split('\t') for s in (ROOT/'tools/data/clean_ranking/train.tsv').read_text().splitlines()]
    if [r[:4] for r in visible]!=expected:raise ValueError('Incomplete TRAIN displays')
    lines=[];meta={};counts=Counter()
    for row,display in zip(pools,visible):
        assert [row[k] for k in ('source','context','code','gold')]==display[:4]
        fam=group(family(row['source']));key=(fam,row['context'],row['code'],row['gold'])
        if key not in allowed:counts['excluded_by_pretrain_admission']+=1;continue
        values=display[5].split('|') if display[5] else []
        if len(values)<2 or row['gold'] not in values:counts['unavailable_or_no_rival']+=1;continue
        if values!=row['values'][:len(values)]:raise ValueError('Cached visible order differs from full pool')
        split,domain=allowed[key];identity=str(len(meta))
        meta[identity]=dict(family=fam,split=split,domain=domain,head_correct=values[0]==row['gold'])
        lines.append('\t'.join((identity,row['context'],row['code'],row['gold'],'|'.join(values),
            '|'.join(row['adjusted'][v].hex() for v in values),'|'.join(row['support'][v].hex() for v in values))))
        counts[split+':'+domain]+=1
    train={m['family'] for m in meta.values() if m['split']=='train'}
    valid={m['family'] for m in meta.values() if m['split']=='validation'}
    if train&valid:raise ValueError('Original family leakage')
    output.mkdir(parents=True)
    for shard in range(4):
        (output/f'displays-{shard}.tsv').write_text(''.join(s+'\n' for s in lines[shard::4]))
    write(output/'metadata.json',meta)
    write(output/'manifest.json',dict(cases=len(meta),counts=dict(counts),families=dict(train=len(train),validation=len(valid)),
        input_sha256={str(p.relative_to(ROOT)):digest(p) for p in [POOLS/'pools.tsv',POOLS/'visible.tsv',POOLS/'observation.json',CACHE]},
        output_sha256={p.name:digest(p) for p in sorted(output.glob('*'))},
        scope='Original admitted TRAIN sources only. Split and exclusions are inherited from both stages of the fixed neural model; no sentence identities are model features.'))
    print(json.dumps(dict(cases=len(meta),counts=dict(counts),train_families=len(train),validation_families=len(valid))))


def row_weights(rows,meta):
    per_case=Counter(r[0] for r in rows);families=defaultdict(set);cases=defaultdict(set)
    for identity in per_case:
        m=meta[identity];families[m['domain']].add(m['family']);cases[m['family']].add(identity)
    w=np.asarray([MIX[meta[i]['domain']]/len(families[meta[i]['domain']])/len(cases[meta[i]['family']])/per_case[i] for i,*_ in rows])
    return w/w.sum()


def fit(cache,output):
    p=check()
    if output.exists():raise ValueError('Preserve fitted gate')
    manifest=json.loads((cache/'manifest.json').read_text())
    for name,value in manifest['output_sha256'].items():
        if digest(cache/name)!=value:raise ValueError('Prepared TRAIN cache changed')
    meta=json.loads((cache/'metadata.json').read_text());observed=[];seen=Counter();proposals={}
    for shard in range(4):
        for line in (cache/f'features-{shard}.tsv').read_text().splitlines():
            f=line.split('\t');identity=f[0]
            if len(f)!=5 or identity not in meta:raise ValueError('Invalid TRAIN feature row')
            h,c,proposed=map(int,f[1:4]);vector=np.asarray([float.fromhex(v) for v in f[4].split('|')])
            if vector.shape!=(20,) or not np.isfinite(vector).all() or h!=meta[identity]['head_correct']:
                raise ValueError('Invalid feature vector/label')
            seen[identity]+=1
            if proposed:
                if identity in proposals:raise ValueError('More than one head proposal')
                proposals[identity]=(vector,c)
            if h or c:observed.append((identity,vector,c))
    if set(seen)!=set(meta):raise ValueError('Incomplete TRAIN feature coverage')
    train=[r for r in observed if meta[r[0]]['split']=='train'];valid=[r for r in observed if meta[r[0]]['split']=='validation']
    x=np.stack([r[1] for r in train]);y=np.array([r[2] for r in train]);w=row_weights(train,meta)
    mean=w@x;scale=np.sqrt(w@((x-mean)**2));scale=np.maximum(scale,1e-6);mean[0]=0;scale[0]=1
    z=(x-mean)/scale;l2=p['fit']['l2']
    def objective(beta):
        logits=z@beta
        loss=w@(np.logaddexp(0,logits)-y*logits)+l2*(beta[1:]@beta[1:])/2
        grad=z.T@(w*(expit(logits)-y));grad[1:]+=l2*beta[1:]
        return loss,grad
    fitted=minimize(objective,np.zeros(20),jac=True,method='L-BFGS-B',options={'maxiter':400,'ftol':1e-12,'gtol':1e-9})
    if not fitted.success or not np.isfinite(fitted.x).all():raise ValueError('Head gate optimization failed')
    beta=fitted.x
    validation=[]
    for threshold in p['fit']['thresholds']:
        groups=defaultdict(lambda:dict(cases=0,before=0,after=0,gained=0,lost=0,swaps=0))
        for identity,m in meta.items():
            if m['split']!='validation':continue
            g=groups[m['domain']];old=int(m['head_correct']);new=old;swap=False
            if identity in proposals:
                vector,correct=proposals[identity]
                swap=bool(expit(((vector-mean)/scale)@beta)>=threshold)
                if swap:new=correct
            g['cases']+=1;g['before']+=old;g['after']+=new;g['gained']+=new>old;g['lost']+=new<old;g['swaps']+=swap
        eligible=all(g['after']>=g['before'] for g in groups.values()) and sum(g['after']-g['before'] for g in groups.values())>0
        key=sum((g['after']-g['before'])/g['cases'] for g in groups.values())/len(groups)
        validation.append(dict(threshold=threshold,per_domain=dict(groups),qualified=eligible,selection_key=key))
    eligible=[r for r in validation if r['qualified']]
    selected=max(eligible,key=lambda r:(r['selection_key'],-sum(g['lost'] for g in r['per_domain'].values()),r['threshold'])) if eligible else None
    output.mkdir(parents=True)
    if selected:
        blob=struct.pack('>IId',0x48434731,20,selected['threshold'])+b''.join(struct.pack('>20d',*v) for v in (mean,scale,beta))
        (output/'head_change.b64').write_bytes(base64.encodebytes(gzip.compress(blob,mtime=0)))
    xv=np.stack([r[1] for r in valid]);yv=np.array([r[2] for r in valid]);wv=row_weights(valid,meta);lv=((xv-mean)/scale)@beta
    report=dict(protocol_sha256=digest(DATA/'protocol.json'),cases=len(meta),labeled_pairs=dict(train=len(train),validation=len(valid)),
        train_labels=dict(repair=int(y.sum()),protection=int(len(y)-y.sum())),train_objective=float(fitted.fun),iterations=int(fitted.nit),
        validation_pair_nll=float(wv@(np.logaddexp(0,lv)-yv*lv)),thresholds=validation,selected=selected,
        qualified=selected is not None,mean=mean.tolist(),scale=scale.tolist(),weights=beta.tolist(),
        cache_sha256={str(f.relative_to(ROOT)):digest(f) for f in sorted(cache.glob('*')) if f.is_file()},
        model_sha256=digest(output/'head_change.b64') if selected else None,
        scope='One fixed regularized logistic fit. Threshold selected only on original-family-disjoint internal validation, never external guards or reserve. Balanced per-case/family/source mass; no lexical identity features.')
    write(output/'report.json',report)
    print(json.dumps({k:report[k] for k in ('cases','labeled_pairs','train_labels','train_objective','validation_pair_nll','selected','qualified')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('output',type=Path)
    a=s.add_parser('fit');a.add_argument('cache',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.output)
    else:fit(a.cache,a.output)
