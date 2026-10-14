#!/usr/bin/env python3
"""Train a bounded residual from current final-pool errors, for calibration only.

Uses the pinned licensed/authored daily-prefix training rows, not evaluation
examples. Runtime features are the existing bounded sentence features. No model
is installed by this tool; known calibration results cannot establish generality.
"""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
from diagnose_sentence_priority import observe
from prepare_tatoeba_corpus import digest
from sentence_features import features
from train_candidate_ranker import learn,matches
from train_phrase_model import ROOT,reverse_codes
from train_sentence_ranker import stored_weights

DATA=ROOT/'tools/data/daily_prefix'
PROTOCOL=ROOT/'tools/data/final_hard_negative/protocol.json'

def check_protocol():
    protocol=json.loads(PROTOCOL.read_text())
    if digest(ROOT/'tools/sentence_features.py')!=protocol['feature_extractor_sha256']:
        raise ValueError('Frozen feature extraction changed')
    if protocol.get('trainer_sha256') and digest(ROOT/'tools/train_candidate_ranker.py')!=protocol['trainer_sha256']:
        raise ValueError('Frozen trainer changed')
    for name,checksum in protocol['model_sha256'].items():
        if digest(ROOT/'app/src/main/assets'/name)!=checksum:raise ValueError('Baseline model changed')
    return protocol

def records(path):
    for line in path.read_text().splitlines():
        f=line.split('\t')
        if len(f)!=10:raise ValueError('Incomplete final-pool observer')
        source,context,code,gold,original=f[:5]
        values=f[6].split('|') if f[6] else []
        raw=[float.fromhex(v) for v in f[7].split('|')] if values else []
        adjusted=[float.fromhex(v) for v in f[8].split('|')] if values else []
        support=[float.fromhex(v) for v in f[9].split('|')] if values else []
        if len(set(values))!=len(values) or any(len(v)!=len(values) for v in (raw,adjusted,support)):
            raise ValueError('Invalid observed pool')
        if int(f[5])!=(values.index(gold)+1 if gold in values else 0):raise ValueError('Rank mismatch')
        if original and original not in values:raise ValueError('Missing original reference')
        if any(not math.isfinite(v) for vs in (raw,adjusted,support) for v in vs):raise ValueError('Nonfinite observed score')
        yield dict(source=source,context=context,code=code,gold=gold,original=original,values=values,
            raw=dict(zip(values,raw)),adjusted=dict(zip(values,adjusted)),support=dict(zip(values,support)))

def train(scored,output):
    protocol=check_protocol();manifest=json.loads((DATA/'manifest.json').read_text())
    if digest(DATA/'train.tsv')!=manifest['file_sha256']['train.tsv'] or digest(DATA/'train.tsv')!=protocol['training_sha256']:
        raise ValueError('Frozen licensed/authored training rows changed')
    cases=[tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()]
    observed=list(records(scored))
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in observed]!=cases:
        raise ValueError('Non-training or partial observer input')
    reverse=reverse_codes();pairs=[];counts=Counter();targets=set();cache={}
    for r in observed:
        counts['observed_targets']+=1;gold=r['gold'];values=r['values']
        if gold not in values:counts['gold_missing_from_pool']+=1;continue
        rank=values.index(gold)+1;counts['gold_rank1' if rank==1 else 'gold_nonleading']+=1
        rivals=sorted((v for v in values if v!=gold),key=lambda v:-r['adjusted'][v])
        # Mine actual score errors, while preserving close correct-head examples.
        cutoff=3 if rank==1 else 0
        rivals=[v for v in rivals if r['adjusted'][gold]-r['adjusted'][v]<=cutoff]
        rivals=rivals[:1 if rank==1 else protocol['maximum_rivals_per_target']]
        if not rivals:counts['no_close_score_rival']+=1;continue
        if not matches(r['code'],gold,reverse):raise ValueError('Inexact training gold')
        family=r['source'].rsplit(':',1)[0] if r['source'].startswith('train:hk:') else r['source']
        for rival in rivals:
            if not matches(r['code'],rival,reverse):raise ValueError('Inexact training rival')
            margin=r['adjusted'][gold]-r['adjusted'][rival]
            pairs.append((family,r['context'],r['code'],gold,rival,margin));targets.add((r['source'],gold))
            counts['correct_head_pairs' if rank==1 else 'error_pairs']+=1
    def extractor(context,text):
        key=context,text
        if key not in cache:cache[key]=features(context,text,3)
        return cache[key]
    p=protocol['parameters']
    weights,metrics=learn(pairs,epochs=p['epochs'],rate=p['rate'],l2=p['l2'],min_count=p['minimum_independent_support'],
        maximum_features=p['maximum_features'],feature_extractor=extractor,source_mix=protocol.get('source_mix'))
    weights=stored_weights(weights)
    output.mkdir(parents=True,exist_ok=True)
    (output/'weights.json').write_text(json.dumps(weights,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'pairs.tsv').write_text(''.join('\t'.join((*p[:5],float(p[5]).hex()))+'\n' for p in pairs))
    report=dict(protocol_sha256=digest(PROTOCOL),training_observer_sha256=digest(scored),
        weights_sha256=digest(output/'weights.json'),pairs_sha256=digest(output/'pairs.tsv'),
        counts=dict(counts),pairs=len(pairs),targets=len(targets),families=len({p[0] for p in pairs}),training=metrics,
        production_change=False,limits='Objective fits unclipped comparative evidence; bounded runtime correction is separately calibrated. Existing source family grouping and all fixed model offsets are retained. No words.hk evaluation examples train it.')
    (output/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True)

def validate(scored,model,output):
    protocol=check_protocol();training=json.loads((model/'training-report.json').read_text())
    if training['protocol_sha256']!=digest(PROTOCOL) or training['weights_sha256']!=digest(model/'weights.json'):
        raise ValueError('Frozen training result changed')
    weights=json.loads((model/'weights.json').read_text());groups=defaultdict(list)
    for r in records(scored):groups[r['source'].split(':',1)[-1]].append(r)
    if set(groups)!={'written200','authored60','natural200','public200'} or sorted(map(len,groups.values()))!=[60,200,200,200]:
        raise ValueError('Expected the four known calibration sets')
    def metrics(ranks):return dict(cases=len(ranks),top1=sum(r==1 for r in ranks),top5=sum(0<r<=5 for r in ranks),
        top20=sum(0<r<=20 for r in ranks),mrr=sum(1/r for r in ranks if 0<r<=20)/len(ranks))
    baseline={n:metrics([r['values'].index(r['gold'])+1 if r['gold'] in r['values'] else 0 for r in rows]) for n,rows in groups.items()}
    cache={};trials={};changes={}
    def evidence(context,text):
        key=context,text
        if key not in cache:cache[key]=sum(v*weights.get(k,0) for k,v in features(context,text,3).items())
        return cache[key]
    for strength in protocol['strength_grid']:
        trial={};movement=[]
        for name,rows in groups.items():
            ranks=[]
            for r in rows:
                original=r['original'];ref=evidence(r['context'],original) if original else 0
                scores={v:r['adjusted'][v]+max(0,strength*max(-1.5,min(1.5,evidence(r['context'],v)-ref))-.1) for v in r['values']}
                pin=bool(original and r['support'][original]>0)
                order=sorted(r['values'],key=lambda v:(0 if pin and v==original else 1,-scores[v]))
                rank=order.index(r['gold'])+1 if r['gold'] in order else 0
                ranks.append(rank)
                before=r['values'].index(r['gold'])+1 if r['gold'] in r['values'] else 0
                if rank!=before:movement.append(dict(source=r['source'],code=r['code'],gold=r['gold'],before=before,after=rank))
            trial[name]=metrics(ranks)
        trials[str(strength)]=trial;changes[str(strength)]=movement
        print(f'calibrated-strength={strength}',flush=True)
    eligible=[s for s,t in trials.items() if all(t[n][m]>=baseline[n][m] for n in baseline for m in ('top1','top5','top20'))]
    selected=max(eligible,key=lambda s:(sum(t['mrr'] for t in trials[s].values()),-float(s))) if eligible else None
    if selected and sum(t['mrr'] for t in trials[selected].values())<=sum(t['mrr'] for t in baseline.values()):selected=None
    report=dict(calibration_only=True,baseline=baseline,trials=trials,eligible=eligible,selected_for_further_testing=selected,
        weights_sha256=digest(model/'weights.json'),protocol_sha256=digest(PROTOCOL),scored_sha256=digest(scored),
        case_changes_by_strength=changes,
        production_change=False,limits='Known calibration pools only, simulated score change. Any candidate needs native parity, existing regression and latency checks plus a newly frozen unopened family reserve before adoption.')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='case_changes_by_strength'},ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('observe','train','validate'))
    parser.add_argument('scored',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--model',type=Path)
    parser.add_argument('--protocol',type=Path,default=PROTOCOL)
    a=parser.parse_args();PROTOCOL=a.protocol
    if a.mode=='observe':
        if a.scored.resolve()!=(DATA/'train.tsv').resolve():parser.error('Only the frozen licensed/authored training list may be observed here')
        observe(a.scored,a.output,json.loads(PROTOCOL.read_text())['baseline_revision'])
    elif a.mode=='train':train(a.scored,a.output)
    elif a.model:validate(a.scored,a.model,a.output)
    else:parser.error('--model is required to validate')
