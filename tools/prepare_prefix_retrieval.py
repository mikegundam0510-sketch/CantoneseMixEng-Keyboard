#!/usr/bin/env python3
"""Freeze another source-separated reserve; dictionary examples are evaluation only."""
import argparse
from pathlib import Path
from prepare_search_recovery import prepare as prepare_reserve
from train_phrase_model import ROOT

DATA=ROOT/'tools/data/prefix_retrieval'
BASELINE='d8575595b689916d8649e71e1a365224392683a9'
PREVIOUS=('tools/data/search_recovery/validation-source.jsonl',
          'tools/data/search_recovery/heldout-source.jsonl')

def prepare(dictionary,hk,treebank,output=DATA):
    return prepare_reserve(dictionary,hk,treebank,output,baseline=BASELINE,
                           additional_sources=PREVIOUS,label='retrieval')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dictionary','hk','treebank'):p.add_argument(name,type=Path)
    p.add_argument('--output',type=Path,default=DATA);a=p.parse_args()
    prepare(a.dictionary,a.hk,a.treebank,a.output)
