"""Admit licensed text/code alignments and actual current-parent errors only."""
from collections import Counter,defaultdict
import gzip,json,hashlib,subprocess
from common import ROOT,DATA,WORK,BASELINE,write,digest
from model import initialize,Codec
from prepare_sentence_pretrain import group,split
from train_aligned_relations import family
from prepare_phrase_relations import gram_index,overlap
from prepare_clean_ranking import rules,spans
from sentence_features import han


def hashed(s):return hashlib.sha256(s.encode()).hexdigest()


def prepare():
    if (DATA/'manifest.json').exists() or (WORK/'corpus.jsonl.gz').exists():raise ValueError('Use fresh outputs')
    checkpoint=ROOT/'app/src/main/assets/sentence_language.b64';_,characters=initialize(checkpoint)
    vocabulary=set(characters);codes=defaultdict(set);body=False
    dictionary=ROOT/'app/src/main/assets/cangjie5.base.dict.yaml'
    for line in dictionary.read_text().splitlines():
        if line=='...':body=True;continue
        if not body or line.startswith('#'):continue
        f=line.split('\t')
        if len(f)<2 or f[0] not in vocabulary or not 1<=len(f[1])<=5 or not all('a'<=c<='z' for c in f[1]):continue
        code=f[1] if len(f[1])==1 else f[1][0]+f[1][-1];codes[f[0]].add(code)
    codes={c:sorted(items,key=lambda s:(-len(s),s)) for c,items in codes.items()}
    codec=Codec(characters,codes);write(DATA/'codes.json',codes)
    inputs=[ROOT/'.native/sentence-pretrain-20261017/data/corpus.jsonl.gz',ROOT/'.native/sentence-pretrain-20261017/data/pairs.jsonl.gz',
        dictionary,checkpoint,ROOT/'tools/data/context_search/calibration1450.tsv',ROOT/'tools/data/context_search/heldout.tsv',
        ROOT/'tools/data/prefix_language/reserve.tsv',ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv']
    mapping=rules();excluded=set()
    for p in inputs[4:]:
        for line in p.read_text().splitlines():
            for text in line.split('\t')[1::2]:
                if len(text)>=6:
                    excluded.add(text);excluded.update(t for a,b,t,m in spans(text,mapping) if len(t)>=6)
    external=gram_index(excluded)
    corpus=[json.loads(s) for s in gzip.decompress(inputs[0].read_bytes()).decode().splitlines()]
    oldpairs=[json.loads(s) for s in gzip.decompress(inputs[1].read_bytes()).decode().splitlines()]
    buckets=defaultdict(list);rejected=Counter()
    for r in corpus:
        text=r['text']
        if not 2<=len(text)<=24 or any(c not in codes for c in text):rejected['text_length_or_neural_vocabulary']+=1;continue
        if overlap(text,external):rejected['external_overlap']+=1;continue
        context='';original=text
        if len(text)>=8 and int(hashed('code-context-v1:'+r['family']+text)[:8],16)%3==0:context,text=text[:3],text[3:]
        alignment=[];parts=[]
        for at,c in enumerate(text):
            variants=codes[c];pick=0
            if len(variants)>1 and int(hashed('code-alias-v1:'+r['family']+original+str(at))[:8],16)%10==0:pick=-1
            parts.append(variants[pick]);alignment.append(len(parts[-1]))
        code=''.join(parts)
        if len(code)>48:rejected['code_length']+=1;continue
        item=dict(family=r['family'],domain=r['domain'],split=r['split'],context=context,text=text,code=code,alignment=alignment,origin=r['origin'])
        assert codec.align(code,text) is not None
        buckets[r['split'],r['domain']].append(item)
    selected=[]
    for s,total in [('train',8192),('validation',1536)]:
        for d,mass in [('HK',.65),('CV',.2),('Tatoeba',.1),('UD',.025),('authored',.025)]:
            selected.extend(sorted(buckets[s,d],key=lambda r:hashed('code-corpus-v1:'+r['family']+r['context']+r['text']))[:round(total*mass)])
    admitted={(r['family'],r['text']) for r in corpus}|{(r['family'],r['positive']) for r in oldpairs}
    expected=(ROOT/'tools/data/prefix_language/observation-cases.tsv').read_text().splitlines()
    observed_meta=json.loads((ROOT/'tools/data/prefix_language/pair-manifest.json').read_text())
    assert subprocess.check_output(['git','rev-parse',BASELINE+':app'],text=True)==subprocess.check_output(['git','rev-parse',observed_meta['parent_revision']+':app'],text=True)
    pairs=[];ranks=Counter()
    for i in range(4):
        p=ROOT/f'.native/prefix-language-20261017/observed-{i}/visible.tsv';inputs.append(p)
        assert digest(p)==observed_meta['observation_sha256'][str(p.relative_to(ROOT))]
        rows=p.read_text().splitlines();assert ['\t'.join(s.split('\t')[:4]) for s in rows]==expected[i::4]
        for line in rows:
            source,context,code,gold,rank,values=line.split('\t');fam=group(family(source));values=values.split('|') if values else []
            assert (fam,gold) in admitted and source.startswith('train:')
            if codec.align(code,gold) is None:rejected['positive_unscorable']+=1;continue
            if not values:rejected['empty_parent_display']+=1;continue
            kind='protected_first' if values[0]==gold else 'missing' if gold not in values else 'wrong_first'
            rivals=[v for v in values if v!=gold and codec.align(code,v) is not None][:1 if kind=='protected_first' else 2]
            for rival in rivals:
                if any(overlap(context+t,external) for t in (gold,rival)):rejected['pair_external_overlap']+=1;continue
                d='HK' if fam.startswith('train:hk:') else 'Tatoeba' if fam.startswith('train:tatoeba:') else 'UD' if fam.startswith('train:ud:') else 'authored'
                pairs.append(dict(family=fam,domain=d,split=split(fam),context=context,code=code,positive=gold,negative=rival,origin=kind,source=source))
                ranks[split(fam)+':'+kind]+=1
    internal=gram_index([r['context']+r['text'] for r in selected if r['split']=='validation']+
        [r['context']+r[k] for r in pairs if r['split']=='validation' for k in ('positive','negative')]+
        [r['text'] for r in corpus if r['split']=='validation'])
    def allowed(r,keys):return r['split']!='train' or not any(overlap(r.get('context','')+r[k],internal) for k in keys)
    selected2=[r for r in selected if allowed(r,['text'])];pairs2=[r for r in pairs if allowed(r,['positive','negative'])]
    rejected['corpus_internal_overlap']=len(selected)-len(selected2);rejected['pair_internal_overlap']=len(pairs)-len(pairs2)
    for name,rows in [('corpus',selected2),('pairs',pairs2)]:
        payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode()
        (WORK/(name+'.jsonl.gz')).write_bytes(gzip.compress(payload,mtime=0))
    manifest=dict(parent_revision=BASELINE,cache_sha256={n:digest(WORK/(n+'.jsonl.gz')) for n in ('corpus','pairs')},
        input_sha256={str(p.relative_to(ROOT)):digest(p) for p in inputs},codes_sha256=digest(DATA/'codes.json'),vocabulary=len(characters),
        corpus=dict(Counter(r['split']+':'+r['domain'] for r in selected2)),pairs=dict(Counter(r['split']+':'+r['origin'] for r in pairs2)),
        families={kind:{s:len({r['family'] for r in rows if r['split']==s}) for s in ('train','validation')} for kind,rows in [('corpus',selected2),('pairs',pairs2)]},
        rejected=dict(rejected),policy='Native dictionary exact first/last code facts, all learned-vocabulary choices without frequency cutoff. Canonical/mapped aliases and original context-prefix views fixed by hashes. Original family-disjoint validation remains unfitted; external6+ overlaps excluded, including unused prefix_language reserve500. Full-generation positives can be absent from parent display. CommonVoice-containing caches ignored; no raw/derived prompt text mirrored.')
    write(DATA/'manifest.json',manifest);print(json.dumps({k:manifest[k] for k in ('vocabulary','corpus','pairs','families','rejected')}))


if __name__=='__main__':prepare()
