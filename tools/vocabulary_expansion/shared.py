"""Isolated vocabulary experiment; predecessor sources and assets stay immutable."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
BASELINE='d7dec75d3f74525f2fc9a3070c65fff8bd43c9d4'
DATA=ROOT/'tools/data/vocabulary_expansion'
WORK=ROOT/'.native/vocabulary-expansion-20261018'
REPORTS=ROOT/'tools/reports/vocabulary-expansion-2026-10-18'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as out:out.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def verify():
    p=json.loads((DATA/'protocol.json').read_text())
    if sha(DATA/'protocol.json')!=json.loads((DATA/'seal.json').read_text())['protocol_sha256']:
        raise ValueError('Vocabulary protocol changed')
    for name,wanted in p['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Frozen source/input changed: '+name)
    return p
