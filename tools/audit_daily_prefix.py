#!/usr/bin/env python3
"""Check frozen dictionary targets against known baseline training, before decoding."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from prepare_daily_prefix_data import DATA
from prepare_tatoeba_corpus import load_training,digest
from train_language_model import corpus,chunks
from train_phrase_model import ROOT,ASSETS

def audit(source,output=DATA/'exposure-audit.json'):
    targets={line.split('\t')[-1] for split in ('validation','heldout') for line in (DATA/(split+'.tsv')).read_text().splitlines()}
    lengths=sorted({len(t) for t in targets});seen=defaultdict(set)
    def observe(text,source):
        for part in chunks(text):
            for n in lengths:
                for i in range(len(part)-n+1):
                    value=part[i:i+n]
                    if value in targets:seen[value].add(source)
    report=json.loads((ASSETS/'MODEL_REPORT.json').read_text())
    if digest(source)!=report['source_sha256']['hkcancor_zip']:raise ValueError('Pinned baseline corpus required')
    excluded=set(report['validation_conversation_files'])|set(report['heldout_conversation_files'])
    for name,text in corpus(source):
        if name not in excluded:observe(text,'HKCanCor training')
    rows,_=load_training(ROOT/'tools/data/tatoeba_corpus')
    for row in rows:observe(row['text'],'Tatoeba training')
    for name in ('quick_phrases.tsv','hk_phrases.tsv','cantonese_phrases.tsv','hk_chat_phrases.tsv'):
        for line in (ASSETS/name).read_text().splitlines():
            fields=line.split('\t')
            if len(fields)==3:observe(fields[1],'Baseline vocabulary:'+name)
    result={'known_training_or_vocabulary_overlap':{k:sorted(v) for k,v in sorted(seen.items())},
        'overlap_count':len(seen),'target_count':len(targets),'performed_before_heldout_decoding':True,
        'scope':'Raw HKCanCor training chunks, licensed Tatoeba training chunks and current baseline vocabulary. No outcome-based exclusions. Dictionary examples may contain previously known short words.'}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('corpus',type=Path);p.add_argument('--output',type=Path,default=DATA/'exposure-audit.json')
    a=p.parse_args();audit(a.corpus,a.output)
