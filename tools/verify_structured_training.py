#!/usr/bin/env python3
"""Independent exhaustive tiny gold-path check and observer label-invariance."""
import argparse
from pathlib import Path
import subprocess

JAVA=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.lang.reflect.*;import java.util.*;
public class StructuredTrainingCheck {
 static DictionaryEngine dictionary;static QuickDecoder q;static Method shadow;
 static Map<String,Double> words=new LinkedHashMap<>();
 static double exhaustive(String code,String gold,String context,int pos,int at,double score) {
  if(pos==code.length())return at==gold.length()?score:Double.NEGATIVE_INFINITY;
  double best=Double.NEGATIVE_INFINITY;
  for(int length=1;length<=Math.min(16,code.length()-pos);length++) {
   String part=code.substring(pos,pos+length);
   for(int end=at;end<gold.length();) {
    end+=Character.charCount(gold.codePointAt(end));String word=gold.substring(at,end);
    if(dictionary.matchQuickCodes(part,word).isEmpty())continue;
    int n=word.codePointCount(0,word.length());Double prior=words.get(part+":"+word);
    if(prior==null&&n==1&&length<=2)prior=(double)dictionary.frequency(word);
    if(prior==null)continue;
    double increment=q.languageScore(context+gold.substring(0,at),word)+(n>1?Math.min(1.5,Math.log1p(prior)/10)*(n-1):0);
    best=Math.max(best,exhaustive(code,gold,context,pos+length,end,score+increment));
   }
  }
  return best;
 }
 @SuppressWarnings("unchecked") static QuickDecoder.TeacherPath path(String code,String gold,String context,int policy)throws Exception {
  QuickDecoder.trainingCode=code;QuickDecoder.trainingGold=gold;QuickDecoder.trainingContext=context;
  Map<Integer,Map<Integer,QuickDecoder.TeacherPath>> paths=(Map<Integer,Map<Integer,QuickDecoder.TeacherPath>>)shadow.invoke(q,policy);
  return paths.getOrDefault(code.length(),Collections.emptyMap()).get(gold.codePointCount(0,gold.length()));
 }
 public static void main(String[] args)throws Exception {
  Path assets=Path.of(args[0]);dictionary=new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
      Files.newBufferedReader(assets.resolve("english.txt")),Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
  words.put("ofvd:你好",100.);words.put("vdrf:好嗎",300.);words.put("ab:日月",20.);
  StringBuilder vocabulary=new StringBuilder();for(Map.Entry<String,Double> e:words.entrySet()) {
   String[] f=e.getKey().split(":");vocabulary.append(f[0]).append('\t').append(f[1]).append('\t').append(e.getValue()).append('\n');
  }
  q=new QuickDecoder(dictionary,new StringReader(vocabulary.toString()),null);
  shadow=QuickDecoder.class.getDeclaredMethod("teacherPaths",int.class);shadow.setAccessible(true);
  int checked=0;
  for(String[] example:new String[][]{{"ofvdrf","你好嗎"},{"aba","日月日"},{"ofvdofvd","你好你好"}}) {
   for(String context:new String[]{"","我問你"}) {
    QuickDecoder.TeacherPath p=path(example[0],example[1],context,0);
    double expected=exhaustive(example[0],example[1],context,0,0,0);
    if(p==null||Math.abs(p.score-expected)>1e-9)throw new AssertionError("Wrong teacher transition/segmentation maximum");
    StringBuilder recovered=new StringBuilder(),codes=new StringBuilder();List<QuickDecoder.TeacherPath> chain=new ArrayList<>();
    for(QuickDecoder.TeacherPath step=p;step.parent!=null;step=step.parent)chain.add(step);Collections.reverse(chain);
    for(QuickDecoder.TeacherPath step:chain){recovered.append(step.word);codes.append(step.part);}
    if(!recovered.toString().equals(example[1])||!codes.toString().equals(example[0]))throw new AssertionError("Bad alignment reconstruction");
    checked++;
   }
   QuickDecoder.trainingOptions.clear();QuickDecoder.trainingCuts.clear();
   path(example[0],example[1],"",0);List<String> withGold=q.decode(example[0],(c,w)->0,"");
   QuickDecoder.trainingGold="";QuickDecoder.trainingOptions.clear();QuickDecoder.trainingCuts.clear();
   List<String> withoutGold=q.decode(example[0],(c,w)->0,"");
   if(!withGold.equals(withoutGold))throw new AssertionError("Gold label changed search");
  }
  if(path("ofvdrf","你嗎好","",0)!=null)throw new AssertionError("Inexact gold accepted");
  QuickDecoder.trainingOptions.clear();
  if(path("ofvdrf","你好嗎","",1)!=null)throw new AssertionError("Missing selected option forced into selected-only path");
  String supplementary="𠮩𠹌你好";StringBuilder code=new StringBuilder();
  for(int cp:supplementary.codePoints().toArray()) {
   List<String> codes=dictionary.quickCodesFor(new String(Character.toChars(cp)));
   if(codes.isEmpty())throw new AssertionError("Missing supplementary fixture");code.append(codes.iterator().next());
  }
  if(path(code.toString(),supplementary,"",0)==null)throw new AssertionError("Supplementary alignment failed");
  System.out.println("exhaustive_path_cases="+checked+" label_invariance=3 invalid_alignment=1 selected_option_isolation=1 supplementary=1");
 }
}
'''

def verify(work,output):
    java=work/'StructuredTrainingCheck.java';java.write_text(JAVA)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-sourcepath',str(work/'app/src/main/java'),
        '-d',str(work/'classes'),str(java)],check=True)
    result=subprocess.check_output(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.StructuredTrainingCheck',
        str(work/'app/src/main/assets')],text=True)
    output.write_text(result);print(result,end='')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();verify(a.work,a.output)
