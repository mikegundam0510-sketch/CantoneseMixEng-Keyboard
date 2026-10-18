"""Select characters using licensed TRAIN support, then freeze legal corpus views."""
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from shared import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write
from prepare_daily_prefix_data import prepare as dictionary_pool,hashed
from prepare_phrase_relations import gram_index,overlap
from prepare_clean_ranking import rules,spans
from sentence_features import han
sys.path.insert(0,str(ROOT/'tools/code_generator'))
from model import load,Codec

CORPUS=ROOT/'.native/sentence-pretrain-20261017/data/corpus.jsonl.gz'
PAIRS=ROOT/'.native/sentence-pretrain-20261017/data/pairs.jsonl.gz'
OLD=ROOT/'.native/code-generator-20261017/corpus.jsonl.gz'
CHECKPOINT=ROOT/'tools/data/code_generator/models/teacher.npz'

def rows(path):return [json.loads(s) for s in gzip.decompress(path.read_bytes()).decode().splitlines()]

def reserve(corpus):
    # Capacity is audited before fitting/outcomes. Never reuse either consumed500.
    seen={r['text'] for r in corpus}
    seen.update(r.get('context','')+r[k] for r in rows(PAIRS) for k in ('positive','negative'))
    groups=set();inputs={}
    for name in subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE],cwd=ROOT,text=True).splitlines():
        if not name.startswith('tools/'):continue
        path=ROOT/name
        if name.endswith('.tsv'):
            inputs[name]=sha(path)
            for line in path.read_text().splitlines():
                seen.update(t for t in line.split('\t') if len(t)>=6 and all(han(c) for c in t))
        elif name.endswith('.jsonl') and 'source' in path.name:
            inputs[name]=sha(path)
            for line in path.read_text().splitlines():
                r=json.loads(line)
                if 'group' in r and 'lemmas' in r:groups.add(str(r['group']))
    mapping=rules();seen.update(t for text in list(seen) for _,_,t,_ in spans(text,mapping) if len(t)>=6)
    excluded=gram_index(seen)
    source=ROOT/'.native/search-alignment-20261014/wordshk.csv'
    inputs[str(source.relative_to(ROOT))]=sha(source)
    # Original extractor's complete fixed eligible heldout pool, not an outcome sample.
    with tempfile.TemporaryDirectory(prefix='vocabulary-eval-') as folder:
        dictionary_pool(source,Path(folder),heldout_count=5550)
        candidates=[json.loads(s) for s in (Path(folder)/'heldout-source.jsonl').read_text().splitlines()]
    fresh=[]
    for r in sorted(candidates,key=lambda r:hashed('vocabulary-reserve-v1:'+r['group'])):
        forms=[r['text']]+[t for _,_,t,_ in spans(r['text'],mapping)]
        if r['group'] not in groups and not any(overlap(t,excluded) for t in forms):fresh.append(r)
    selected=fresh[:500]
    # Fix available N before any vocabulary result/fit/decode; >=200 for eligibility.
    if len(selected)<200:raise ValueError('Insufficient new independent families: '+str(len(selected)))
    write(DATA/'reserve-capacity.json',dict(complete_pool=5550,eligible_unused_families=len(fresh),
        selected=len(selected),minimum_eligible=200,excluded_previous_groups=len(groups),
        purpose='Independent evaluation only, never fitting or APK. No decoder-success filter. Pool/family selection precedes vocabulary choice and fitting.',
        sha256=inputs))
    (DATA/'reserve-source.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in selected))
    return selected,inputs

def prepare():
    if DATA.exists() or WORK.exists():raise ValueError('Preserve existing experiment; use separately declared paths')
    DATA.mkdir(parents=True);WORK.mkdir(parents=True);REPORTS.mkdir(parents=True)
    corpus=rows(CORPUS);fresh,inputs=reserve(corpus)
    dictionary=ROOT/'app/src/main/assets/cangjie5.base.dict.yaml'
    frequencies=ROOT/'app/src/main/assets/character_frequencies.tsv'
    allcodes=defaultdict(set);body=False
    for line in dictionary.read_text().splitlines():
        if line=='...':body=True;continue
        if not body or line.startswith('#'):continue
        f=line.split('\t')
        if len(f)<2 or len(f[0])!=1 or not han(f[0]) or not 1<=len(f[1])<=5 or not all('a'<=c<='z' for c in f[1]):continue
        allcodes[f[0]].add(f[1] if len(f[1])==1 else f[1][0]+f[1][-1])
    def code(text):return ''.join(sorted(allcodes[c],key=lambda s:(-len(s),s))[0] for c in text)
    (DATA/'reserve.tsv').write_text(''.join('\t'.join(('vocabulary:reserve','',code(r['text']),r['text']))+'\n' for r in fresh))
    evaluation=[ROOT/'tools/data/context_search/calibration1450.tsv',ROOT/'tools/data/context_search/heldout.tsv',
        ROOT/'tools/data/prefix_language/reserve.tsv',ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv',DATA/'reserve.tsv']
    texts=[]
    for p in evaluation:
        for line in p.read_text().splitlines():
            for field in line.split('\t')[1::2]:texts.extend(t for _,_,t,_ in spans(field,rules()) if len(t)>=6)
    external=gram_index(texts)
    internal=gram_index(r['text'] for r in corpus if r['split']=='validation')
    admitted=[r for r in corpus if not overlap(r['text'],external) and
        (r['split']!='train' or not overlap(r['text'],internal))]
    counts=Counter();families=defaultdict(set);hk=Counter();domains=defaultdict(set)
    for r in admitted:
        if r['split']!='train':continue
        counts.update(r['text'])
        if r['domain']=='HK':hk.update(r['text'])
        for c in set(r['text']):families[c].add(r['family']);domains[c].add(r['domain'])
    freq={f[0]:int(f[1]) for line in frequencies.read_text().splitlines() if len(f:=line.split('\t'))==2 and f[1].isdigit()}
    _,old=load(CHECKPOINT);oldset=set(old)
    new=sorted((c for c in counts if c not in oldset and c in allcodes and counts[c]>=2 and
        (len(families[c])>=2 or hk[c]>=3) and (freq.get(c,0)>=500 or hk[c]>=3)),key=lambda c:(-counts[c],ord(c)))[:512]
    unsupported=[]
    while True:
        available=oldset|set(new)
        supervised=set(c for r in admitted if r['split']=='train' and 2<=len(r['text'])<=24 and set(r['text'])<=available for c in r['text'])
        removed=[c for c in new if c not in supervised]
        if not removed:break
        unsupported.extend(removed);new=[c for c in new if c in supervised]
    characters=sorted(oldset|set(new));codes={c:sorted(allcodes[c],key=lambda s:(-len(s),s)) for c in characters}
    oldcodes=json.loads((ROOT/'tools/data/code_generator/codes.json').read_text())
    if any(codes[c]!=oldcodes[c] for c in old):raise ValueError('Existing code facts changed')
    codec=Codec(characters,codes)
    write(DATA/'codes.json',codes)
    write(DATA/'vocabulary.json',dict(old=len(old),new=len(new),total=len(characters),characters=characters,
        additions=[dict(character=c,train_count=counts[c],families=len(families[c]),hk_count=hk[c],lexical_frequency=freq.get(c,0),domains=sorted(domains[c])) for c in new],
        untrainable_additions=unsupported,
        rule='Retain all2248 old characters/code aliases. New: >=2 TRAIN occurrences; >=2 original TRAIN families OR >=3 HK occurrences; licensed lexical frequency>=500 OR >=3 HK occurrences; real dictionary codes. Max512 by TRAIN count then codepoint, then iteratively require a fully supported2..24 TRAIN span. No validation/test character selection.'))
    base=rows(OLD);selected=[];seen=set();rejected=Counter()
    for r in base:
        if overlap(r.get('context','')+r['text'],external):rejected['old_external']+=1;continue
        q=dict(r,kind='protection');selected.append(q);seen.add((r['family'],r['context'],r['text']))
    for r in admitted:
        text=r['text'];original=text
        if not set(text).intersection(new) or not 2<=len(text)<=24 or any(c not in codes for c in text):continue
        context=''
        if len(text)>=8 and int(hashed('code-context-v1:'+r['family']+text)[:8],16)%3==0:context,text=text[:3],text[3:]
        # New letters must occur as supervised output, not only in left context.
        if set(context).intersection(new):context,text='',original
        if (r['family'],context,text) in seen:continue
        parts=[]
        for at,c in enumerate(text):
            variants=codes[c];pick=-1 if len(variants)>1 and int(hashed('code-alias-v1:'+r['family']+original+str(at))[:8],16)%10==0 else 0
            parts.append(variants[pick])
        if len(''.join(parts))>48:continue
        selected.append(dict(family=r['family'],domain=r['domain'],split=r['split'],context=context,text=text,
            code=''.join(parts),alignment=list(map(len,parts)),origin=r['origin'],kind='addition'))
        seen.add((r['family'],context,text))
    for r in selected:
        if codec.align(r['code'],r['text']) is None:raise ValueError('Illegal prepared alignment')
    targets=Counter(c for r in selected if r['split']=='train' for c in r['text'])
    if any(not targets[c] for c in new):raise ValueError('New character without a supervised TRAIN target')
    payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in selected).encode()
    (WORK/'corpus.jsonl.gz').write_bytes(gzip.compress(payload,mtime=0))
    # Only character/code facts and hashes are published, never CV prompt views.
    facts=WORK/'code-facts.tsv';facts.write_text(''.join(c+'\t'+','.join(codes[c])+'\n' for c in characters))
    checks=[r for r in selected if r['kind']=='addition' and r['domain']!='CV'][:96]
    (WORK/'legal-cases.tsv').write_text(''.join('\t'.join((r['family'],r['code'],r['text']))+'\n' for r in checks))
    required=[CORPUS,PAIRS,OLD,CHECKPOINT,dictionary,frequencies]+evaluation
    inputs.update({str(p.relative_to(ROOT)):sha(p) for p in required})
    write(DATA/'manifest.json',dict(parent_revision=BASELINE,old_vocabulary=len(old),added=len(new),vocabulary=len(characters),
        corpus=dict(Counter(r['split']+':'+r['kind']+':'+r['domain'] for r in selected)),rejected=dict(rejected),
        cache_sha256=sha(WORK/'corpus.jsonl.gz'),sha256=inputs,
        rule='Original-family split preserved. Full original validation and every old/new evaluation6+ excluded from TRAIN. New vocabulary uses admitted TRAIN only. CommonVoice no author IDs, TRAIN only, ignored cache. Independent families frozen before vocabulary and fit.'))
    print(json.dumps(dict(old=len(old),added=len(new),total=len(characters),corpus=dict(Counter(r['split']+':'+r['kind'] for r in selected)),reserve=len(fresh))))

if __name__=='__main__':prepare()
