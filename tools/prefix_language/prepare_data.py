"""Freeze TRAIN observation identities and new evaluation-only source families."""
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import subprocess

from experiment import ROOT,DATA,WORK,BASELINE,write,digest
from prepare_sentence_pretrain import group,split
from train_aligned_relations import family
from prepare_clean_ranking import rules,spans
from prepare_daily_prefix_data import prepare as dictionary_pool,hashed
from prepare_phrase_relations import gram_index,overlap
from sentence_features import han
from train_phrase_model import reverse_codes


def domain(f):
    return 'HK' if f.startswith('train:hk:') else 'Tatoeba' if f.startswith('train:tatoeba:') else 'UD' if f.startswith('train:ud:') else 'authored'


def prepare():
    if (DATA/'inputs.json').exists():raise ValueError('Preserve fixed data')
    cache=ROOT/'.native/sentence-pretrain-20261017/data'
    corpus=[json.loads(s) for s in gzip.decompress((cache/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
    pairs=[json.loads(s) for s in gzip.decompress((cache/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
    # Only positives already admitted to the original family-disjoint pretrain
    # corpus/pair cache are observed. The checkpoint never fitted its validation.
    admitted={(r['family'],r['text']) for r in corpus}|{(r['family'],r['positive']) for r in pairs}
    buckets=defaultdict(list)
    for line in (ROOT/'tools/data/clean_ranking/train.tsv').read_text().splitlines():
        r=line.split('\t');f=group(family(r[0]));s=split(f)
        if (f,r[3]) in admitted:buckets[s,domain(f)].append(r)
    selected=[]
    for s,total in [('train',2048),('validation',512)]:
        for d,mass in [('HK',.7),('Tatoeba',.2),('UD',.05),('authored',.05)]:
            rows=sorted(buckets[s,d],key=lambda r:hashed('prefix-language-input-v1:'+'\t'.join(r)))
            selected.extend(rows[:round(total*mass)])
    selected.sort(key=lambda r:hashed('prefix-language-order-v1:'+'\t'.join(r)))
    (DATA/'observation-cases.tsv').write_text(''.join('\t'.join(r)+'\n' for r in selected))
    for i in range(4):(WORK/f'train-{i}.tsv').write_text(''.join('\t'.join(r)+'\n' for r in selected[i::4]))
    # New public dictionary families; exclude all current tracked evaluation
    # targets/families and all text seen by pretraining/adaptation.
    seen={r['text'] for r in corpus}|{r['context']+r[k] for r in pairs for k in ('positive','negative')}
    groups=set();inputs={}
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE],text=True).splitlines()
    for name in tracked:
        if not name.startswith('tools/'):continue
        p=ROOT/name
        if name.endswith('.tsv'):
            inputs[name]=digest(p)
            for line in p.read_text().splitlines():seen.update(t for t in line.split('\t') if len(t)>=6 and all(han(c) for c in t))
        elif name.endswith('.jsonl') and 'source' in p.name:
            inputs[name]=digest(p)
            for line in p.read_text().splitlines():
                row=json.loads(line)
                if 'group' in row and 'lemmas' in row:groups.add(str(row['group']))
    mapping=rules();seen.update(t for text in list(seen) for _,_,t,_ in spans(text,mapping) if len(t)>=6)
    excluded=gram_index(seen)
    source=ROOT/'.native/search-alignment-20261014/wordshk.csv'
    with tempfile.TemporaryDirectory(prefix='prefix-language-eval-') as tmp:
        dictionary_pool(source,Path(tmp),heldout_count=5000)
        candidates=[json.loads(s) for s in (Path(tmp)/'heldout-source.jsonl').read_text().splitlines()]
    fresh=[]
    for r in sorted(candidates,key=lambda r:hashed('prefix-language-families-v1:'+r['group'])):
        forms=[r['text']]+[t for _,_,t,_ in spans(r['text'],mapping)]
        if r['group'] not in groups and not any(overlap(t,excluded) for t in forms):fresh.append(r)
    # Capacity audit found only543 groups before any model fitting/outcome.
    # Preserve500 independent groups; use existing1450 for calibration instead.
    reserve=fresh[:500]
    if len(reserve)!=500:raise ValueError('Insufficient new families: '+str(len(fresh)))
    reverse=reverse_codes()
    for s,rows in [('reserve',reserve)]:
        code=lambda text:''.join(sorted(reverse[c],key=lambda x:(-len(x),x))[0] for c in text)
        (DATA/(s+'.tsv')).write_text(''.join('\t'.join(('prefix-language:'+s,'',code(r['text']),r['text']))+'\n' for r in rows))
        (DATA/(s+'-source.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
    note=dict(parent=BASELINE,selected_observations=len(selected),observations_by_split_domain=dict(Counter(split(group(family(r[0])))+':'+domain(group(family(r[0]))) for r in selected)),
        pretrain_cache_sha256={str(p.relative_to(ROOT)):digest(p) for p in (cache/'corpus.jsonl.gz',cache/'pairs.jsonl.gz')},
        dictionary_sha256=digest(source),eligible_unused_evaluation_families=len(fresh),excluded_previous_groups=len(groups),
        exclusion_input_sha256=inputs,file_sha256={p.name:digest(p) for p in sorted(DATA.glob('*')) if p.suffix in ('.tsv','.jsonl')},
        policy='Fixed TRAIN subset admitted in original model cache; shared original-family internal split. Capacity audit before any fit/outcome found543 new families; preserve500 reserve, use existing1450 calibration. Reserve excludes all tracked targets/groups and full pretrain/adaptation texts6+, including CV. Dictionary examples evaluation-only NCDOL1.0; never fitted or packaged.')
    write(DATA/'inputs.json',note);print(json.dumps({k:note[k] for k in ('selected_observations','observations_by_split_domain','eligible_unused_evaluation_families')}))


if __name__=='__main__':prepare()
