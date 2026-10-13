#!/usr/bin/env python3
"""Compare every observed training-prefix feature vector and serialized correction with Java."""
import argparse
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
from prefix_features import features,encode
from train_phrase_model import ROOT

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class PrefixParity {
 public static void main(String[] args)throws Exception {
  PrefixRanker model=PrefixRanker.load(Files.newInputStream(Path.of(args[0])));
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);List<String> hints=f[2].isEmpty()?Collections.emptyList():Arrays.asList(f[2].split("\\|"));
    List<String> values=new ArrayList<>();
    for(Map.Entry<String,Integer> e:new TreeMap<>(PrefixRanker.features(f[0],f[1],hints)).entrySet())values.add(e.getKey()+"="+e.getValue());
    out.write(String.join(";",values)+"\t"+Double.toHexString(model.correction(f[0],f[1],hints))+"\n");
   }
  }
 }
}
'''

def verify(pairs,weights_path):
    weights=json.loads(weights_path.read_text());weights={k:struct.unpack('>f',struct.pack('>f',v))[0] for k,v in weights.items()}
    cases={('', '你交咗', '份報告|同事'),('你交，','咗',''),('𠮩','𠹌','𠮩𠹌'),('abc你','交咗','份報告')}
    for line in pairs.read_text().splitlines():
        f=line.split('\t')
        for text in f[5:7]:cases.add((f[1],text,f[8]))
    cases=sorted(cases)
    with tempfile.TemporaryDirectory(prefix='prefix-parity-') as directory:
        work=Path(directory);(work/'model.b64').write_bytes(encode(weights,1.5));java=work/'PrefixParity.java';java.write_text(DRIVER)
        (work/'cases.tsv').write_text(''.join('\t'.join(c)+'\n' for c in cases))
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(ROOT/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
        subprocess.run(['java','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.PrefixParity',str(work/'model.b64'),str(work/'cases.tsv'),str(work/'out.tsv')],check=True)
        rows=(work/'out.tsv').read_text().splitlines();assert len(rows)==len(cases)
        for case,row in zip(cases,rows):
            context,text,hints=case;vector=features(context,text,hints.split('|') if hints else [])
            expected=';'.join(f'{k}={v}' for k,v in sorted(vector.items()));actual,score=row.split('\t')
            if expected!=actual:raise AssertionError(('Feature mismatch',case,expected,actual))
            total=sum(weights.get(k,0)*v for k,v in vector.items());correction=1.5*max(-2,min(2,total))
            if not math.isclose(correction,float.fromhex(score),abs_tol=1e-12):raise AssertionError(('Score mismatch',case,correction,score))
    print(json.dumps({'feature_vectors':len(cases),'serialized_corrections':len(cases),'parity':True}))
    return len(cases)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pairs',type=Path);p.add_argument('weights',type=Path)
    a=p.parse_args();verify(a.pairs,a.weights)
