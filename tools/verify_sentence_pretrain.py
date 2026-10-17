#!/usr/bin/env python3
"""Actual Java/Python language score parity and bounded malformed-file rejection."""
import argparse
import base64
import gzip
from pathlib import Path
import struct
import subprocess
from sentence_features import han
from sentence_language_model import read, paths, batch, forward

JAVA = r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;
public final class SentenceLanguageScoreCheck {
 public static void main(String[] args)throws Exception {
  SentenceLanguageRanker m=SentenceLanguageRanker.load(Files.newInputStream(Path.of(args[0])));
  int rows=0,rejected=0;
  for(String line:Files.readAllLines(Path.of(args[1]))) {
   String[] f=line.split("\t",-1); double expected=Double.valueOf(f[2]),actual=m.score(f[0],f[1]);
   if(!Double.isFinite(actual)||Math.abs(actual-expected)>3e-5||Math.abs(actual)>1.000001)
    throw new AssertionError("Sentence language score mismatch: "+line+" actual="+actual);
   rows++;
  }
  for(Path p:Files.newDirectoryStream(Path.of(args[2]))) {
   boolean bad=false;try{SentenceLanguageRanker.load(Files.newInputStream(p));}catch(IOException e){bad=true;}
   if(!bad)throw new AssertionError("Malformed sentence model accepted: "+p);rejected++;
  }
  if(m.arrayBytes()>2*1024*1024)throw new AssertionError("Sentence model memory bound");
  System.out.printf("score_rows=%d rejected_models=%d array_bytes=%d%n",rows,rejected,m.arrayBytes());
 }
}
'''


def verify(work, output):
    model = work/'app/src/main/assets/sentence_language.b64'
    values, chars, children, prior, strength = read(model)
    vocabulary={c:i+3 for i,c in enumerate(chars)};tree=paths(children,len(prior))
    texts=['你交咗功課畀老細未','想你繼續完善下連續打字','我唔使返工','我想返工','我唔想返工',
           '佢做咗未','佢未做','係我搬咗屋','香港','𠮩𠹌','𠀀𠀁','abc你好','香港。你好','','甲'*49,'甲'*48]
    cases=[]
    for context in ('','我問你','甲'*20,'中文abc香港','甲乙丙丁戊己庚辛壬癸甲乙'):
        for text in texts:
            score=float(strength*forward(values,*batch([dict(context=context,text=text)],vocabulary),tree,prior)[0][0]) if text and len(text)<=48 and all(han(c) for c in text) else 0
            cases.append((context,text,score))
    casefile=work/'language-score-cases.tsv'
    casefile.write_text(''.join('\t'.join((c,t,float(s).hex()))+'\n' for c,t,s in cases))
    raw=gzip.decompress(base64.b64decode(model.read_bytes()));bad=work/'malformed-sentence-models';bad.mkdir()
    size=struct.unpack_from('>I',raw,12)[0];tree_at=32+4*(size-3);prior_at=tree_at+8*(size-3)
    variants=[]
    for at,fmt,value in [(0,'>I',0),(4,'>I',0),(8,'>I',33),(12,'>I',9000),(24,'>f',float('nan')),
                         (28,'>f',1.1),(tree_at,'>i',0),(tree_at,'>i',-1),
                         (tree_at,'>i',2**30),(prior_at+4,'>f',float('nan')),(prior_at+4,'>f',.1)]:
        data=bytearray(raw);struct.pack_into(fmt,data,at,value);variants.append(data)
    data=bytearray(raw);data[36:40]=data[32:36];variants.append(data)
    data=bytearray(raw);struct.pack_into('>f',data,len(raw)-4,float('nan'));variants.append(data)
    variants.extend([raw+b'bad',raw[:-4]])
    for i,data in enumerate(variants):(bad/(str(i)+'.b64')).write_bytes(base64.encodebytes(gzip.compress(data,mtime=0)))
    java=work/'SentenceLanguageScoreCheck.java';java.write_text(JAVA)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-d',str(work/'classes'),str(java)],check=True)
    result=subprocess.check_output(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.SentenceLanguageScoreCheck',str(model),str(casefile),str(bad)],text=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(result);print(result,end='')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();verify(a.work,a.output)
