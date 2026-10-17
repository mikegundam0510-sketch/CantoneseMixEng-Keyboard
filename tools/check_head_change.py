#!/usr/bin/env python3
"""Check fitted numerical parity and enabled repair/protection in real decoding."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy.special import expit

from prepare_sentence_pretrain import write
from run_head_change import model,DATA,ROOT


def check(stage,cache,output):
    fitted=model();output.mkdir(parents=True,exist_ok=True)
    mean,scale,beta=(np.asarray(fitted[k]) for k in ('mean','scale','weights'))
    rows=[]
    for shard in range(4):
        values=(cache/f'features-{shard}.tsv').read_text().splitlines()
        for at in np.linspace(0,len(values)-1,20,dtype=int):
            vector=np.array([float.fromhex(v) for v in values[at].split('\t')[4].split('|')])
            probability=expit(((vector-mean)/scale)@beta)
            rows.append('|'.join(float(v).hex() for v in vector)+'\t'+float(probability).hex())
    parity=output/'probability-parity.tsv';parity.write_text(''.join(r+'\n' for r in rows))
    classes=stage/'classes'
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(classes),'-d',str(classes),str(ROOT/'tools/HeadChangeGateCheck.java')],check=True)
    r=subprocess.run(['java','-cp',str(classes),'hk.cantonesemixeng.keyboard.HeadChangeGateCheck',str(DATA/'model/head_change.b64'),str(parity)],capture_output=True,text=True,check=True)
    (output/'numeric-check.txt').write_text(r.stdout)
    source=(ROOT/'tools/VisibleRerankIntegrationCheck.java').read_text().replace('class VisibleRerankIntegrationCheck','class HeadChangeIntegrationCheck')
    anchor='    public static void main(String[] args)throws Exception {'
    source=source.replace(anchor,'''    static HeadChangeGate gate(double intercept)throws Exception {
        return HeadChangeGate.load(model(out->{
            out.writeInt(0x48434731);out.writeInt(20);out.writeDouble(.75);
            for(int a=0;a<3;a++)for(int i=0;i<20;i++)out.writeDouble(a==1?1:a==2&&i==0?intercept:0);
        }));
    }
'''+anchor)
    anchor='null,null,sr,null,null,nn);'
    if source.count(anchor)!=1:raise ValueError('Controlled model constructor changed')
    source=source.replace(anchor,'null,null,sr,null,null,nn,gate(20));')
    anchor='        for(String s:b)if(d.matchQuickCodes'
    source=source.replace(anchor,'''        QuickDecoder protectedDecoder=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,sr,null,null,nn,gate(-20));
        if(!protectedDecoder.decode("aabb",(c,w)->0).get(0).equals(a.get(0)))throw new AssertionError("Enabled protection disconnected");
        QuickDecoder missingGate=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,sr,null,null,nn);
        if(!missingGate.decode("aabb",(c,w)->0).equals(a))throw new AssertionError("Missing-gate constructor changed parent order");
'''+anchor)
    p=stage/'HeadChangeIntegrationCheck.java';p.write_text(source)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-cp',str(classes),'-d',str(classes),str(p)],check=True)
    r=subprocess.run(['java','-cp',str(classes),'hk.cantonesemixeng.keyboard.HeadChangeIntegrationCheck'],capture_output=True,text=True,check=True)
    (output/'integration-check.txt').write_text(r.stdout)
    write(output/'preflight.json',dict(fitted_probability_parity=80,tolerance=1e-11,
        controlled_repair=True,controlled_protection=True,tail_order_preserved=True,
        null_gate_full_parent_order=True,nonfinite_rejection=True,malformed_rejected=8,
        original_sets=True,positive_negative_personal_context=True,familiar_characters_active=True,mixed_translation_unchanged=True))
    print('fitted_parity80=true enabled_repair_protection=true personal_mixed_fallback=true')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',type=Path);p.add_argument('cache',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();check(a.stage,a.cache,a.output)
