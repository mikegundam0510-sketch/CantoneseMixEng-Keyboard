#!/usr/bin/env python3
"""Controlled tail movement, first invariance, personal priorities and mixed paths."""
import argparse
from pathlib import Path
import subprocess
from prepare_sentence_pretrain import write
from train_phrase_model import ROOT


def check(stage,output):
    output.mkdir(parents=True,exist_ok=True);classes=stage/'classes'
    p=ROOT/'tools/PinnedHeadCheck.java'
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(classes),'-d',str(classes),str(p)],check=True)
    r=subprocess.run(['java','-cp',str(classes),'hk.cantonesemixeng.keyboard.PinnedHeadCheck'],capture_output=True,text=True,check=True)
    (output/'properties.txt').write_text(r.stdout)
    text=(ROOT/'tools/VisibleRerankIntegrationCheck.java').read_text().replace('class VisibleRerankIntegrationCheck','class PinnedHeadIntegrationCheck')
    text=text.replace('丙\\taa\\n甲\\taa','丙\\taa\\n丁\\taa\\n甲\\taa')
    text=text.replace('丙\\t1000\\n甲\\t1000','丙\\t1000\\n丁\\t1000\\n甲\\t1000')
    text=text.replace("new int[]{'丙','甲','乙'}","new int[]{'丙','丁','甲','乙'}")
    text=text.replace("cp=='甲'?.009f:.01f","cp=='甲'?.009f:cp=='丙'?.02f:.01f")
    text=text.replace('!b.get(0).equals("甲乙")','!b.get(0).equals(a.get(0))||!a.get(1).equals("丁乙")||!b.get(1).equals("甲乙")')
    text=text.replace('after.decode("aabb",familiar).get(0).equals("甲乙")','after.decode("aabb",familiar).get(1).equals("甲乙")')
    text=text.replace('cold_head=甲乙','head=丙乙 tail_moved=甲乙')
    p=stage/'PinnedHeadIntegrationCheck.java';p.write_text(text)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-cp',str(classes),'-d',str(classes),str(p)],check=True)
    r=subprocess.run(['java','-cp',str(classes),'hk.cantonesemixeng.keyboard.PinnedHeadIntegrationCheck'],capture_output=True,text=True,check=True)
    (output/'integration.txt').write_text(r.stdout)
    write(output/'preflight.json',dict(randomized_displays=400,first_and_set_invariance=True,relative_tail_exact=True,
        neutral_constant_and_invalid_fallback=True,immutable_inputs=True,controlled_tail_movement=True,
        personal_positive_negative=True,familiar_characters_active=True,mixed_translation_unchanged=True))
    print('first_and_set_invariance400=true real_decode_tail_moves=true personal_mixed_fallback=true')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();check(a.stage,a.output)
