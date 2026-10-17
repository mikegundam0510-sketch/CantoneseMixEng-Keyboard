"""Teacher-forced code generation, then real-error/protection pair adaptation."""
from collections import Counter
import gzip,json,time
import numpy as np
from common import ROOT,DATA,WORK,REPORTS,frozen,write,digest
from model import initialize,Codec,batch,forward,loss_gradient,pair_gradient,save,NAMES
from train_sentence_pretrain import weights


def weighted(rows,mix,pair=False):
    value=weights(rows,mix,pair)
    if pair:
        for domain in {r['domain'] for r in rows}:
            ix=np.array([r['domain']==domain for r in rows]);mass=value[ix].sum()
            normalizer=sum(target for protection,target in [(False,.75),(True,.25)]
                if any(r['domain']==domain and (r['origin']=='protected_first')==protection for r in rows))
            for protection,target in [(False,.75),(True,.25)]:
                group=ix&np.array([(r['origin']=='protected_first')==protection for r in rows])
                if group.any():value[group]*=mass*target/(normalizer*value[group].sum())
    return (value/value.mean()).astype(np.float32)


def fit():
    protocol=frozen();out=DATA/'models'
    if out.exists():raise ValueError('Preserve completed models before reading/collecting outputs')
    manifest=json.loads((DATA/'manifest.json').read_text())
    for name,wanted in manifest['cache_sha256'].items():
        if digest(WORK/(name+'.jsonl.gz'))!=wanted:raise ValueError('Changed generator cache')
    corpus=[json.loads(s) for s in gzip.decompress((WORK/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
    pairs=[json.loads(s) for s in gzip.decompress((WORK/'pairs.jsonl.gz').read_bytes()).decode().splitlines()]
    v,chars=initialize(ROOT/'app/src/main/assets/sentence_language.b64');codec=Codec(chars,json.loads((DATA/'codes.json').read_text()))
    out.mkdir();history={};rng=np.random.default_rng(protocol['seed'])
    def stage(kind,rows):
        nonlocal v
        config=protocol[kind];tr=[r for r in rows if r['split']=='train'];va=[r for r in rows if r['split']=='validation']
        wt=weighted(tr,config['source_mix'],kind=='contrast');wv=weighted(va,config['source_mix'],kind=='contrast')
        def objective(data,w):
            total=0.
            for start in range(0,len(data),config['batch']):
                chunk=data[start:start+config['batch']];ww=w[start:start+len(chunk)]
                if kind=='teacher':_,nll=forward(v,batch(chunk,codec),codec);loss=nll
                else:
                    sp,nll=forward(v,batch(chunk,codec,'positive'),codec);sn,_=forward(v,batch(chunk,codec,'negative'),codec)
                    loss=np.logaddexp(0,-2*(sp-sn))+.1*nll
                total+=float(ww@loss)
            return total/len(data)
        initial=best=objective(va,wv);best_epoch=0;best_v={k:a.copy() for k,a in v.items()}
        moment={k:np.zeros_like(a) for k,a in v.items()};variance={k:np.zeros_like(a) for k,a in v.items()};step=0;epochs=[]
        print(json.dumps(dict(stage=kind,initial_validation=initial,train=len(tr),validation=len(va))),flush=True)
        for epoch in range(config['epochs']):
            started=time.perf_counter();order=rng.permutation(len(tr));total=0.
            for start in range(0,len(tr),config['batch']):
                ix=order[start:start+config['batch']];chunk=[tr[i] for i in ix]
                if kind=='teacher':loss,grad=loss_gradient(v,batch(chunk,codec),codec,wt[ix])
                else:loss,grad=pair_gradient(v,batch(chunk,codec,'positive'),batch(chunk,codec,'negative'),codec,wt[ix])
                norm=np.sqrt(sum(float(np.sum(g*g)) for g in grad.values()));scale=min(1.,5/max(norm,1e-12));step+=1
                for k in NAMES:
                    g=grad[k]*scale;moment[k]=.9*moment[k]+.1*g;variance[k]=.999*variance[k]+.001*g*g
                    rate=config['rate']*(.25 if k in ('embedding','input','recurrent','bias') else 1.)
                    v[k]-=rate*(moment[k]/(1-.9**step))/(np.sqrt(variance[k]/(1-.999**step))+1e-8)
                v['embedding'][0]=0;v['code_embedding'][0]=0;total+=loss*len(chunk)
            valid=objective(va,wv)
            if not np.isfinite(valid) or not all(np.isfinite(a).all() for a in v.values()):raise ValueError('Nonfinite generator training')
            row=dict(stage=kind,epoch=epoch+1,train_loss=total/len(tr),internal_validation=valid,seconds=time.perf_counter()-started)
            epochs.append(row);print(json.dumps(row),flush=True)
            if valid<best:best=valid;best_epoch=epoch+1;best_v={k:a.copy() for k,a in v.items()}
        v=best_v;save(out/(kind+'.npz'),v,chars)
        history[kind]=dict(train=len(tr),validation=len(va),initial_internal_validation=initial,best_internal_validation=best,best_epoch=best_epoch,epochs=epochs)
        write(out/'report.json',dict(protocol_sha256=digest(DATA/'protocol.json'),manifest_sha256=digest(DATA/'manifest.json'),
            vocabulary=len(chars),array_bytes=sum(a.nbytes for a in v.values()),stages=history,
            model_sha256={p.name:digest(p) for p in sorted(out.glob('*.npz'))},numpy=np.__version__,
            scope='Code+history conditioned normalized legal-edge generation, then same-code actual display-error comparisons. Internal losses, not keyboard accuracy. No CV raw/derived prompt cache mirrored.'))
    stage('teacher',corpus);stage('contrast',pairs)


if __name__=='__main__':fit()
