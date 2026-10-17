"""Verify frozen inference bytes and merge complete ordinary three-shard runs."""
import argparse
import json
from experiment import ROOT,DATA,WORK,REPORTS,frozen,digest


def check(arm):
    frozen();r=json.loads((DATA/(arm+'-freeze.json')).read_text());stage=WORK/arm
    for name,wanted in r['native_sha256'].items():
        if digest(stage/name)!=wanted:raise ValueError('Frozen native inference changed: '+arm+'/'+name)
    if r['protocol_sha256']!=digest(DATA/'protocol.json'):raise ValueError('Wrong protocol freeze')
    if arm=='trained':
        if r['model_sha256']!=digest(DATA/'model/prefix.b64'):raise ValueError('Changed trained checkpoint')
        for name,wanted in r['training_sha256'].items():
            if digest(ROOT/name)!=wanted:raise ValueError('Changed training evidence')


def merge(arm):
    check(arm)
    inputs=(ROOT/'tools/data/context_search/calibration1450.tsv').read_text().splitlines();rows=[None]*len(inputs)
    for i in range(3):
        assert (WORK/f'calibration-{i}.tsv').read_text().splitlines()==inputs[i::3]
        shard=(WORK/f'{arm}-{i}.tsv').read_text().splitlines();assert len(shard)==len(inputs[i::3])
        for n,line in enumerate(shard):
            assert '\t'.join(line.split('\t')[:4])==inputs[i+n*3]
            rows[i+n*3]=line
    output=REPORTS/(arm+'-1450.tsv')
    if output.exists():raise ValueError('Do not overwrite completed evaluation')
    output.write_text(''.join(r+'\n' for r in rows));print(arm,'complete1450=true')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('arm',choices=['language','trained']);a=p.parse_args();merge(a.arm)
