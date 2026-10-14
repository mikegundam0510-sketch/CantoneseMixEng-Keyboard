#!/usr/bin/env python3
"""Check all observed training relation vectors and guarded scores against Java."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile
from evaluate_phrase_relations import KINDS
from phrase_relation_features import features,encode
from train_phrase_model import ROOT

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class RelationParity {
 public static void main(String[] args)throws Exception {
  PhraseRelationRanker m=PhraseRelationRanker.load(Files.newInputStream(Path.of(args[0])));
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);List<String> vec=new ArrayList<>();
    for(Map.Entry<String,Integer> e:new TreeMap<>(m.features(f[0],f[1])).entrySet())vec.add(e.getKey()+"="+e.getValue());
    PhraseRelationRanker.Evidence value=m.evidence(f[0],f[1]),reference=m.evidence(f[0],f[2]);
    double lift=value.supportedOver(reference)?m.correction(value.raw,reference.raw):0;
    out.write(String.join(";",vec)+"\t"+Double.toHexString(value.raw)+"\t"+Double.toHexString(lift)+"\t"+m.trustedPromotion(value,reference,lift)+"\n");
   }
  }
 }
}
'''

def verify(pairs,weights_path,lexicon_path,output):
    weights=json.loads(weights_path.read_text());lexicon=json.loads(lexicon_path.read_text())
    cases={('','你交咗功課畀老細未','係交咗功課界老細字'),('你交，','咗功課',''),('abc你','食花生',''),
        ('','我食錢包',''),('','我用司機',''),('我用','手機',''),('𠮷','哥食飯',''),('','你'*50,''),
        ('你交'+('好'*12),'咗功課',''),('我食','pizza你食飯','')}
    for line in pairs.read_text().splitlines():
        f=line.split('\t')
        for text in f[3:5]:cases.add((f[1],text,f[3]))
    cases=sorted(cases)
    with tempfile.TemporaryDirectory(prefix='relation-parity-') as directory:
        work=Path(directory);(work/'model.b64').write_bytes(encode(lexicon,weights,1.5))
        (work/'cases.tsv').write_text(''.join('\t'.join(c)+'\n' for c in cases));java=work/'RelationParity.java';java.write_text(DRIVER)
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(ROOT/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
        subprocess.run(['java','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RelationParity',str(work/'model.b64'),str(work/'cases.tsv'),str(work/'out.tsv')],check=True)
        rows=(work/'out.tsv').read_text().splitlines()
        if len(rows)!=len(cases):raise ValueError('Incomplete native parity')
        def evidence(context,text):
            fs=features(context,text,lexicon);score=sum(n*weights.get(k,0) for k,n in fs.items())
            pos={k for k in fs if k.split('|',1)[0] in KINDS and weights.get(k,0)>0}
            kinds={KINDS[k.split('|',1)[0]] for k in pos}
            def unknown(k):
                p=k.split('|');return p[0]=='G' and 'O' in p[1] or p[0]=='B' and 'O' in p[1:] or p[0]=='Q' and 'O' in p[2]
            neg={k for k in fs if weights.get(k,0)<-.1 and not unknown(k)}
            return fs,score,pos,kinds,neg
        max_error=0
        for (context,text,ref),line in zip(cases,rows):
            vec,raw,lift,trusted=line.split('\t');actual={}
            for item in vec.split(';') if vec else []:
                key,n=item.rsplit('=',1);actual[key]=int(n)
            fs,total,pos,kinds,neg=evidence(context,text);_,reference,rpos,rkinds,rneg=evidence(context,ref)
            correction=max(0,1.5*max(-2,min(2,total-reference))-.1) if len(kinds)>=2 and pos-rpos else 0
            if actual!=fs:raise AssertionError(('Feature mismatch',context,text,dict(fs),actual))
            max_error=max(max_error,abs(total-float.fromhex(raw)),abs(correction-float.fromhex(lift)))
            if not math.isclose(total,float.fromhex(raw),abs_tol=1e-11) or not math.isclose(correction,float.fromhex(lift),abs_tol=1e-11):
                raise AssertionError(('Score mismatch',context,text,total,raw,correction,lift))
            expected=correction>=.5 and len(kinds)>=2 and bool(pos-rpos) and (
                bool(rneg-neg) or len(kinds-{'negation'})>len(rkinds-{'negation'}))
            if str(expected).lower()!=trusted:raise AssertionError(('Guard mismatch',context,text,ref))
    report=dict(feature_vectors=len(cases),serialized_scores=len(cases),guarded_lifts=len(cases),max_error=max_error,parity=True)
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('pairs','weights','lexicon','output'):p.add_argument(name,type=Path)
    a=p.parse_args();verify(a.pairs,a.weights,a.lexicon,a.output)
