#!/usr/bin/env python3
"""Actual Java/Python recurrent score parity, bounds and malformed-loader checks."""
import argparse
import base64
import gzip
from pathlib import Path
import struct
import subprocess
import numpy as np

from context_gru import read,encode,padded,forward
from sentence_features import han

JAVA=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;
public class ContextGRUScoreCheck {
 public static void main(String[] args)throws Exception {
  ContextSentenceRanker m=ContextSentenceRanker.load(Files.newInputStream(Path.of(args[0])));
  int rows=0,rejected=0;
  for(String line:Files.readAllLines(Path.of(args[1]))) {
   String[] f=line.split("\t",-1);double expected=Double.valueOf(f[2]),actual=m.score(f[0],f[1]);
   if(!Double.isFinite(actual)||Math.abs(actual-expected)>3e-5||Math.abs(actual)>2.000001)
    throw new AssertionError("Recurrent score mismatch: "+line+" actual="+actual);
   rows++;
  }
  for(Path p:Files.newDirectoryStream(Path.of(args[2]))) {
   boolean bad=false;try{ContextSentenceRanker.load(Files.newInputStream(p));}catch(IOException e){bad=true;}
   if(!bad)throw new AssertionError("Malformed recurrent model accepted: "+p);rejected++;
  }
  if(m.arrayBytes()>512*1024)throw new AssertionError("Recurrent memory bound");
  System.out.printf("score_rows=%d rejected_models=%d array_bytes=%d%n",rows,rejected,m.arrayBytes());
 }
}
'''


def verify(work,output):
    model=work/'app/src/main/assets/context_gru.b64';values,chars,cap,strength=read(model);vocabulary={c:i+3 for i,c in enumerate(chars)}
    texts=['你交咗功課畀老細未','想你繼續完善下連續打字','我唔使返工','我想返工','我唔想返工','香港','𠮩𠹌','𠀀𠀁','abc你好','香港。你好','','甲'*49]
    cases=[]
    for context in ('','我問你','甲'*20,'中文abc香港','甲乙丙丁戊己庚辛壬癸甲乙'):
        for text in texts:
            value=float(strength*forward(values,padded([encode(context,text,vocabulary)]),cap)[0]) if text and len(text)<=48 and all(han(c) for c in text) else 0
            cases.append((context,text,value))
    casefile=work/'gru-score-cases.tsv';casefile.write_text(''.join('\t'.join((c,t,float(s).hex()))+'\n' for c,t,s in cases))
    raw=gzip.decompress(base64.b64decode(model.read_bytes()));bad=work/'malformed-gru';bad.mkdir(exist_ok=False)
    variants=[]
    for offset,fmt,value in ((4,'>I',0),(12,'>I',9000),(24,'>f',float('nan')),(28,'>f',float('inf'))):
        data=bytearray(raw);struct.pack_into(fmt,data,offset,value);variants.append(data)
    data=bytearray(raw);data[36:40]=data[32:36];variants.append(data)
    variants.append(raw+b'bad');variants.append(raw[:-4])
    size=struct.unpack_from('>I',raw,12)[0];data=bytearray(raw);struct.pack_into('>f',data,32+4*(size-3),float('nan'));variants.append(data)
    for i,data in enumerate(variants):(bad/(str(i)+'.b64')).write_bytes(base64.encodebytes(gzip.compress(data,mtime=0)))
    java=work/'ContextGRUScoreCheck.java';java.write_text(JAVA)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-d',str(work/'classes'),str(java)],check=True)
    result=subprocess.check_output(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.ContextGRUScoreCheck',str(model),str(casefile),str(bad)],text=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(result);print(result,end='')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();verify(a.work,a.output)
