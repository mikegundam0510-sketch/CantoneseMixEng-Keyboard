"""Search-time features: trailing12 Han characters and actual remaining-code hints."""
import base64
from collections import Counter
import gzip
import json
import math
import struct
from sentence_features import features as sentence_features, han, role

def features(context, text, hints=()):
    history=''
    for c in context+text:history=(history+c)[-12:] if han(c) else ''
    result=Counter({k:v for k,v in sentence_features('',history).items() if k[:2] in ('W|','K|','R|','E|')})
    for index,hint in enumerate(hints[:6]):
        head=''
        for c in hint:
            if not han(c) or len(head)==2:break
            head+=c
        tier='0' if index<2 else '1'
        for a in range(1,min(2,len(history))+1):
            for b in range(1,len(head)+1):result[f'B|{tier}|{history[-a:]}|{head[:b]}']+=1
        if history and head:result[f'C|{tier}|{role(history[-1])}|{role(head[0])}']+=1
    return Counter({k:min(2,v) for k,v in result.items()})

def encode(weights,strength=1):
    if not math.isfinite(strength) or not 0<=strength<=2 or len(weights)>16000:raise ValueError('Invalid prefix bounds')
    out=bytearray(struct.pack('>IIff',0x50524b31,len(weights),strength,2))
    for key,value in sorted(weights.items()):
        raw=key.encode()
        if not 3<=len(raw)<=64 or not math.isfinite(value) or abs(value)>1.5:raise ValueError('Invalid prefix feature')
        out.extend(struct.pack('>H',len(raw)));out.extend(raw);out.extend(struct.pack('>f',value))
    return base64.encodebytes(gzip.compress(bytes(out),mtime=0))

def metadata(context,hints):return json.dumps({'context':context,'hints':hints},ensure_ascii=False,sort_keys=True)
