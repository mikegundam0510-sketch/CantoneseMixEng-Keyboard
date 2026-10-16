#!/usr/bin/env python3
"""Train one fixed small whole-candidate model on licensed TRAIN pairs only."""
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np

from context_gru import initialize,encode,padded,forward,loss_gradient,save,NAMES,tail
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes

DATA=ROOT/'tools/data/context_neural'
PAIRS=ROOT/'tools/data/clean_ranking/model015/pairs.tsv'


def category(family):
    return 'HK' if family.startswith('train:hk:') else 'Tatoeba' if family.startswith('train:tatoeba:') else 'UD' if family.startswith('train:ud:') else 'authored'


def prepare(output=DATA):
    if output.exists():raise ValueError('Use a fresh neural TRAIN folder')
    allowed={tuple(s.split('\t')[1:]) for s in (ROOT/'tools/data/clean_ranking/train.tsv').read_text().splitlines()}
    reverse=reverse_codes();rows=[]
    for line in PAIRS.read_text().splitlines():
        stage,family,context,code,positive,negative,offset=line.split('\t')
        if stage!='final':continue
        if (context,code,positive) not in allowed or not matches(code,positive,reverse) or not matches(code,negative,reverse):
            raise ValueError('Non-TRAIN or inexact final comparison')
        margin=float.fromhex(offset)
        if not math.isfinite(margin):raise ValueError('Nonfinite TRAIN offset')
        split='validation' if int(hashlib.sha256(('context-gru-internal-v1:'+family).encode()).hexdigest()[:8],16)%10==0 else 'train'
        rows.append(dict(family=family,domain=category(family),context=context,code=code,positive=positive,negative=negative,
            offset=max(-4,min(4,margin)),split=split))
    if len(rows)<10000:raise ValueError('Insufficient final TRAIN supervision')
    output.mkdir(parents=True)
    (output/'pairs.jsonl.gz').write_bytes(gzip.compress(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode(),mtime=0))
    counts=Counter(r['split'] for r in rows);domains=Counter(r['domain'] for r in rows)
    manifest=dict(pair_source=str(PAIRS.relative_to(ROOT)),pair_source_sha256=digest(PAIRS),
        licensed_training_sha256=digest(ROOT/'tools/data/clean_ranking/train.tsv'),pairs_sha256=digest(output/'pairs.jsonl.gz'),
        pairs=len(rows),splits=dict(counts),domains=dict(domains),
        scope='Only original clean TRAIN final comparisons. Family-disjoint internal neural validation by SHA256; no evaluation corpus or dictionary usage examples fit the model. Internal validation is not keyboard accuracy.',
        offsets='Frozen historical baseline margins clipped to[-4,4]; near the current parent model but not recomputed. This approximation is reported; actual current Java inference determines adoption.',
        license='Retain clean_ranking and original HKCanCor CC BY4/Tatoeba CC BY2FR/UD CC BY-SA4/project credits. NCDOL examples remain evaluation-only.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest))


def weights(rows):
    # Equal comparison mass per positive case, then per family within a domain.
    rivals=Counter((r['family'],r['context'],r['code'],r['positive']) for r in rows)
    cases=defaultdict(set)
    for r in rows:cases[r['family']].add((r['context'],r['code'],r['positive']))
    families=defaultdict(set)
    for r in rows:families[r['domain']].add(r['family'])
    mix={'HK':.65,'Tatoeba':.2,'UD':.05,'authored':.1}
    value=np.array([mix[r['domain']]/len(families[r['domain']])/len(cases[r['family']])/rivals[r['family'],r['context'],r['code'],r['positive']] for r in rows],dtype=np.float32)
    return value/value.mean()


def fit(data,output):
    if output.exists():raise ValueError('Preserve prior neural fit')
    p=json.loads((data/'protocol.json').read_text());m=json.loads((data/'manifest.json').read_text())
    if digest(data/'manifest.json')!=p['manifest_sha256'] or digest(data/'pairs.jsonl.gz')!=m['pairs_sha256']:raise ValueError('TRAIN source changed')
    for n,h in p['source_sha256'].items():
        if digest(ROOT/n)!=h:raise ValueError('Frozen neural source changed: '+n)
    rows=[json.loads(s) for s in gzip.decompress((data/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
    train=[r for r in rows if r['split']=='train'];validation=[r for r in rows if r['split']=='validation']
    counts=Counter();support=defaultdict(set)
    for r in train:
        for c in tail(r['context'])+r['positive']:counts[c]+=1;support[c].add(r['family'])
    chars=sorted(sorted((c for c in counts if counts[c]>=3 and len(support[c])>=2),key=lambda c:(-counts[c],ord(c)))[:4096])
    vocabulary={c:i+3 for i,c in enumerate(chars)}
    seqs=[encode(r['context'],r[key],vocabulary) for r in rows for key in ('positive','negative')]
    encoded=padded(seqs).reshape(len(rows),2,-1)
    n=len(train);order_train=np.array([i for i,r in enumerate(rows) if r['split']=='train']);order_val=np.array([i for i,r in enumerate(rows) if r['split']=='validation'])
    wt,wv=weights(train),weights(validation);offsets=np.array([r['offset'] for r in rows],dtype=np.float32)
    values=initialize(len(chars)+3)
    moment={k:np.zeros_like(v) for k,v in values.items()};variance={k:np.zeros_like(v) for k,v in values.items()}
    rng=np.random.default_rng(20261016);best=float('inf');best_values=None;history=[];step=0
    def validation_loss():
        losses=[]
        for at in range(0,len(order_val),256):
            ix=order_val[at:at+256];batch=encoded[ix]
            pos=forward(values,batch[:,0]);neg=forward(values,batch[:,1]);gap=offsets[ix]+pos-neg
            losses.append(float(np.sum(wv[at:at+len(ix)]*np.logaddexp(0,-gap))))
        return sum(losses)/len(order_val)
    output.mkdir(parents=True);initial=validation_loss()
    for epoch in range(40):
        permutation=rng.permutation(n);epoch_loss=0
        for at in range(0,n,128):
            local=permutation[at:at+128];ix=order_train[local];batch=encoded[ix]
            loss,grad=loss_gradient(values,batch[:,0],batch[:,1],offsets[ix],wt[local],l2=.0001)
            norm=np.sqrt(sum(float(np.sum(g*g)) for g in grad.values()));scale=min(1,5/max(norm,1e-12));step+=1
            for k in NAMES:
                g=grad[k]*scale;moment[k]=.9*moment[k]+.1*g;variance[k]=.999*variance[k]+.001*g*g
                values[k]-=.003*(moment[k]/(1-.9**step))/(np.sqrt(variance[k]/(1-.999**step))+1e-8)
            values['embedding'][0]=0;epoch_loss+=loss*len(ix)
        valid=validation_loss();entry=dict(epoch=epoch+1,training_objective=epoch_loss/n,internal_validation_loss=valid);history.append(entry)
        if not math.isfinite(valid) or not all(np.isfinite(v).all() for v in values.values()):raise ValueError('Nonfinite recurrent training')
        if valid<best:best=valid;best_values={k:v.copy() for k,v in values.items()};best_epoch=epoch+1
        print(json.dumps(entry),flush=True)
    for strength in (.5,1):save(output/('context-gru-'+str(strength)+'.b64'),best_values,chars,strength)
    report=dict(protocol_sha256=digest(data/'protocol.json'),manifest_sha256=digest(data/'manifest.json'),numpy=np.__version__,
        vocabulary=len(chars)+3,embedding_dimension=16,hidden=16,cap=2,context=12,maximum_candidate=48,
        initial_internal_validation_loss=initial,best_internal_validation_loss=best,best_epoch=best_epoch,
        epochs=history,models={n.name:digest(n) for n in output.glob('*.b64')},
        note='One seeded fixed-capacity model; checkpoint selected only on family-disjoint TRAIN internal validation, not keyboard evaluation. Two predeclared residual strengths. No full sentence lookup, private text, online calls or dictionary example fitting.')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('--output',type=Path,default=DATA)
    a=s.add_parser('fit');a.add_argument('data',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.output)
    else:fit(a.data,a.output)
