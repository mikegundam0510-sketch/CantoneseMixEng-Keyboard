#!/usr/bin/env python3
"""Run the actual optional Java ranker on frozen baseline assets, without APK."""
import argparse
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
from train_phrase_model import ROOT

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class RelationEvaluation {
 static Path assets;static Reader a(String n)throws Exception{return Files.newBufferedReader(assets.resolve(n));}
 public static void main(String[] args)throws Exception {
  assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
  QuickDecoder q=new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),
   OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
   PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),a("hk_chat_phrases.tsv"),
   CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
   CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))),
   SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))),
   PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))),
   Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);
  int count=0;try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    if(line.isEmpty()||line.startsWith("#"))continue;String[] f=line.split("\t",-1);
    if(f.length!=4)throw new IllegalArgumentException("Named four-column cases required");
    List<String> values=q.decode(f[2],(c,w)->0,f[1]);if(values.size()>20)throw new AssertionError("Display bound");
    for(String text:values)if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact candidate");
    out.write(line+"\t"+(values.indexOf(f[3])+1)+"\t"+String.join("|",values)+"\n");
    if(++count%100==0)System.out.println("decoded="+count);
   }
  }
 }
}
'''

def build(work):
    work.mkdir(parents=True,exist_ok=True)
    archive=subprocess.check_output(['git','archive','21ede20','app/src/main/java','app/src/main/assets'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as data:data.extractall(work,filter='data')
    for name in ('QuickDecoder','PhraseRelationRanker'):
        relative=f'app/src/main/java/hk/cantonesemixeng/keyboard/{name}.java';shutil.copyfile(ROOT/relative,work/relative)
    java=work/'RelationEvaluation.java';java.write_text(DRIVER)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)

def run(work,cases,output):
    output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True);pending=output.with_suffix('.pending.tsv')
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RelationEvaluation',
        str(work/'app/src/main/assets'),str(cases.resolve()),str(pending)],check=True)
    pending.replace(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('build','run'));p.add_argument('work',type=Path)
    p.add_argument('--cases',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.mode=='build':build(a.work)
    elif a.cases and a.output:run(a.work,a.cases,a.output)
    else:p.error('--cases and --output required')
