#!/usr/bin/env python3
"""Enable bounded evidence-gated PRR3 head swaps without changing fitted weights."""
import argparse
import base64
import gzip
from pathlib import Path
import struct
from phrase_relation_features import encode as validate_model


def encode(source,margin,lift,weights=None,strength=0):
    disabled=margin==0 and lift==0
    if not disabled and (not .5<=margin<=1 or not .5<=lift<=1):raise ValueError('Invalid head promotion thresholds')
    body=gzip.decompress(base64.b64decode(source))
    if struct.unpack_from('>I',body)[0]!=0x50525232:raise ValueError('PRR2 source required')
    weights={} if weights is None else weights
    if disabled and (weights or strength!=0):raise ValueError('Disabled head model has weights')
    if not 0<=strength<=1.5:raise ValueError('Invalid head strength')
    validate_model({},weights,strength)
    extra=struct.pack('>Iff',len(weights),strength,2)
    for key,value in sorted(weights.items()):
        key=key.encode();extra+=struct.pack('>H',len(key))+key+struct.pack('>f',value)
    payload=struct.pack('>I',0x50525233)+body[4:20]+struct.pack('>ff',margin,lift)+body[20:]+extra
    return base64.encodebytes(gzip.compress(payload,mtime=0))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--margin',required=True,type=float);p.add_argument('--lift',required=True,type=float)
    p.add_argument('--weights',type=Path);p.add_argument('--strength',type=float,default=0)
    a=p.parse_args()
    import json
    a.output.write_bytes(encode(a.source.read_bytes(),a.margin,a.lift,json.loads(a.weights.read_text()) if a.weights else None,a.strength))
