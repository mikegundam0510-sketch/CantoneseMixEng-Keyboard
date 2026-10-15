#!/usr/bin/env python3
"""Freeze traceable Han spans; split at boundaries, never guess corpus glyphs."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import re
import unicodedata
import zipfile
from prepare_daily_prefix_data import MARKERS,hashed
from prepare_phrase_relations import gram_index,overlap
from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_candidate_ranker import matches
from train_phrase_model import ROOT,reverse_codes

DATA=ROOT/'tools/data/clean_ranking'
OLD=ROOT/'tools/data/joint_ranking'
BASE=ROOT/'tools/data/phrase_relations/train.tsv'

def rules(folder=DATA):
    spec=json.loads((folder/'orthography/rules.json').read_text())
    source=folder/'orthography/HKVariants.txt'
    if digest(source)!=spec['source_sha256']:raise ValueError('Pinned orthography source changed')
    documented={f[0]:f[1] for s in source.read_text().splitlines() if not s.startswith('#') and len(f:=s.split('\t'))==2 and ' ' not in f[1]}
    for a,b in spec['pairs'].items():
        if len(a)!=1 or len(b)!=1 or documented.get(a)!=b:raise ValueError('Unverified or ambiguous orthography rule')
    return spec['pairs']

def spans(original,mapping):
    """Original code-point offsets; every non-Han character ends a span."""
    text=[];changes=[];start=0
    for at,c in enumerate(original+'\0'):
        normalized=unicodedata.normalize('NFC',c)
        if len(normalized)==1 and han(normalized):
            if not text:start=at
            value=mapping.get(normalized,normalized);text.append(value)
            if c!=value:changes.append(dict(offset=at,before=c,after=value,rule='OpenCC-reviewed' if normalized!=value else 'Unicode-NFC'))
        elif text:
            yield start,at,''.join(text),changes
            text=[];changes=[]

def inventory(path):
    meta=json.loads(path.with_suffix('.json').read_text())
    if digest(path)!=meta['output_sha256']:raise ValueError('Native code inventory changed')
    allowed=defaultdict(list);ranks={}
    for line in path.read_text().splitlines():
        c,code,rank,frequency,particle=line.split('\t');rank=int(rank)
        if not han(c) or len(c)!=1 or not re.fullmatch('[a-z]{1,2}',code) or rank<1:raise ValueError('Malformed native code rank')
        ranks[c,code]=rank
        if rank<=24:allowed[c].append(code)
    return {c:sorted(codes,key=lambda code:(-len(code),code))[0] for c,codes in allowed.items()},ranks

def exclusions(mapping):
    manifest=json.loads((OLD/'manifest.json').read_text());texts=set();hashes={}
    names={n for n in manifest['known_input_sha256'] if n.endswith('.tsv')}
    names.update('tools/data/joint_ranking/'+split+'.tsv' for split in ('validation','heldout'))
    for name in sorted(names):
        path=ROOT/name;hashes[name]=digest(path)
        for line in path.read_text().splitlines():
            if line.startswith(('#','train:')):continue
            for text in line.split('\t'):
                if len(text)>=6 and all(han(c) for c in text):
                    texts.add(text);texts.update(s for _,_,s,_ in spans(text,mapping) if len(s)>=6)
    return gram_index(texts),hashes

def hk_records(path,allowed):
    with zipfile.ZipFile(path) as archive:
        for name in sorted(allowed):
            words=[];index=0
            for line in archive.read(name).decode('utf-8-sig').splitlines()+['<sent>']:
                m=re.fullmatch(r'\s*([^/<>]+?)/([^/]+)/([^/]*)/\s*',line)
                if m:
                    # Non-Han tokens form explicit boundaries, never disappear.
                    words.append(m[1].strip())
                elif '/' in line and not line.lstrip().startswith('<'):
                    # E.g. the corpus's ○/#/#/@ annotation. Keep the actual
                    # non-Han marker as a boundary; unknown Han syntax needs review.
                    if any(han(c) for c in line):raise ValueError('Unparsed Han corpus token: '+name)
                    words.append(line.strip())
                elif '</sent_tag>' in line or '<sent>' in line:
                    if words:yield name,index,''.join(words);index+=1;words=[]

def prepare(hk,codes,output=DATA):
    generated=('train.tsv','provenance.jsonl','manifest.json')
    if any((output/name).exists() for name in generated):raise ValueError('Preserve frozen clean data; use a fresh output folder with orthography rules')
    mapping=rules(output);code_for,ranks=inventory(codes);excluded,input_hashes=exclusions(mapping)
    eligible_reverse=defaultdict(set)
    for (c,part),rank in ranks.items():
        if rank<=24:eligible_reverse[c].add(part)
    source=json.loads((ROOT/'app/src/main/assets/PHRASE_MODEL_REPORT.json').read_text())
    if digest(hk)!=source['source_sha256']['hkcancor_zip']:raise ValueError('Pinned TRAIN HKCanCor required')
    allowed=set(source['training_conversation_files']);seen=set();rows=[];provenance=[];rejected=Counter();candidates={'HK':{},'Tatoeba':{}}
    def candidate(source_id,context,original,start,end,text,changes,origin,old=False,old_code=''):
        if not 6<=len(text)<=24 or not MARKERS.intersection(text):rejected['length_or_marker']+=1;return None
        if not all(c in code_for for c in text):rejected['outside_cold_top24_character_options']+=1;return None
        # Previously fitted unchanged protection rows are retained, never called fresh.
        if (not old or changes) and overlap(text,excluded):rejected['evaluation_overlap']+=1;return None
        code=old_code if old_code and matches(old_code,text,eligible_reverse) else ''.join(code_for[c] for c in text)
        record=(source_id,context,code,text)
        info=dict(source=source_id,context=context,code=code,gold=text,origin=origin,original=original,
            start=start,end=end,changes=changes,old_code=old_code,retained=old,
            maximum_character_rank=max(ranks[c,part] for c,part in align(code,text,eligible_reverse)))
        return record,info
    reverse=reverse_codes()
    for index,line in enumerate(BASE.read_text().splitlines()):
        source_id,context,old_code,original=line.split('\t')
        parts=list(spans(original,mapping))
        if len(parts)!=1 or parts[0][:2]!=(0,len(original)):rejected['retained_non_han_boundary']+=1;continue
        start,end,text,changes=parts[0]
        item=candidate(source_id,context,original,start,end,text,changes,dict(kind='retained',file=str(BASE.relative_to(ROOT)),row=index),True,old_code)
        if item and text not in seen:rows.append(item[0]);provenance.append(item[1]);seen.add(text)
    retained=len(rows)
    for name,index,original in hk_records(hk,allowed):
        for start,end,text,changes in spans(original,mapping):
            if text in seen:continue
            source_id='train:hk:'+name+':'+hashed('clean-v1:'+str(index)+':'+str(start)+':'+text)[:16]
            item=candidate(source_id,'',original,start,end,text,changes,dict(kind='HKCanCor',file=name,utterance=index))
            if item:candidates['HK'].setdefault(text,item)
    for line in (ROOT/'tools/data/tatoeba_corpus/train.jsonl').read_text().splitlines():
        row=json.loads(line);original=row['text']
        for start,end,text,changes in spans(original,mapping):
            if text in seen:continue
            source_id='train:tatoeba:'+str(row['group'])
            item=candidate(source_id,'',original,start,end,text,changes,dict(kind='Tatoeba',id=str(row['id']),group=str(row['group'])))
            if item:candidates['Tatoeba'].setdefault(text,item)
    counts={}
    for domain,limit in (('HK',4000),('Tatoeba',1200)):
        count=0
        for text,(row,info) in sorted(candidates[domain].items(),key=lambda item:hashed('clean-ranking-v1:'+item[1][0][0]+':'+item[0])):
            if text in seen:continue
            rows.append(row);provenance.append(info);seen.add(text);count+=1
            if count==limit:break
        counts[domain]=count
    if counts['HK']<2000 or counts['Tatoeba']<600:raise ValueError('Insufficient eligible training-only natural spans')
    output.mkdir(parents=True,exist_ok=True)
    (output/'train.tsv').write_text(''.join('\t'.join(r)+'\n' for r in rows))
    (output/'provenance.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in provenance))
    input_hashes.update({str(BASE.relative_to(ROOT)):digest(BASE),'tools/data/tatoeba_corpus/train.jsonl':digest(ROOT/'tools/data/tatoeba_corpus/train.jsonl')})
    manifest=dict(parent_revision='0787863',training_cases=len(rows),retained=retained,additional=counts,
        eligible={k:len(v) for k,v in candidates.items()},rejected=dict(rejected),hkcancor_sha256=digest(hk),
        training_conversations=sorted(allowed),input_sha256=input_hashes,code_inventory_sha256=digest(codes),
        orthography_sha256=digest(output/'orthography/rules.json'),
        file_sha256={name:digest(output/name) for name in ('train.tsv','provenance.jsonl')},
        policy='Hash selection before decoding; Han spans split at every non-Han boundary; reviewed OpenCC subset and NFC only; exact cold-top24 character codes; original46 HK TRAIN files and Tatoeba TRAIN families only; new/transformed target overlap6+ with known evaluation and untouched reserve500 excluded. No rare-glyph guesses or benchmark edits.',
        limits='This is feasible-input admission, not successful decoding or fresh user data. Existing protection rows can already have appeared in old calibration. Re-encoding may choose another legal code; preserve original code and raw span provenance.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ('training_cases','retained','additional','eligible','rejected')}))
    return manifest

def align(code,text,reverse):
    """Deterministic exact alignment, for provenance and rank checks."""
    states={0:[]}
    for c in text:
        following={}
        for at,path in states.items():
            for part in sorted(reverse.get(c,()),key=lambda s:(-len(s),s)):
                if code.startswith(part,at):following.setdefault(at+len(part),path+[(c,part)])
        states=following
    return states.get(len(code),[])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('hk',type=Path);p.add_argument('codes',type=Path)
    p.add_argument('--output',type=Path,default=DATA);a=p.parse_args();prepare(a.hk,a.codes,a.output)
