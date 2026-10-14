#!/usr/bin/env python3
"""Freeze licensed natural HK examples, train-only POS lexicon and unseen guards.

The UD corpus gets a custom source-disjoint partition, not its official benchmark
split. words.hk examples stay evaluation-only. No decoder outcomes select data.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata
import zipfile
from prepare_daily_prefix_data import prepare as dictionary_pool
from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_phrase_model import ROOT,ASSETS,reverse_codes

DATA=ROOT/'tools/data/phrase_relations'
BASELINE='21ede200e95cde63e18632ad5ac8b33629ea51fe'
UD_REVISION='68c3151c1181a7b67ef5c917570635bcccf7e4bf'

def hashed(text):return hashlib.sha256(text.encode()).hexdigest()

def hkcancor(source):
    with zipfile.ZipFile(source) as z:
        for name in sorted(z.namelist()):
            if not name.startswith('utf8/') or name.endswith('/'):continue
            words=[];index=0
            for line in z.read(name).decode('utf-8-sig').splitlines():
                m=re.fullmatch(r'\s*([^/<>\s]+)/([^/]+)/[^/]*/\s*',line)
                if m and all(han(c) for c in m[1]):words.append((unicodedata.normalize('NFC',m[1]),m[2]))
                elif m or '</sent_tag>' in line or '<sent>' in line:
                    if words:yield name,index,words;index+=1
                    words=[]
            if words:yield name,index,words

def ud(source):
    ident=None;words=[];chunk=0
    for line in source.read_text().splitlines()+['']:
        if line.startswith('# sent_id = '):ident=int(line.split('=')[1].strip());chunk=0
        elif line and not line.startswith('#'):
            f=line.split('\t')
            if len(f)!=10 or not f[0].isdigit():continue
            if all(han(c) for c in f[1]):
                role='Q' if 'NounType=Clf' in f[5] else {'PRON':'P','NOUN':'N','PROPN':'N','VERB':'V','AUX':'V',
                    'NUM':'M','ADJ':'A','ADV':'D','ADP':'R','DET':'D','PART':'F','CCONJ':'C','SCONJ':'C'}.get(f[3],'O')
                words.append((unicodedata.normalize('NFC',f[1]),role))
            elif words:yield ident,chunk,words;chunk+=1;words=[]
        elif not line and words:yield ident,chunk,words;chunk+=1;words=[]

def hk_role(tag):
    return {'n':'N','v':'V','r':'P','q':'Q','m':'M','a':'A','d':'D','p':'R','c':'C','u':'F','y':'T','f':'N'}.get(tag[:1],'O')

def prior_sets():
    tracked=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE],cwd=ROOT,text=True).splitlines())
    evaluation=set();trained=set();hashes={}
    for relative in sorted(p for p in tracked if p.endswith('.tsv') and p.startswith('tools/')):
        path=ROOT/relative;hashes[relative]=digest(path)
        training='train' in path.name or path.name=='pairs.tsv'
        for line in path.read_text().splitlines():
            if line.startswith('#'):continue
            for text in line.split('\t'):
                if len(text)>=6 and all(han(c) for c in text):(trained if training else evaluation).add(text)
    return evaluation,trained,hashes

def gram_index(texts):
    index=defaultdict(set)
    for text in texts:
        for i in range(len(text)-5):index[text[i:i+6]].add(text)
    return index

def overlap(text,index):
    return any(p in text or text in p for i in range(len(text)-5) for p in index.get(text[i:i+6],()))

def prepare(hk_source,ud_dir,dictionary_source,output=DATA):
    phrase=json.loads((ASSETS/'PHRASE_MODEL_REPORT.json').read_text())
    if digest(hk_source)!=phrase['source_sha256']['hkcancor_zip']:raise ValueError('Pinned HKCanCor required')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ud_dir,text=True).strip()
    if revision!=UD_REVISION:raise ValueError('Pinned UD treebank required')
    ud_file=ud_dir/'yue_hk-ud-test.conllu';reverse=reverse_codes();prior,existing,input_hashes=prior_sets();prior_index=gram_index(prior)
    allowed=set(phrase['training_conversation_files']);excluded=set(phrase['excluded_conversation_files'])
    lexical=defaultdict(Counter);new_hk={};new_ud={};ud_validation={};ud_reserve={};rejected=Counter()
    frequencies={f[0]:int(f[1]) for s in (ASSETS/'character_frequencies.tsv').read_text().splitlines()
                 if len(f:=s.split('\t'))==2 and f[1].isdigit()}
    markers=set('我你佢哋唔冇未嘅咗喺嗰呢咁嚟咩啲嘢睇攞俾畀瞓喎㗎噉搵啱')
    def eligible(text):
        return (6<=len(text)<=24 and all(c in reverse for c in text) and markers.intersection(text)
            and sum(frequencies.get(c,0)<500 and c not in markers for c in text)<=max(1,len(text)//8))
    def code(text):return ''.join(sorted(reverse[c],key=lambda s:(-len(s),s))[0] for c in text)
    raw_training=set()
    for name,index,words in hkcancor(hk_source):
        text=''.join(w for w,_ in words)
        if name not in allowed:continue
        raw_training.add(text)
        for word,tag in words:
            if 1<=len(word)<=4:lexical[word][hk_role(tag)]+=1
        if not eligible(text) or overlap(text,prior_index):rejected['hk_ineligible_or_prior_evaluation']+=1;continue
        if text in existing:rejected['hk_already_selected_training']+=1;continue
        new_hk.setdefault(text,('train:hk:'+name+':'+hashed(text)[:16],'',code(text),text))
    ud_sources={}
    for ident,index,words in ud(ud_file):
        origin='missing-days' if ident<=410 else 'temple-interview' if ident<=547 else 'what-day' if ident<=650 else 'legco-2016'
        text=''.join(w for w,_ in words);ud_sources[f'{ident}:{index}']=origin
        if ident<=547:
            raw_training.add(text)
            for word,role in words:
                if 1<=len(word)<=4:lexical[word][role]+=1
        if not eligible(text) or overlap(text,prior_index):rejected['ud_ineligible_or_prior_evaluation']+=1;continue
        if ident<=547 and text not in existing:
            new_ud.setdefault(text,('train:ud:'+origin+':'+str(ident)+'-'+str(index),'',code(text),text))
        elif ident>547:
            record=(origin,str(ident)+':'+str(index),'',code(text),text)
            (ud_validation if ident<=650 else ud_reserve).setdefault(text,record)
    # Preserve every attributed old row; new examples never duplicate its target.
    old=[tuple(s.split('\t')) for s in (ROOT/'tools/data/daily_prefix/train.tsv').read_text().splitlines()]
    hk=sorted(new_hk.values(),key=lambda r:hashed('phrase-hk-v1:'+r[0]))[:2000]
    added_ud=sorted(new_ud.values(),key=lambda r:hashed('phrase-ud-v1:'+r[0]))[:300]
    old_texts={r[3] for r in old};added=[r for r in hk+added_ud if r[3] not in old_texts]
    # Duplicated targets across the new productions/conversations count once.
    training=list(old);seen=set(old_texts)
    for row in added:
        if row[3] not in seen:training.append(row);seen.add(row[3])
    # Raw text exposure includes baseline HKCanCor and licensed Tatoeba, beyond selected pairs.
    for line in (ROOT/'tools/data/tatoeba_corpus/train.jsonl').read_text().splitlines():
        raw_training.add(json.loads(line)['text'])
    train_index=gram_index(raw_training|seen)
    def fresh_ud(pool,prefix):
        selected={}
        for r in sorted(pool.values(),key=lambda r:hashed(prefix+':'+r[0]+r[1])):
            if not overlap(r[4],train_index) and not overlap(r[4],prior_index):
                selected.setdefault(r[1].split(':')[0],r)
        return list(selected.values())
    valid_ud=fresh_ud(ud_validation,'phrase-ud-validation-v1');held_ud=fresh_ud(ud_reserve,'phrase-ud-heldout-v1')
    # Extend the old fixed dictionary family hash sample; first800 remain old data.
    with tempfile.TemporaryDirectory(prefix='phrase-dictionary-pool-') as directory:
        directory=Path(directory);dictionary_pool(dictionary_source,directory,heldout_count=2000)
        pool=[json.loads(s) for s in (directory/'heldout-source.jsonl').read_text().splitlines()][800:]
    old_families={json.loads(s)['group'] for n in ('validation','heldout')
                  for s in (ROOT/'tools/data/daily_prefix'/(n+'-source.jsonl')).read_text().splitlines()}
    candidates=[r for r in pool if r['group'] not in old_families and not overlap(r['text'],prior_index)
                and not overlap(r['text'],train_index)]
    dictionary_validation=candidates[:100]
    validation_index=gram_index({r['text'] for r in dictionary_validation}|{r[4] for r in valid_ud})
    dictionary_reserve=[r for r in candidates[100:] if not overlap(r['text'],validation_index)][:500]
    test_index=gram_index({r['text'] for r in dictionary_reserve})
    held_ud=[r for r in held_ud if not overlap(r[4],validation_index) and not overlap(r[4],test_index)]
    if len(hk)<1000 or len(dictionary_reserve)!=500 or len(valid_ud)<10 or len(held_ud)<40:
        raise ValueError(f'Insufficient pre-decoding pools: hk{len(hk)},dict{len(dictionary_reserve)},ud{len(valid_ud)}/{len(held_ud)}')
    output.mkdir(parents=True,exist_ok=True)
    def write(name,rows):
        (output/(name+'.tsv')).write_text(''.join('\t'.join(r)+'\n' for r in rows))
    write('train',training)
    write('new-training',[r for r in training if r not in old])
    write('validation',[('validation:fresh-written100','',code(r['text']),r['text']) for r in dictionary_validation]
        +[('validation:fresh-ud',r[2],r[3],r[4]) for r in valid_ud])
    write('heldout',[('heldout:fresh-written500','',code(r['text']),r['text']) for r in dictionary_reserve]
        +[('heldout:fresh-ud-legco',r[2],r[3],r[4]) for r in held_ud])
    (output/'evaluation-source.jsonl').write_text(''.join(json.dumps(dict(r,split=split),ensure_ascii=False,sort_keys=True)+'\n'
        for split,rs in (('validation',dictionary_validation),('heldout',dictionary_reserve)) for r in rs))
    (output/'ud-evaluation-source.json').write_text(json.dumps(dict(validation=valid_ud,heldout=held_ud),ensure_ascii=False,indent=2)+'\n')
    lexicon={word:[max(counts,key=lambda k:(counts[k],k)),min(65535,sum(counts.values()))]
             for word,counts in sorted(lexical.items()) if sum(counts.values())>=2 or len(word)>=2}
    (output/'lexicon.json').write_text(json.dumps(lexicon,ensure_ascii=False,sort_keys=True)+'\n')
    (output/'UD-README.md').write_text((ud_dir/'README.md').read_text());(output/'UD-LICENSE.txt').write_text((ud_dir/'LICENSE.txt').read_text())
    manifest=dict(baseline_revision=BASELINE,hkcancor_sha256=digest(hk_source),ud_revision=revision,ud_sha256=digest(ud_file),
        dictionary_sha256=digest(dictionary_source),input_sha256=input_hashes,training_cases=len(training),reused_training_cases=len(old),
        additional_hk=sum(r[0].startswith('train:hk:') for r in training[len(old):]),additional_ud=sum(r[0].startswith('train:ud:') for r in training[len(old):]),
        lexicon_words=len(lexicon),ud_validation_cases=len(valid_ud),ud_heldout_cases=len(held_ud),fresh_written_validation=100,fresh_written_heldout=500,
        source_splits=dict(hk_training=sorted(allowed),hk_excluded=sorted(excluded),ud_training=['missing-days','temple-interview'],
            ud_validation=['what-day'],ud_heldout=['legco-2016']),rejected=dict(rejected),
        file_sha256={name:digest(output/name) for name in sorted(('train.tsv','new-training.tsv','validation.tsv','heldout.tsv',
            'evaluation-source.jsonl','ud-evaluation-source.json','lexicon.json','UD-README.md','UD-LICENSE.txt'))},
        selection='Frozen before decoding. Exact previous training duplicates and known evaluation substring6+ excluded from additions. Entire UD productions are disjoint. Extend unchanged dictionary family hash sample beyond original800; exclude source families, seen target substrings and raw training exposure before taking100/500.',
        licenses='HKCanCor CC BY4.0; UD_Cantonese-HK CC BY-SA4.0; old attributed Tatoeba CC BY2.0 France and project-authored rows. words.hk dictionary examples NCDOL1.0, evaluation-only; no dictionary example or evaluation POS enters training or lexicon.',
        limits='Older spoken dialogue/interview/parliament and dictionary usage, not contemporary private typing-frequency measurements. UD custom source split, not an official UD benchmark result. Existing raw baseline words remain possible shared lexical knowledge.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('training_cases','additional_hk','additional_ud','lexicon_words','ud_validation_cases','ud_heldout_cases')},ensure_ascii=False))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('hk',type=Path);p.add_argument('ud',type=Path);p.add_argument('dictionary',type=Path)
    p.add_argument('--output',type=Path,default=DATA);a=p.parse_args();prepare(a.hk,a.ud,a.dictionary,a.output)
