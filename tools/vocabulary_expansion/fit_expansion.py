"""Fit teacher CE for new rows only; no new reranking/shared-weight objective."""
import gzip
import json
import time
import numpy as np
from shared import ROOT,DATA,WORK,sha,write,verify
from expanded_model import initialize,assert_frozen,update,ROW_KEYS,Codec,batch,forward,loss_gradient,save
from train_sentence_pretrain import weights

MIX={'HK':.65,'CV':.2,'Tatoeba':.1,'UD':.025,'authored':.025}

def balanced(rows):
    result=np.zeros(len(rows),np.float32)
    for kind in ('protection','addition'):
        ids=[i for i,r in enumerate(rows) if r['kind']==kind]
        if not ids:raise ValueError('Both new-target and protection rows required')
        w=weights([rows[i] for i in ids],MIX)
        result[ids]=w*(.5*len(rows)/len(ids))
    return result

def fit():
    p=verify();directory=DATA/'models'
    if directory.exists():raise ValueError('Preserve existing fitted model')
    m=json.loads((DATA/'manifest.json').read_text())
    if sha(WORK/'corpus.jsonl.gz')!=m['cache_sha256']:raise ValueError('Changed corpus cache')
    info=json.loads((DATA/'vocabulary.json').read_text());characters=info['characters']
    values,parent,oldids,ids=initialize(ROOT/'tools/data/code_generator/models/teacher.npz',characters,
        {r['character']:r['train_count'] for r in info['additions']})
    codec=Codec(characters,json.loads((DATA/'codes.json').read_text()))
    records=[json.loads(s) for s in gzip.decompress((WORK/'corpus.jsonl.gz').read_bytes()).decode().splitlines()]
    tr=[r for r in records if r['split']=='train'];va=[r for r in records if r['split']=='validation']
    wt,wv=balanced(tr),balanced(va);config=p['training'];rng=np.random.default_rng(p['seed'])
    def objective(rows,w):
        total=0.
        for start in range(0,len(rows),config['batch']):
            chunk=rows[start:start+config['batch']];_,nll=forward(values,batch(chunk,codec),codec)
            total+=float(w[start:start+len(chunk)]@nll)
        return total/len(rows)
    initial=best=objective(va,wv);best_epoch=0;best_values={k:a.copy() for k,a in values.items()}
    moment={k:np.zeros_like(values[k][ids]) for k in ROW_KEYS};variance={k:np.zeros_like(a) for k,a in moment.items()}
    steps=0;history=[];directory.mkdir()
    print(json.dumps(dict(initial_internal_validation=initial,train=len(tr),validation=len(va),new_rows=len(ids))),flush=True)
    for epoch in range(config['epochs']):
        started=time.perf_counter();order=rng.permutation(len(tr));losses=0.
        for start in range(0,len(tr),config['batch']):
            ix=order[start:start+config['batch']];chunk=[tr[i] for i in ix]
            loss,grad=loss_gradient(values,batch(chunk,codec),codec,wt[ix]);steps+=1
            update(values,grad,ids,moment,variance,steps,config['rate']);losses+=loss*len(chunk)
        assert_frozen(values,parent,oldids)
        valid=objective(va,wv)
        if not np.isfinite(valid) or any(not np.isfinite(a).all() for a in values.values()):raise ValueError('Nonfinite expanded model')
        row=dict(epoch=epoch+1,train_loss=losses/len(tr),internal_validation=valid,seconds=time.perf_counter()-started)
        history.append(row);print(json.dumps(row),flush=True)
        if valid<best:best=valid;best_epoch=epoch+1;best_values={k:a.copy() for k,a in values.items()}
    values=best_values;assert_frozen(values,parent,oldids);save(directory/'expanded.npz',values,characters)
    write(directory/'report.json',dict(protocol_sha256=sha(DATA/'protocol.json'),manifest_sha256=sha(DATA/'manifest.json'),
        initial_internal_validation=initial,best_internal_validation=best,best_epoch=best_epoch,epochs=history,
        old_characters=len(parent['embedding'])-3,added_characters=len(ids),vocabulary=len(characters),
        all_old_rows_and_shared_parameters_bit_identical=True,trainable_parameters=sum(values[k][ids].size for k in ROW_KEYS),
        array_bytes=sum(a.nbytes for a in values.values()),model_sha256=sha(directory/'expanded.npz'),numpy=np.__version__,
        scope='Fixed12-epoch new-row-only conditional CE; no new pair/rerank objective. Validation original families never fitted; objective decrease is not keyboard hit gain.'))

if __name__=='__main__':fit()
