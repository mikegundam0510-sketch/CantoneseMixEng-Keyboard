#!/usr/bin/env python3
"""Check Python/Java shared scores, token splits and actual decoder integration."""
import argparse
import json
from pathlib import Path
import subprocess
from train_candidate_ranker import features

JAVA=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class JointScoreCheck {
 public static void main(String[] args)throws Exception {
  Path assets=Path.of(args[0]);CandidateRanker joint=CandidateRanker.load(Files.newInputStream(assets.resolve("joint_ranker.b64")));
  DictionaryEngine d=new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
      Files.newBufferedReader(assets.resolve("english.txt")),Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
  OfflineLanguageModel lm=OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64")));
  QuickDecoder before=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,null,null,null);
  QuickDecoder after=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,null,null,null,joint);
  int rows=0,splits=0;
  for(String line:Files.readAllLines(Path.of(args[1]))) {
   String[] f=line.split("\t",-1);double expected=Double.valueOf(f[2]);
   double value=joint.score(f[0],f[1]);
   if(Math.abs(value-expected)>1e-9)throw new AssertionError("Python/Java score mismatch: "+line);
   if(Math.abs(after.languageScore(f[0],f[1])-before.languageScore(f[0],f[1])-value)>1e-9)
       throw new AssertionError("Shared score missing or double-applied in decoder");
   for(int i=0;i<=f[1].codePointCount(0,f[1].length());i++) {
    int at=f[1].offsetByCodePoints(0,i);String left=f[1].substring(0,at),right=f[1].substring(at);
    if(Math.abs(value-joint.score(f[0],left)-joint.score(f[0]+left,right))>1e-9)throw new AssertionError("Token split changes score");
    splits++;
   }
   rows++;
  }
  if(joint.arrayBytes()>1024*1024)throw new AssertionError("Unexpected model memory");
  System.out.println("rows="+rows+" token_splits="+splits+" array_bytes="+joint.arrayBytes());
 }
}
'''

def verify(work,weights,strength,output):
    fitted=json.loads(weights.read_text())
    texts=['你交咗功課畀老細未','想你繼續完善下連續打字','我唔使返工','今日真係好攰','聽日再同你講','𠮩𠹌香港','abc你好','香港。你好']
    rows=[(context,text,strength*sum(fitted.get(k,0)*v for k,v in features(context,text).items()))
          for context in ('','我問你','香港，') for text in texts]
    cases=work/'joint-score-cases.tsv';cases.write_text(''.join('\t'.join((c,t,float(s).hex()))+'\n' for c,t,s in rows))
    java=work/'JointScoreCheck.java';java.write_text(JAVA)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-sourcepath',str(work/'app/src/main/java'),
                    '-d',str(work/'classes'),str(java)],check=True)
    result=subprocess.check_output(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.JointScoreCheck',
                                  str(work/'app/src/main/assets'),str(cases)],text=True)
    output.write_text(result);print(result,end='')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','weights','output'):p.add_argument(name,type=Path)
    p.add_argument('--strength',type=float,choices=(.25,.5,1),required=True)
    a=p.parse_args();verify(a.work,a.weights,a.strength,a.output)
