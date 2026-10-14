#!/usr/bin/env python3
"""Freeze reviewed public dictionary examples as evaluation-only HK written data.

No example trains the model. Prefix training uses the licensed previous corpus
training cases and separately authored daily templates. Outcomes never select
examples. Original glyphs are retained except NFC/markup/pronunciation removal.
"""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import itertools
import io
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from prepare_tatoeba_corpus import digest
from sentence_features import han
from train_phrase_model import ROOT,ASSETS,reverse_codes

DATA=ROOT/'tools/data/daily_prefix'
CSV_SHA='31c55697f459564312e958bc87d077855b85c6965bab1a683c54d6ce6b6d5ddb'
BASELINE='241803b'
MARKERS=set('我你佢哋唔冇未嘅咗喺嗰呢咁嚟咩啲嘢睇攞俾畀瞓喎㗎噉搵啱')

def hashed(text):return hashlib.sha256(text.encode()).hexdigest()

def existing_targets():
    result=set();hashes={}
    tracked=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE],cwd=ROOT,text=True).splitlines())
    for path in sorted(list(ROOT.glob('tools/data/**/*.tsv'))+list(ROOT.glob('tools/*cases.tsv'))):
        if str(path.relative_to(ROOT)) not in tracked:continue
        hashes[str(path.relative_to(ROOT))]=digest(path)
        for line in path.read_text().splitlines():
            if not line or line.startswith('#'):continue
            for text in line.split('\t'):
                if len(text)>=6 and all(han(c) for c in text):result.add(text)
    return result,hashes

def extracts(text):
    in_example=False;number=0
    for line in text.splitlines():
        if line.strip()=='<eg>':in_example=True;continue
        if line.startswith(('----','<explanation>')):in_example=False
        if not in_example or not line.startswith('yue:'):continue
        value=unicodedata.normalize('NFC',line[4:].strip())
        value=re.sub(r'\s*\([a-zA-Z0-9 ,./:;?\-]+\)\s*$','',value)
        value=value.replace('#','').strip();number+=1
        # Full punctuation-delimited sentences, retaining internal comma
        # clauses as an ordinary Han composition without committing punctuation.
        for match in re.finditer(r'([^。！？!?；;]+)[。！？!?；;]',value):
            sentence=match[1]
            normalized=re.sub(r'[，、,「」『』“”‘’"\s]','',sentence)
            if normalized and all(han(c) for c in normalized):yield number,normalized,value

def prepare(source,output=DATA,heldout_count=800):
    if digest(source)!=CSV_SHA:raise ValueError('Pinned dictionary example CSV required')
    reverse=reverse_codes();prior,inputs=existing_targets();rejected=Counter()
    frequencies={}
    for line in (ASSETS/'character_frequencies.tsv').read_text().splitlines():
        f=line.split('\t')
        if len(f)==2 and f[1].isdigit():frequencies[f[0]]=int(f[1])
    records=[]
    for row in csv.reader(io.StringIO(source.read_text())):
        if len(row)!=6 or row[4]!='OK' or row[5]!='已公開':
            rejected['not_public_reviewed']+=1;continue
        for number,text,original in extracts(row[2]):
            if not 6<=len(text)<=24 or not all(c in reverse for c in text):
                rejected['length_or_code']+=1;continue
            if not MARKERS.intersection(text):rejected['no_hk_conversational_marker']+=1;continue
            if sum(frequencies.get(c,0)<500 for c in text)>max(1,len(text)//8):
                rejected['rare_character_ratio']+=1;continue
            if any(p in text or text in p for p in prior):
                rejected['known_target_overlap']+=1;continue
            lemmas=tuple(sorted(part.split(':')[0] for part in row[1].split(',')))
            records.append({'id':row[0],'example':number,'text':text,'original':original,'lemmas':lemmas})
    # Related headwords, duplicate examples and one-edit variants stay together.
    parents=list(range(len(records)));seen={}
    def root(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    def union(a,b):
        a,b=root(a),root(b);parents[max(a,b)]=min(a,b)
    for i,r in enumerate(records):
        keys={'lemma:'+v for v in r['lemmas']}|{'text:'+r['text']}
        keys.update('edit:'+r['text'][:j]+r['text'][j+1:] for j in range(len(r['text'])))
        for key in keys:
            if key in seen:union(i,seen[key])
            else:seen[key]=i
    groups=defaultdict(list)
    for i,r in enumerate(records):groups[root(i)].append(r)
    pools={'validation':[],'heldout':[]}
    for members in groups.values():
        identity=','.join(sorted({r['id'] for r in members}));group=hashed('daily-written-group-v1:'+identity)
        split='validation' if int(group[:8],16)%5==0 else 'heldout'
        row=min(members,key=lambda r:hashed(r['id']+':'+r['text']))
        pools[split].append(dict(row,group=group))
    selected={}
    for split,count in (('validation',200),('heldout',heldout_count)):
        rows=sorted(pools[split],key=lambda r:hashed('daily-written-sample-v1:'+r['group']))[:count]
        if len(rows)!=count:raise ValueError(f'Insufficient eligible {split}: {len(rows)}')
        selected[split]=rows
    output.mkdir(parents=True,exist_ok=True)
    def code(text):return ''.join(sorted(reverse[c],key=lambda s:(-len(s),s))[0] for c in text)
    for split,rows in selected.items():
        (output/(split+'.tsv')).write_text(''.join('\t'.join(('',code(r['text']),r['text']))+'\n' for r in rows))
        (output/(split+'-source.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
    authored=json.loads((DATA/'authored.json').read_text());training=[]
    reserved={r['text'] for rows in selected.values() for r in rows}
    for topic,templates in authored['train'].items():
        for index,template in enumerate(templates):
            keys=sorted(set(re.findall(r'\{([a-z]+)\}',template)))
            variants=[]
            for values in itertools.product(*(authored['slots'][k] for k in keys)):
                text=template.format(**dict(zip(keys,values)))
                if not 6<=len(text)<=24 or not all(c in reverse for c in text):continue
                if any(p in text or text in p for p in prior|reserved):continue
                variants.append(text)
            for text in sorted(set(variants),key=lambda s:hashed('daily-authored-v1:'+s))[:12]:
                training.append((f'train:daily:{topic}:{index}','',code(text),text))
    # Reuse only already attributed training rows; public dictionary examples
    # and any of their substring-equivalent targets never train this scorer.
    licensed=[]
    for line in (ROOT/'tools/data/sentence_search/train.tsv').read_text().splitlines():
        r=tuple(line.split('\t'));text=r[3]
        if not all(c in MARKERS or frequencies.get(c,0)>=500 for c in text):continue
        if any(p in text or text in p for p in reserved):continue
        licensed.append(r)
    rows=licensed+training
    (output/'train.tsv').write_text(''.join('\t'.join(r)+'\n' for r in rows))
    manifest={'baseline_revision':BASELINE,'dictionary_csv_sha256':CSV_SHA,
        'evaluation_source':'Public, reviewed words.hk dictionary examples mirrored in AlienKevin/wordshk-tools/examples/wordshk.csv',
        'evaluation_license':'Hong Kong Lexicography Limited; Non-Commercial Open Data License1.0; evaluation-only, not bundled in app or used for training.',
        'rejected':dict(rejected),'eligible_examples':len(records),'family_groups':len(groups),
        'validation_cases':200,'heldout_cases':heldout_count,'training_cases':len(rows),
        'licensed_training_cases':len(licensed),'authored_training_cases':len(training),
        'input_sha256':inputs,'authored_sha256':digest(DATA/'authored.json'),
        'file_sha256':{n:digest(output/n) for n in ('train.tsv','validation.tsv','heldout.tsv','validation-source.jsonl','heldout-source.jsonl')},
        'allowed_training_sources':sorted({r[0] for r in rows}),
        'selection':'Source/family hash order before decoding; headword/duplicate/one-edit families kept in one split; one example per group. Known target substrings6+ excluded. New dictionary examples are evaluation-only.',
        'limits':'Human-authored dictionary usage examples, not contemporary private chat, observed typing frequency or a speaker-disjoint live-device trial. Internal commas omitted only to form a continuous Han composition. Original glyphs retained.'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print({k:manifest[k] for k in ('eligible_examples','family_groups','training_cases','authored_training_cases','validation_cases','heldout_cases')})
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv',type=Path);p.add_argument('--output',type=Path,default=DATA)
    a=p.parse_args();prepare(a.csv,a.output)
