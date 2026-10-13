#!/usr/bin/env python3
"""Fit frozen same-code prefix errors; evaluation-only dictionary examples are forbidden."""
import argparse
import json
import math
from pathlib import Path
from prefix_features import features,metadata,encode
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import learn,matches
from train_phrase_model import ROOT,reverse_codes

DATA=ROOT/'tools/data/daily_prefix'

def read_pairs(path):
    manifest=json.loads((DATA/'manifest.json').read_text())
    if digest(DATA/'train.tsv')!=manifest['file_sha256']['train.tsv']:raise ValueError('Frozen training checksum changed')
    allowed={tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()}
    reverse=reverse_codes();pairs=[];seen=set()
    for number,line in enumerate(path.read_text().splitlines(),1):
        row=line.split('\t')
        if len(row)!=10:raise ValueError(f'Invalid prefix row {number}')
        source,context,code,gold,position,positive,negative,margin,hints,rank=row
        if (source,context,code,gold) not in allowed:raise ValueError('Non-training target')
        at=int(position);offset=float.fromhex(margin)
        if not 0<at<len(code) or not gold.startswith(positive) or positive==negative or int(rank)<2:raise ValueError('Invalid checkpoint')
        if not math.isfinite(offset) or abs(offset)>1000:raise ValueError('Invalid score margin')
        if not matches(code[:at],positive,reverse) or not matches(code[:at],negative,reverse) or not matches(code[at:],gold[len(positive):],reverse):raise ValueError('Inexact prefix pair')
        hint_list=hints.split('|') if hints else []
        if len(hint_list)>6:raise ValueError('Unbounded hints')
        if any(not any(matches(code[at:at+n],h,reverse) for n in range(2,min(16,len(code)-at)+1)) for h in hint_list):raise ValueError('Inexact lookahead hint')
        # Independent corpus utterances and authored template families, not rival count.
        identity=(source,context,code,gold,at,positive,negative)
        if identity in seen:continue
        seen.add(identity)
        family=source.rsplit(':',1)[0] if source.startswith('train:hk:') else source
        pairs.append((family,metadata(context,hint_list),code[:at],positive,negative,offset))
    if not pairs:raise ValueError('No actual at-risk prefix pairs')
    return pairs

def train(path,output):
    pairs=read_pairs(path);p=json.loads((DATA/'protocol.json').read_text())['parameters']
    def extractor(context,text):
        m=json.loads(context);return features(m['context'],text,m['hints'])
    weights,metrics=learn(pairs,epochs=p['epochs'],rate=p['rate'],l2=p['l2'],
        min_count=p['minimum_independent_support'],maximum_features=p['maximum_features'],feature_extractor=extractor)
    metrics['feature_support_unit']='Distinct corpus conversation, Tatoeba translation-family or project-authored template; rival/checkpoint/slot variants never multiply independent support.'
    output.mkdir(parents=True,exist_ok=True)
    (output/'weights.json').write_text(json.dumps(weights,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'prefix_ranker.b64').write_bytes(encode(weights))
    report={'pairs_sha256':digest(path),'training_sha256':digest(DATA/'train.tsv'),
        'protocol_sha256':digest(DATA/'protocol.json'),'pairs':len(pairs),'families':len({p[0] for p in pairs}),
        'model_bytes':(output/'prefix_ranker.b64').stat().st_size,'training':metrics,
        'purpose':'Search survival only; actual baseline pruning margins; no words.hk dictionary examples in training; no full-sentence features.'}
    (output/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))
    return weights

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pairs',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();train(a.pairs,a.output)
