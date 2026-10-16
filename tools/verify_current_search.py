#!/usr/bin/env python3
"""Verify current-search Java scores, prefix splits and actual score integration."""
import argparse
import json
from pathlib import Path
import subprocess

from train_current_search import features
from verify_joint_score import JAVA


def verify(work,weights,strength,output,maximum=5):
    fitted=json.loads(weights.read_text())
    texts=['你交咗功課畀老細未','想你繼續完善下連續打字','我唔使返工','今日真係好攰',
        '聽日再同你講','𠮩𠹌香港','abc你好','香港。你好','我'*30]
    texts+=sorted((k for k in fitted if len(k)==maximum),key=lambda k:(-abs(fitted[k]),k))[:12]
    rows=[(context,text,strength*sum(fitted.get(k,0)*v for k,v in features(context,text,maximum).items()))
        for context in ('','我問你','香港，','甲乙丙丁戊己庚辛壬癸甲乙') for text in texts]
    cases=work/'current-score-cases.tsv'
    cases.write_text(''.join('\t'.join((c,t,float(s).hex()))+'\n' for c,t,s in rows))
    java=work/'JointScoreCheck.java'
    java.write_text(JAVA.replace('CandidateRanker.load(Files.newInputStream(assets.resolve("joint_ranker.b64")))',
        'CandidateRanker.loadWords(Files.newInputStream(assets.resolve("joint_ranker.b64")))')
        .replace('joint.arrayBytes()>1024*1024','joint.arrayBytes()>3*1024*1024'))
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-sourcepath',str(work/'app/src/main/java'),
        '-d',str(work/'classes'),str(java)],check=True)
    result=subprocess.check_output(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.JointScoreCheck',
        str(work/'app/src/main/assets'),str(cases)],text=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(result);print(result,end='')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','weights','output'):p.add_argument(name,type=Path)
    p.add_argument('--strength',type=float,required=True);p.add_argument('--maximum',type=int,choices=(3,5),default=5)
    a=p.parse_args();verify(a.work,a.weights,a.strength,a.output,a.maximum)
