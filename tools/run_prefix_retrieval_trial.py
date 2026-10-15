#!/usr/bin/env python3
"""Reproduce a rejected retrieval trial in a separate archived tree, never the app."""
import argparse
from pathlib import Path
import subprocess
from native_phrase_relations import build,run
from prepare_prefix_retrieval import DATA,BASELINE

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trial',choices=('broad','lexical'))
    for name in ('cases','output','work'):p.add_argument(name,type=Path)
    a=p.parse_args();build(a.work,BASELINE,original=True)
    subprocess.run(['patch','-p1','-d',str(a.work),'-i',str((DATA/(a.trial+'-rejected.patch')).resolve())],check=True)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(a.work/'app/src/main/java'),
                    '-d',str(a.work/'classes'),str(a.work/'RelationEvaluation.java')],check=True)
    run(a.work,a.cases,a.output)
