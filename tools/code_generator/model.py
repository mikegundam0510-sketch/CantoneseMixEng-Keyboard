"""Code-conditioned autoregressive character/consumption-edge generator.

The recurrent character history and a reverse code encoder jointly predict a
normalized distribution over legal (character, consumed-code-length) edges.
All sequence likelihoods include every consumed character; no target lookup.
"""
import json
from pathlib import Path
import numpy as np
from common import ROOT
from context_gru import sigmoid,tail
from sentence_language_model import read,paths

NAMES=('embedding','input','recurrent','bias','word_h','word_c','word_bias',
       'code_embedding','code_recurrent','length_h','length_c','length_bias')


def initialize(checkpoint,seed=20261017):
    old,chars,children,prior,_=read(checkpoint);rng=np.random.default_rng(seed)
    ix,bits,mask=paths(children,len(prior));b=old['output_bias'][ix]
    word_bias=((bits*b-np.logaddexp(0,b))*mask).sum(axis=1)
    word_h=np.sum(((bits-sigmoid(b))*mask)[:,:,None]*old['output'][ix],axis=1)
    word_h[0]=word_h[2]=0;word_bias[0]=word_bias[2]=-30
    h=old['recurrent'].shape[0];c=16
    values={k:old[k].copy() for k in ('embedding','input','recurrent','bias')}
    values.update(word_h=word_h,word_c=rng.normal(0,.01,(len(prior),c)),word_bias=word_bias,
        code_embedding=rng.normal(0,.1,(27,c)),code_recurrent=rng.normal(0,.08,(c,c)),
        length_h=np.zeros((h,2)),length_c=np.zeros((c,2)),length_bias=np.log([.1,.9]))
    values={k:np.asarray(v,dtype=np.float32) for k,v in values.items()};values['code_embedding'][0]=0
    return values,chars


def code_states(v,code_ids):
    b,l=code_ids.shape;c=v['code_recurrent'].shape[0]
    states=np.zeros((b,l+1,c),dtype=v['embedding'].dtype)
    for p in range(l-1,-1,-1):
        active=(code_ids[:,p]!=0)[:,None]
        new=np.tanh(v['code_embedding'][code_ids[:,p]]+states[:,p+1]@v['code_recurrent'])
        states[:,p]=np.where(active,new,states[:,p+1])
    return states


def step(v,token,h):
    x=v['embedding'][token];a=x@v['input']+v['bias'];b=h@v['recurrent'];width=h.shape[-1]
    z=sigmoid(a[...,:width]+b[...,:width]);r=sigmoid(a[...,width:2*width]+b[...,width:2*width])
    g=np.tanh(a[...,2*width:]+r*b[...,2*width:]);new=(1-z)*h+z*g
    return new,(token,x,h,z,r,g,b)


class Codec:
    def __init__(self,characters,codes):
        self.characters=characters;self.vocab={c:i+3 for i,c in enumerate(characters)}
        self.codes={c:tuple(codes.get(c,[])) for c in characters};self.by_code={}
        for c,items in self.codes.items():
            for code in items:self.by_code.setdefault(code,[]).append(self.vocab[c])
        self.by_code={k:sorted(set(v)) for k,v in self.by_code.items()};self.cache={}
    def edges(self,code,pos):
        key=code[pos:pos+2]
        if key not in self.cache:
            items=[]
            for length in (1,2):
                if len(key)<length:continue
                items.extend((i,length) for i in self.by_code.get(key[:length],[]))
            self.cache[key]=(np.asarray([i for i,n in items],dtype=np.int32),np.asarray([n-1 for i,n in items],dtype=np.int32))
        return self.cache[key]
    def align(self,code,text):
        if not text or any(c not in self.vocab for c in text):return None
        failed=set()
        def visit(pos,at):
            if at==len(text):return [] if pos==len(code) else None
            if (pos,at) in failed:return None
            for n in (2,1):
                if code[pos:pos+n] in self.codes[text[at]] and pos+n<=len(code):
                    rest=visit(pos+n,at+1)
                    if rest is not None:return [n]+rest
            failed.add((pos,at));return None
        return visit(0,0)
    def encode(self,row,key='text'):
        text=row[key];context=tail(row.get('context',''));alignment=row.get('alignment') if key=='text' else None
        alignment=alignment or self.align(row['code'],text)
        if alignment is None or sum(alignment)!=len(row['code']):raise ValueError('Unaligned training target')
        seq=[2]+[self.vocab.get(c,1) for c in context]+[self.vocab[c] for c in text]
        pos=[-1]*len(context);at=0;targets=[-1]*len(context)
        for c,n in zip(text,alignment):
            ids,lens=self.edges(row['code'],at)
            matched=np.flatnonzero((ids==self.vocab[c])&(lens==n-1))
            if len(matched)!=1:raise ValueError('Target edge missing')
            pos.append(at);targets.append(int(matched[0]));at+=n
        return seq,pos,targets


def batch(rows,codec,key='text'):
    enc=[codec.encode(r,key) for r in rows];b=len(rows);t=max(len(s) for s,p,y in enc)-1
    tokens=np.zeros((b,t),dtype=np.int32);positions=np.full((b,t),-1,dtype=np.int32);targets=np.zeros((b,t),dtype=np.int32)
    code=np.zeros((b,max(len(r['code']) for r in rows)),dtype=np.int32)
    for i,((seq,pos,y),r) in enumerate(zip(enc,rows)):
        tokens[i,:len(seq)-1]=seq[:-1];positions[i,:len(pos)]=pos
        targets[i,:len(y)]=np.maximum(y,0);code[i,:len(r['code'])]=[ord(c)-96 for c in r['code']]
    return rows,tokens,positions,targets,code


def forward(v,packed,codec,cache=False):
    rows,tokens,positions,targets,code=packed;b,t=tokens.shape
    cs=code_states(v,code);h=np.zeros((b,v['recurrent'].shape[0]),dtype=v['embedding'].dtype)
    sums=np.zeros(b,dtype=h.dtype);steps=[]
    for at in range(t):
        raw,gru=step(v,tokens[:,at],h);active=(tokens[:,at]!=0)[:,None];new=np.where(active,raw,h)
        pos=positions[:,at];mask=(pos>=0).astype(h.dtype);options=[codec.edges(rows[i]['code'],int(p)) if p>=0 else (np.array([0],np.int32),np.array([0],np.int32)) for i,p in enumerate(pos)]
        k=max(len(ids) for ids,lens in options);ids=np.zeros((b,k),np.int32);lens=np.zeros((b,k),np.int32);legal=np.zeros((b,k),bool)
        for i,(ii,ll) in enumerate(options):ids[i,:len(ii)]=ii;lens[i,:len(ii)]=ll;legal[i,:len(ii)]=True
        e=cs[np.arange(b),np.maximum(pos,0)]
        wh=v['word_h'][ids]+v['length_h'].T[lens];wc=v['word_c'][ids]+v['length_c'].T[lens]
        logits=np.einsum('bkh,bh->bk',wh,new)+np.einsum('bkc,bc->bk',wc,e)+v['word_bias'][ids]+v['length_bias'][lens]
        logits=np.where(legal,logits,-1e9);shift=logits.max(axis=1,keepdims=True);probs=np.exp(logits-shift)*legal;z=probs.sum(axis=1,keepdims=True);probs/=z
        sums+=mask*(logits[np.arange(b),targets[:,at]]-shift[:,0]-np.log(z[:,0]))
        if cache:steps.append((gru,active,new,e,pos,mask,ids,lens,probs,targets[:,at]))
        h=new
    counts=(positions>=0).sum(axis=1);lengths=np.asarray([len(r['code']) for r in rows],dtype=h.dtype)
    if np.any(counts<=0):raise ValueError('Empty candidate')
    result=(sums/lengths,-sums/counts)
    return result+(dict(steps=steps,code_states=cs,code=code,counts=counts,lengths=lengths),) if cache else result


def backward(v,cached,sum_derivative):
    grad={k:np.zeros_like(a) for k,a in v.items()};cs=cached['code_states'];code=cached['code'];b=code.shape[0]
    de=np.zeros_like(cs);width=v['recurrent'].shape[0];dh=np.zeros((b,width),dtype=cs.dtype)
    for gru,active,new,e,pos,mask,ids,lens,probs,target in reversed(cached['steps']):
        dl=-probs.copy();dl[np.arange(b),target]+=1;dl*=sum_derivative[:,None]*mask[:,None]
        np.add.at(grad['word_h'],ids,dl[:,:,None]*new[:,None,:]);np.add.at(grad['word_c'],ids,dl[:,:,None]*e[:,None,:]);np.add.at(grad['word_bias'],ids,dl)
        for n in (0,1):
            amount=np.sum(dl*(lens==n),axis=1)
            grad['length_h'][:,n]+=new.T@amount;grad['length_c'][:,n]+=e.T@amount;grad['length_bias'][n]+=amount.sum()
        dh+=np.einsum('bk,bkh->bh',dl,v['word_h'][ids]+v['length_h'].T[lens])
        signal=np.einsum('bk,bkc->bc',dl,v['word_c'][ids]+v['length_c'].T[lens])
        np.add.at(de,(np.arange(b),np.maximum(pos,0)),signal)
        token,x,previous,z,r,g,recurrent=gru;used=dh*active;old=dh*(1-active)+used*(1-z)
        dg=used*z*(1-g*g);dz=used*(g-previous)*z*(1-z);dr=dg*recurrent[:,2*width:]*r*(1-r)
        da=np.concatenate((dz,dr,dg),axis=1);db=np.concatenate((dz,dr,dg*r),axis=1)
        grad['input']+=x.T@da;grad['recurrent']+=previous.T@db;grad['bias']+=da.sum(axis=0);np.add.at(grad['embedding'],token,da@v['input'].T)
        dh=old+db@v['recurrent'].T
    carry=np.zeros_like(cs[:,0])
    for p in range(code.shape[1]):
        active=(code[:,p]!=0)[:,None];signal=de[:,p]+carry;dv=signal*active*(1-cs[:,p]**2)
        np.add.at(grad['code_embedding'],code[:,p],dv);grad['code_recurrent']+=cs[:,p+1].T@dv
        carry=dv@v['code_recurrent'].T+signal*(1-active)
    grad['embedding'][0]=0;grad['code_embedding'][0]=0
    return grad


def loss_gradient(v,packed,codec,weights):
    _,nll,c=forward(v,packed,codec,True)
    return float(np.mean(weights*nll)),backward(v,c,-weights/(len(weights)*c['counts']))


def pair_gradient(v,positive,negative,codec,weights):
    sp,nll,cp=forward(v,positive,codec,True);sn,_,cn=forward(v,negative,codec,True)
    gap=2*(sp-sn);loss=float(np.mean(weights*(np.logaddexp(0,-gap)+.1*nll)))
    d=-2*weights*sigmoid(-gap)/len(weights)
    gp=backward(v,cp,d/cp['lengths']-.1*weights/(len(weights)*cp['counts']))
    gn=backward(v,cn,-d/cn['lengths'])
    return loss,{k:gp[k]+gn[k] for k in NAMES}


def save(path,v,characters):
    if Path(path).exists():raise ValueError('Do not replace a checkpoint')
    np.savez_compressed(path,characters=np.array([ord(c) for c in characters],np.int32),**v)


def load(path):
    with np.load(path,allow_pickle=False) as src:
        v={k:src[k] for k in NAMES};characters=[chr(int(c)) for c in src['characters']]
    if any(not np.isfinite(a).all() for a in v.values()):raise ValueError('Nonfinite generator weight')
    return v,characters


def decode(v,codec,code,context='',beam=24):
    if not 1<=len(code)<=48 or not code.isascii() or not code.isalpha():return []
    code=code.lower();cs=code_states(v,np.array([[ord(c)-96 for c in code]],np.int32))[0]
    h=np.zeros(v['recurrent'].shape[0],np.float32)
    for token in [2]+[codec.vocab.get(c,1) for c in tail(context)]:h=step(v,token,h)[0]
    # Deferred hidden-state transitions evaluate only surviving histories.
    lattice=[[] for _ in range(len(code)+1)];lattice[0]=[('',0.,h)]
    states={'':h}
    for pos in range(len(code)):
        unique={}
        for text,score,parent in lattice[pos]:
            if text not in unique or score>unique[text][1]:unique[text]=(text,score,parent)
        paths_here=sorted(unique.values(),key=lambda p:(-p[1],p[0]))[:beam]
        if not paths_here:continue
        ids,lens=codec.edges(code,pos)
        if not len(ids):continue
        hs=[]
        for text,score,parent in paths_here:
            if text not in states:states[text]=step(v,codec.vocab[text[-1]],parent)[0]
            hs.append(states[text])
        hs=np.stack(hs);e=cs[pos]
        logits=hs@(v['word_h'][ids]+v['length_h'].T[lens]).T+(v['word_c'][ids]+v['length_c'].T[lens])@e+v['word_bias'][ids]+v['length_bias'][lens]
        shifted=logits-logits.max(axis=1,keepdims=True);logp=shifted-np.log(np.exp(shifted).sum(axis=1,keepdims=True))
        scores=np.array([p[1] for p in paths_here])[:,None]+logp
        for length in (1,2):
            columns=np.flatnonzero(lens==length-1)
            if not len(columns):continue
            flat=scores[:,columns].reshape(-1);chosen=np.argsort(-flat,kind='stable')[:beam]
            for ix in chosen:
                i,j=divmod(int(ix),len(columns));column=int(columns[j]);text=paths_here[i][0]+codec.characters[int(ids[column])-3]
                lattice[pos+length].append((text,float(flat[ix]),hs[i]))
    best={}
    for text,score,parent in lattice[-1]:best[text]=max(best.get(text,-float('inf')),score)
    return sorted(best.items(),key=lambda p:(-p[1],p[0]))[:20]
