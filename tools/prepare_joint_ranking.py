#!/usr/bin/env python3
"""Extend licensed training conversations; keep dictionary examples evaluation-only."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
from prepare_daily_prefix_data import MARKERS,hashed
from prepare_phrase_relations import hkcancor,gram_index,overlap
from prepare_search_recovery import prepare as reserve
from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_phrase_model import ROOT,reverse_codes

BASELINE='b5b084fa043724f38913a8042b47ffcd551330e8'
DATA=ROOT/'tools/data/joint_ranking'
PREVIOUS=tuple('tools/data/'+name+'/'+split+'-source.jsonl'
    for name in ('search_recovery','prefix_retrieval') for split in ('validation','heldout'))

def prepare(dictionary,hk,treebank,output=DATA):
    reserve(dictionary,hk,treebank,output,baseline=BASELINE,additional_sources=PREVIOUS,label='joint')
    manifest=json.loads((output/'manifest.json').read_text())
    old=[tuple(s.split('\t')) for s in (ROOT/'tools/data/phrase_relations/train.tsv').read_text().splitlines()]
    evaluation=set()
    for name in manifest['known_input_sha256']:
        if not name.endswith('.tsv'):continue
        for line in (ROOT/name).read_text().splitlines():
            fields=line.split('\t')
            if fields[0].startswith('train:') or line.startswith('#'):continue
            evaluation.update(s for s in fields if len(s)>=6 and all(han(c) for c in s))
    evaluation.update(s.split('\t')[3] for split in ('validation','heldout')
                      for s in (output/(split+'.tsv')).read_text().splitlines())
    excluded=gram_index(evaluation);reverse=reverse_codes();seen={r[3] for r in old};rejected=Counter()
    report=json.loads((ROOT/'app/src/main/assets/PHRASE_MODEL_REPORT.json').read_text())
    allowed=set(report['training_conversation_files']);hk_rows={};tatoeba_rows={}
    def accept(text):
        if text in seen:rejected['already_selected']+=1;return False
        if not 6<=len(text)<=24 or not MARKERS.intersection(text) or not all(c in reverse for c in text):
            rejected['length_marker_or_code']+=1;return False
        if overlap(text,excluded):rejected['evaluation_overlap']+=1;return False
        return True
    def code(text):return ''.join(sorted(reverse[c],key=lambda s:(-len(s),s))[0] for c in text)
    for name,index,words in hkcancor(hk):
        if name not in allowed:continue
        text=''.join(w for w,_ in words)
        if accept(text):hk_rows.setdefault(text,('train:hk:'+name+':'+hashed(text)[:16],'',code(text),text))
    for line in (ROOT/'tools/data/tatoeba_corpus/train.jsonl').read_text().splitlines():
        row=json.loads(line);text=row['text']
        if accept(text):tatoeba_rows.setdefault(text,('train:tatoeba:'+str(row['group']),'',code(text),text))
    additional=[]
    for rows,limit in ((hk_rows,4000),(tatoeba_rows,600)):
        for row in sorted(rows.values(),key=lambda r:hashed('joint-ranking-training-v1:'+r[0]+r[3])):
            if row[3] in seen:continue
            additional.append(row);seen.add(row[3]);limit-=1
            if limit==0:break
    if sum(r[0].startswith('train:hk:') for r in additional)<2500:raise ValueError('Insufficient unused licensed natural training text')
    for name,rows in (('train',old+additional),('additional-training',additional)):
        (output/(name+'.tsv')).write_text(''.join('\t'.join(r)+'\n' for r in rows))
    manifest.update(training_cases=len(old)+len(additional),reused_training_cases=len(old),
        additional_hk=sum(r[0].startswith('train:hk:') for r in additional),
        additional_tatoeba=sum(r[0].startswith('train:tatoeba:') for r in additional),
        training_rejected=dict(rejected),eligible_unused_hk=len(hk_rows),eligible_unused_tatoeba=len(tatoeba_rows),
        source_split='Original46 HKCanCor training conversations and Tatoeba train groups only. Excluded conversations, translations and all known evaluation target substrings6+ are forbidden in additions.',
        training_license='HKCanCor CC BY4.0; Tatoeba CC BY2.0 France; retained UD derivative CC BY-SA4.0 and project-authored rows. Full original notices retained.',
        training_limit='New ranking supervision from already licensed baseline training text; not new recordings, contemporary chat frequency, or additional independent speakers. Rival and checkpoint multiplicity never multiply family support.')
    manifest['file_sha256'].update({name:digest(output/name) for name in ('train.tsv','additional-training.tsv')})
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('training_cases','additional_hk','additional_tatoeba','validation_cases','heldout_cases')}))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dictionary','hk','treebank'):p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,default=DATA);a=p.parse_args();prepare(a.dictionary,a.hk,a.treebank,a.output)
