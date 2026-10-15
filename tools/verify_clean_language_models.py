#!/usr/bin/env python3
"""Compare binary-model scores with Java, including reset/cache/token invariants."""
import argparse
import base64
import gzip
import json
import math
from pathlib import Path
import struct
import subprocess

from train_language_model import key
from sentence_features import han


def payload(path):
    return gzip.decompress(base64.b64decode(path.read_bytes()))


def read_character(path):
    raw = payload(path)
    magic, order, count, unknown = struct.unpack_from('>IIIf',raw)
    if magic!=0x4b4c4d32 or order!=5 or len(raw)!=16+16*count or not 0<unknown<1:
        raise ValueError('Invalid character header')
    rows = [struct.unpack_from('>qff',raw,16+16*i) for i in range(count)]
    if any(not all(math.isfinite(x) and 0<=x<=1 for x in r[1:]) for r in rows):
        raise ValueError('Invalid character probabilities')
    if any(a[0]>=b[0] for a,b in zip(rows,rows[1:])): raise ValueError('Unsorted character hashes')
    return unknown, {h:(p,b) for h,p,b in rows}


def character_score(model, preceding, text):
    unknown, rows = model
    history = ''
    for c in preceding:
        history = (history+c)[-4:] if han(c) else ''
    result = 0
    for c in text:
        if not han(c): history='';continue
        window=history+c
        p=rows.get(key(c),(unknown,1))[0]
        for n in range(2,min(5,len(window))+1):
            gram=window[-n:]; context=rows.get(key(gram[:-1]))
            if context is not None: p=rows.get(key(gram),(0,1))[0]+context[1]*p
        result+=math.log(max(unknown,p)); history=window[-4:]
    return result


def read_word(path):
    raw=payload(path)
    magic,length,nodes,edges,strength=struct.unpack_from('>IIIIf',raw)
    if magic!=0x574c4d31 or not 2<=length<=12 or edges!=nodes-1 or len(raw)!=20+12*nodes+8*edges:
        raise ValueError('Invalid word header')
    records=[struct.unpack_from('>IIf',raw,20+12*i) for i in range(nodes)]
    links=[struct.unpack_from('>II',raw,20+12*nodes+8*i) for i in range(edges)]
    relations={}
    def visit(node,reverse):
        start,count,value=records[node]
        if value: relations[''.join(reversed(reverse))]=value
        for c,target in links[start:start+count]: visit(target,reverse+chr(c))
    visit(0,'')
    return length,strength,relations


def word_score(model, preceding, text):
    length,strength,relations=model
    history=''
    for c in preceding: history=(history+c)[-(length-1):] if han(c) else ''
    result=0
    for c in text:
        if not han(c):history='';continue
        window=history+c
        result+=strength*max((relations.get(window[-n:],0) for n in range(1,min(length,len(window))+1)),default=0)
        history=window[-(length-1):]
    return result


JAVA = r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class CleanLanguageModelCheck {
 public static void main(String[] args)throws Exception {
  Path assets=Path.of(args[0]);
  OfflineLanguageModel c=OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64")));
  PhraseLanguageModel w=PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64")));
  DictionaryEngine d=new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
    Files.newBufferedReader(assets.resolve("english.txt")),Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
  QuickDecoder with=new QuickDecoder(d,new StringReader(""),null,null,c,w,null);
  QuickDecoder without=new QuickDecoder(d,new StringReader(""),null,null,c,null,null);
  int rows=0,splits=0;
  for(String line:Files.readAllLines(Path.of(args[1]))) {
   String[] f=line.split("\t",-1);String context=f[0],text=f[1];
   double cs=c.score(context,text),ws=w.score(context,text);
   if(Math.abs(cs-Double.valueOf(f[2]))>1e-9||Math.abs(ws-Double.valueOf(f[3]))>1e-9)
    throw new AssertionError("Python/Java mismatch: "+line);
   if(Math.abs(c.score(context,text,new HashMap<>())-cs)>1e-9)throw new AssertionError("Cache mismatch");
   if(Math.abs(with.languageScore(context,text)-without.languageScore(context,text)-ws)>1e-9)
    throw new AssertionError("Word evidence missing/double charged");
   for(int i=0;i<=text.codePointCount(0,text.length());i++) {
    int at=text.offsetByCodePoints(0,i);String left=text.substring(0,at),right=text.substring(at);
    if(Math.abs(cs-c.score(context,left)-c.score(context+left,right))>1e-9
       ||Math.abs(ws-w.score(context,left)-w.score(context+left,right))>1e-9)
     throw new AssertionError("Token split mismatch");
    splits++;
   }
   rows++;
  }
  if(c.arrayBytes()>20*1024*1024||w.arrayBytes()>1024*1024)throw new AssertionError("Model memory budget");
  System.out.printf("rows=%d token_splits=%d character_array_bytes=%d word_array_bytes=%d%n",rows,splits,c.arrayBytes(),w.arrayBytes());
 }
}
'''


def verify(work, output):
    assets=work/'app/src/main/assets'
    c=read_character(assets/'language_model.b64');w=read_word(assets/'phrase_model.b64')
    # TRAIN relation samples ensure checks include nonzero word evidence.
    sampled=sorted(w[2],key=lambda t:(-w[2][t],t))[:12]
    texts=['你交咗功課畀老細未','想你繼續完善下連續打字','我唔使返工','今日真係好攰',
           '𠮩𠹌香港','abc你好','香港。你好','香港Mr Bean你好','香港○你好','𠀀𠀁','']+sampled
    rows=[(context,text,character_score(c,context,text),word_score(w,context,text))
          for context in ('','我問你','香港，','𠮩𠹌香港') for text in texts]
    cases=work/'clean-model-score-cases.tsv'
    cases.write_text(''.join('\t'.join((a,b,float(x).hex(),float(y).hex()))+'\n' for a,b,x,y in rows))
    java=work/'CleanLanguageModelCheck.java';java.write_text(JAVA)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-sourcepath',str(work/'app/src/main/java'),
                    '-d',str(work/'classes'),str(java)],check=True)
    value=subprocess.check_output(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.CleanLanguageModelCheck',
        str(assets),str(cases)],text=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(value);print(value,end='')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();verify(a.work,a.output)
