"""Small reset-after GRU whole-candidate residual, NumPy training reference."""
import base64
import gzip
from pathlib import Path
import struct
import numpy as np

from sentence_features import han

NAMES=('embedding','input','recurrent','bias','output','output_bias')
MAGIC=0x47525531


def tail(text,limit=12):
    result=''
    for c in reversed(text):
        if not han(c) or len(result)==limit:break
        result=c+result
    return result


def encode(context,text,vocabulary):
    return [vocabulary.get(c,1) for c in tail(context)]+[2]+[vocabulary.get(c,1) for c in text[:48]]


def padded(rows):
    value=np.zeros((len(rows),max(map(len,rows))),dtype=np.int32)
    for i,row in enumerate(rows):value[i,:len(row)]=row
    return value


def initialize(vocabulary,dimension=16,hidden=16,seed=20261016):
    rng=np.random.default_rng(seed)
    values=dict(embedding=rng.normal(0,.12,(vocabulary,dimension)),
        input=rng.normal(0,1/np.sqrt(dimension),(dimension,3*hidden)),
        recurrent=rng.normal(0,.1,(hidden,3*hidden)),bias=np.zeros(3*hidden),
        output=rng.normal(0,.02,hidden),output_bias=np.zeros(1))
    values={k:v.astype(np.float32) for k,v in values.items()}
    values['embedding'][0]=0;values['bias'][:hidden]=-1
    return values


def sigmoid(x):return 1/(1+np.exp(-np.clip(x,-40,40)))


def forward(values,ids,cap=2,cache=False):
    hidden=values['output'].size;h=np.zeros((len(ids),hidden),dtype=values['embedding'].dtype);steps=[]
    for at in range(ids.shape[1]):
        token=ids[:,at];mask=(token!=0).astype(h.dtype)[:,None];x=values['embedding'][token]
        a=x@values['input']+values['bias'];b=h@values['recurrent']
        z=sigmoid(a[:,:hidden]+b[:,:hidden]);r=sigmoid(a[:,hidden:2*hidden]+b[:,hidden:2*hidden])
        g=np.tanh(a[:,2*hidden:]+r*b[:,2*hidden:])
        new=(1-z)*h+z*g
        if cache:steps.append((token,mask,x,h,z,r,g,b))
        h=mask*new+(1-mask)*h
    y=np.tanh(h@values['output']+values['output_bias'][0]);score=cap*y
    return (score,(h,y,steps)) if cache else score


def loss_gradient(values,positive,negative,offset,weights,cap=2,l2=0):
    count=len(positive);ids=np.concatenate((positive,negative))
    score,(h,y,steps)=forward(values,ids,cap,True)
    gap=offset+score[:count]-score[count:]
    loss=np.mean(weights*np.logaddexp(0,-gap))
    d=-weights*sigmoid(-gap)/count
    ds=np.concatenate((d,-d))*cap*(1-y*y)
    grad={k:np.zeros_like(v) for k,v in values.items()}
    grad['output']=h.T@ds;grad['output_bias'][0]=ds.sum()
    dh=ds[:,None]*values['output'][None,:];hidden=h.shape[1]
    for token,mask,x,previous,z,r,g,b in reversed(steps):
        active=dh*mask;old=dh*(1-mask)+active*(1-z)
        dg=active*z*(1-g*g);dz=active*(g-previous)*z*(1-z)
        dr=dg*b[:,2*hidden:]*r*(1-r)
        da=np.concatenate((dz,dr,dg),axis=1)
        db=np.concatenate((dz,dr,dg*r),axis=1)
        grad['input']+=x.T@da;grad['recurrent']+=previous.T@db;grad['bias']+=da.sum(axis=0)
        np.add.at(grad['embedding'],token,da@values['input'].T)
        dh=old+db@values['recurrent'].T
    grad['embedding'][0]=0
    if l2:
        for k in ('embedding','input','recurrent','output'):
            loss+=.5*l2*np.sum(values[k]*values[k]);grad[k]+=l2*values[k]
        grad['embedding'][0]=0
    return float(loss),grad


def binary(values,characters,strength=1,cap=2):
    dimension=values['embedding'].shape[1];hidden=values['output'].size
    if values['embedding'].shape[0]!=len(characters)+3:raise ValueError('Vocabulary/embedding mismatch')
    header=struct.pack('>IIIIIIff',MAGIC,dimension,hidden,len(characters)+3,12,48,cap,strength)
    header+=b''.join(struct.pack('>I',ord(c)) for c in characters)
    return header+b''.join(np.asarray(values[k],dtype='>f4').tobytes() for k in NAMES)


def save(path,values,characters,strength):
    Path(path).write_bytes(base64.encodebytes(gzip.compress(binary(values,characters,strength),mtime=0)))


def read(path):
    raw=gzip.decompress(base64.b64decode(Path(path).read_bytes()))
    magic,dimension,hidden,size,context,maximum,cap,strength=struct.unpack_from('>IIIIIIff',raw)
    if magic!=MAGIC or context!=12 or maximum!=48:raise ValueError('Unsupported GRU model')
    characters=[chr(struct.unpack_from('>I',raw,32+4*i)[0]) for i in range(size-3)]
    offset=32+4*(size-3);values={}
    shapes=[(size,dimension),(dimension,3*hidden),(hidden,3*hidden),(3*hidden,),(hidden,),(1,)]
    for k,shape in zip(NAMES,shapes):
        count=int(np.prod(shape));values[k]=np.frombuffer(raw,dtype='>f4',count=count,offset=offset).astype(np.float32).reshape(shape);offset+=4*count
    if offset!=len(raw):raise ValueError('Unexpected model bytes')
    return values,characters,cap,strength
