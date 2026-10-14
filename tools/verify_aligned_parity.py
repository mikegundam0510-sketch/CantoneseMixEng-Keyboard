#!/usr/bin/env python3
"""Verify PRR2 exported float scores and signed clipped corrections against Java."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile
from phrase_relation_features import features
from train_aligned_relations import encode_aligned,clipped
from train_phrase_model import ROOT

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class AlignedParity {
 public static void main(String[] args)throws Exception {
  PhraseRelationRanker m=PhraseRelationRanker.load(Files.newInputStream(Path.of(args[0])));
  if(!m.aligned())throw new AssertionError("PRR2 mode");
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);List<String> vector=new ArrayList<>();
    for(Map.Entry<String,Integer> e:new TreeMap<>(m.features(f[0],f[1])).entrySet())vector.add(e.getKey()+"="+e.getValue());
    double raw=m.rawScore(f[0],f[1]),reference=m.rawScore(f[0],f[2]);
    if(raw!=m.evidence(f[0],f[1]).raw)throw new AssertionError("Optimized raw score");
    out.write(String.join(";",vector)+"\t"+Double.toHexString(raw)+"\t"+Double.toHexString(m.alignedCorrection(raw,reference))+"\n");
   }
  }
 }
}
'''

def verify(model,output):
    weights=json.loads((model/'weights.json').read_text())
    lexicon=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text());cases=set()
    for line in (model/'pairs.tsv').read_text().splitlines():
        f=line.split('\t')
        for text in f[3:5]:cases.add((f[1],text,f[5]))
    cases.update([('你交，','咗功課',''),('abc你','食花生',''),('𠮷','哥食飯',''),('','你'*50,''),('我食','pizza你食飯','')])
    cases=sorted(cases)
    with tempfile.TemporaryDirectory(prefix='aligned-parity-') as directory:
        work=Path(directory);(work/'model.b64').write_bytes(encode_aligned(lexicon,weights,1.5))
        (work/'cases.tsv').write_text(''.join('\t'.join(r)+'\n' for r in cases));java=work/'AlignedParity.java';java.write_text(DRIVER)
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(ROOT/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
        subprocess.run(['java','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.AlignedParity',str(work/'model.b64'),str(work/'cases.tsv'),str(work/'out.tsv')],check=True)
        rows=(work/'out.tsv').read_text().splitlines();assert len(rows)==len(cases);error=0
        for (context,text,reference),row in zip(cases,rows):
            vector,actual,correction=row.split('\t');parsed={}
            for item in vector.split(';') if vector else []:
                key,n=item.rsplit('=',1);parsed[key]=int(n)
            fs=features(context,text,lexicon);assert parsed==fs
            raw=sum(n*weights.get(k,0) for k,n in fs.items())
            ref=sum(n*weights.get(k,0) for k,n in features(context,reference,lexicon).items())
            delta=1.5*clipped(raw-ref)
            error=max(error,abs(raw-float.fromhex(actual)),abs(delta-float.fromhex(correction)))
            assert math.isclose(raw,float.fromhex(actual),abs_tol=1e-11) and math.isclose(delta,float.fromhex(correction),abs_tol=1e-11)
    result=dict(cases=len(cases),feature_vectors_equal=True,maximum_error=error,raw_and_signed_clipped_parity=True)
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();verify(a.model,a.output)
