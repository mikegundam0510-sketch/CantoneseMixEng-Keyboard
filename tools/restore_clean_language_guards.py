#!/usr/bin/env python3
"""Restore the pinned, previously observed guard references for reproduction."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def restore():
    protocol=json.loads((ROOT/'tools/data/clean_language_models/protocol.json').read_text())
    names=('guard-cases3893.tsv','baseline3893.tsv')
    with zipfile.ZipFile(ROOT/'tools/reports/clean-language-models-2026-10-16/guard-reference.zip') as archive:
        if set(archive.namelist())!=set(names): raise ValueError('Unexpected guard archive members')
        for name in names:
            relative='.native/joint-ranking-20261015/'+name
            payload=archive.read(name)
            if hashlib.sha256(payload).hexdigest()!=protocol['evaluation_sha256'][relative]:
                raise ValueError('Guard reference changed: '+name)
            target=ROOT/relative
            if target.exists():
                if target.read_bytes()!=payload: raise ValueError('Preserve different existing guard cache: '+name)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(payload)
    print('Verified/restored two pinned guard references; no decoder or reserve500 run.')


if __name__=='__main__':restore()
