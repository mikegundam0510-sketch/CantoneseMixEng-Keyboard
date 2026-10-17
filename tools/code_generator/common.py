"""Shared fixed locations and immutable experiment inputs."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_tatoeba_corpus import digest
from prepare_sentence_pretrain import write
BASELINE='22d26b571aa5c766a7ed4e606dd193632eaab1bd'
DATA=ROOT/'tools/data/code_generator'
WORK=ROOT/'.native/code-generator-20261017'
REPORTS=ROOT/'tools/reports/code-generator-2026-10-17'


def frozen():
    p=json.loads((DATA/'protocol.json').read_text())
    if digest(DATA/'protocol.json')!=json.loads((DATA/'seal.json').read_text())['protocol_sha256']:
        raise ValueError('Generator protocol changed')
    for name,wanted in {**p['source_sha256'],**p['input_sha256']}.items():
        if digest(ROOT/name)!=wanted:raise ValueError('Frozen generator input changed: '+name)
    return p
