"""Learn actual current-parent prefix repair/protection comparisons, TRAIN only."""
from collections import Counter
import gzip
import json
import numpy as np
from experiment import ROOT,DATA,WORK,REPORTS,frozen,write,digest
from prepare_data import domain
from prepare_sentence_pretrain import group,split
from train_aligned_relations import family
from train_candidate_ranker import matches
from train_phrase_model import reverse_codes
from prepare_phrase_relations import gram_index,overlap
from sentence_language_model import read,paths,batch,forward,pair_gradient,save,NAMES
from train_sentence_pretrain import weights


def collect():
    frozen();expected=(DATA/'observation-cases.tsv').read_text().splitlines();allowed=set(expected)
    rows=[];visible=[];seen=set();rejected=Counter();reverse=reverse_codes()
    evaluation=[DATA/'reserve.tsv',ROOT/'tools/data/context_search/calibration1450.tsv',
        ROOT/'tools/data/context_search/heldout.tsv',ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv']
    external=gram_index([f for p in evaluation for s in p.read_text().splitlines() for f in s.split('\t')[1::2] if len(f)>=6])
    for i in range(4):
        out=WORK/f'observed-{i}';before=(out/'visible.tsv').read_text().splitlines()
        assert ['\t'.join(r.split('\t')[:4]) for r in before]==expected[i::4]
        visible.extend(before)
        for line in (out/'prefix.tsv').read_text().splitlines():
            f=line.split('\t');assert len(f)==10 and '\t'.join(f[:4]) in allowed
            source,context,code,gold,at,positive,negative,offset,origin,rank=f;at=int(at)
            assert 0<at<len(code) and gold.startswith(positive) and origin in ('lost','survived')
            assert matches(code[:at],positive,reverse) and matches(code[:at],negative,reverse)
            assert matches(code[at:],gold[len(positive):],reverse)
            key=tuple(f[:7])
            if key in seen:continue
            seen.add(key)
            if any(overlap(context+t,external) for t in (positive,negative)):
                rejected['new_evaluation_overlap']+=1;continue
            fam=group(family(source))
            rows.append(dict(family=fam,domain=domain(fam),split=split(fam),context=context,code=code[:at],
                positive=positive,negative=negative,offset=0.,origin=origin,raw_margin=float.fromhex(offset),
                full_code=code,position=at,raw_rank=int(rank),source=source))
    # Keep original validation families out of the adapted fit, including their
    # full-positive spans admitted to the original pretrained model's holdout.
    cache=ROOT/'.native/sentence-pretrain-20261017/data'
    corpus=[json.loads(s) for s in gzip.decompress((cache/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
    oldpairs=[json.loads(s) for s in gzip.decompress((cache/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
    protected=gram_index([r['text'] for r in corpus if r['split']=='validation']+
        [r['context']+r[k] for r in oldpairs+rows if r['split']=='validation' for k in ('positive','negative')])
    clean=[]
    for r in rows:
        if r['split']=='train' and any(overlap(r['context']+r[k],protected) for k in ('positive','negative')):
            rejected['internal_validation_overlap']+=1
        else:clean.append(r)
    payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in clean).encode()
    (DATA/'pairs.jsonl.gz').write_bytes(gzip.compress(payload,mtime=0))
    write(DATA/'pair-manifest.json',dict(parent_revision=frozen()['parent_revision'],
        cases_sha256=digest(DATA/'observation-cases.tsv'),pairs_sha256=digest(DATA/'pairs.jsonl.gz'),
        observed_cases=len(expected),comparisons=len(clean),counts=dict(Counter(r['split']+':'+r['domain']+':'+r['origin'] for r in clean)),
        families={s:len({r['family'] for r in clean if r['split']==s}) for s in ('train','validation')},rejected=dict(rejected),
        observation_sha256={str((WORK/f'observed-{i}'/n).relative_to(ROOT)):digest(WORK/f'observed-{i}'/n) for i in range(4) for n in ('visible.tsv','prefix.tsv')},
        objective='Same causal prefix score as runtime, no EOS. Pair offset zero: survival uses neural gap>.25, raw score only floor/proposal order. Family/case/rival-balanced domain mass; positive LM auxiliary0.05. Lost and survived origins retained. Actual traces only, no forced reconstruction.'))
    assert clean and {r['split'] for r in clean}=={'train','validation'}
    return clean


def train():
    p=frozen();rows=collect();out=DATA/'model'
    if out.exists():raise ValueError('Preserve existing model')
    out.mkdir();initial=ROOT/'app/src/main/assets/sentence_language.b64'
    values,characters,children,prior,strength=read(initial);assert strength==.5
    tree=paths(children,len(prior));vocab={c:i+3 for i,c in enumerate(characters)}
    tr=[r for r in rows if r['split']=='train'];va=[r for r in rows if r['split']=='validation']
    config=p['training'];mix=config['source_mix'];wt=weights(tr,mix,True);wv=weights(va,mix,True)
    def objective(data,w):
        total=0.
        for start in range(0,len(data),128):
            chunk=data[start:start+128]
            sp,nll=forward(values,*batch(chunk,vocab,'positive'),tree,prior)
            sn,_=forward(values,*batch(chunk,vocab,'negative'),tree,prior)
            total+=float(w[start:start+len(chunk)]@(np.logaddexp(0,-.5*(sp-sn))+.05*nll))
        return total/len(data)
    initial_loss=best=objective(va,wv);best_epoch=0;best_values={k:v.copy() for k,v in values.items()}
    moment={k:np.zeros_like(v) for k,v in values.items()};variance={k:np.zeros_like(v) for k,v in values.items()}
    rng=np.random.default_rng(config['seed']);step=0;history=[]
    for epoch in range(config['epochs']):
        order=rng.permutation(len(tr));total=0.
        for start in range(0,len(tr),config['batch']):
            ix=order[start:start+config['batch']];chunk=[tr[i] for i in ix]
            loss,grad=pair_gradient(values,batch(chunk,vocab,'positive'),batch(chunk,vocab,'negative'),tree,prior,np.zeros(len(ix),dtype=np.float32),wt[ix])
            norm=np.sqrt(sum(float(np.sum(g*g)) for g in grad.values()));scale=min(1.,5/max(norm,1e-12));step+=1
            for k in NAMES:
                g=grad[k]*scale;moment[k]=.9*moment[k]+.1*g;variance[k]=.999*variance[k]+.001*g*g
                values[k]-=config['rate']*(moment[k]/(1-.9**step))/(np.sqrt(variance[k]/(1-.999**step))+1e-8)
            values['embedding'][0]=0;total+=loss*len(chunk)
        valid=objective(va,wv)
        if not np.isfinite(valid) or not all(np.isfinite(v).all() for v in values.values()):raise ValueError('Nonfinite training')
        record=dict(epoch=epoch+1,train_loss=total/len(tr),internal_validation_loss=valid)
        history.append(record);print(json.dumps(record),flush=True)
        if valid<best:best=valid;best_epoch=epoch+1;best_values={k:v.copy() for k,v in values.items()}
    save(out/'prefix.b64',best_values,characters,children,prior)
    write(out/'report.json',dict(initial_checkpoint_sha256=digest(initial),protocol_sha256=digest(DATA/'protocol.json'),
        pairs_sha256=digest(DATA/'pairs.jsonl.gz'),model_sha256=digest(out/'prefix.b64'),train=len(tr),validation=len(va),
        initial_internal_validation=initial_loss,best_internal_validation=best,best_epoch=best_epoch,epochs=history,
        improved_internal_loss=best_epoch>0,scope='Internal prefix-comparison loss only; not keyboard accuracy. No external evaluation fitted.'))


if __name__=='__main__':train()
