"""Add train-supported rows; every old row and shared parameter stays bit-identical."""
import sys
import numpy as np
from shared import ROOT
sys.path.insert(0,str(ROOT/'tools/code_generator'))
from model import NAMES,Codec,load,save,batch,forward,loss_gradient,decode

ROW_KEYS=('embedding','word_h','word_c','word_bias')

def initialize(parent,characters,counts,seed=20261018):
    old,oldchars=load(parent);oldmap={c:i+3 for i,c in enumerate(oldchars)}
    newmap={c:i+3 for i,c in enumerate(characters)}
    if not set(oldmap).issubset(newmap):raise ValueError('Existing characters must remain')
    ids=np.array([i for c,i in newmap.items() if c not in oldmap],np.int32)
    oldids=np.array([0,1,2]+[newmap[c] for c in oldchars],np.int32)
    values={k:a.copy() for k,a in old.items()};rng=np.random.default_rng(seed)
    mass=sum(counts[c]+.5 for c in characters if c not in oldmap)
    for k in ROW_KEYS:
        a=old[k];shape=(len(characters)+3,)+a.shape[1:]
        values[k]=np.zeros(shape,np.float32);values[k][oldids]=a
        for c,i in newmap.items():
            if c in oldmap:continue
            if k=='word_bias':values[k][i]=a[1]+np.log((counts[c]+.5)/mass)
            elif k=='embedding':values[k][i]=a[1]+rng.normal(0,.01,a.shape[1:])
            elif k=='word_h':values[k][i]=a[1]
            # No unseen code affinity is invented; new word_c starts at zero.
    assert_frozen(values,old,oldids)
    return values,old,oldids,ids

def assert_frozen(values,parent,oldids):
    for k,a in parent.items():
        current=values[k][oldids] if k in ROW_KEYS else values[k]
        if current.tobytes()!=a.tobytes():raise ValueError('Old parameter changed: '+k)

def update(values,grad,ids,moment,variance,step,rate=.001):
    selected={k:grad[k][ids] for k in ROW_KEYS}
    norm=np.sqrt(sum(float(np.sum(g*g)) for g in selected.values()));scale=min(1.,5/max(norm,1e-12))
    for k in ROW_KEYS:
        g=selected[k]*scale;moment[k]=.9*moment[k]+.1*g;variance[k]=.999*variance[k]+.001*g*g
        values[k][ids]-=rate*(moment[k]/(1-.9**step))/(np.sqrt(variance[k]/(1-.999**step))+1e-8)
