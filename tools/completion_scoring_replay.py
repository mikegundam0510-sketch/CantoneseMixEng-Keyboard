#!/usr/bin/env python3
"""Replay a display-boundary policy on actual complete native pools; calibration only."""
import argparse
from pathlib import Path
import subprocess

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class CompletionReplay {
 public static void main(String[] args)throws Exception {
  PhraseRelationRanker model=PhraseRelationRanker.load(Files.newInputStream(Path.of(args[0])));
  PhraseRelationRanker tailModel=args[8].equals("-")?null:PhraseRelationRanker.load(Files.newInputStream(Path.of(args[8])));
  boolean strictEvidence=Boolean.parseBoolean(args[9]);
  int width=Integer.parseInt(args[3]),count=0,cap=Integer.parseInt(args[4]);
  double margin=Double.parseDouble(args[5]);boolean supportOnly=Boolean.parseBoolean(args[6]);double minimumLift=Double.parseDouble(args[7]);
  if(width!=20&&width!=36&&width!=5)throw new IllegalArgumentException("Frozen display policies only");
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);if(f.length!=10)throw new IllegalArgumentException("Actual native observer required");
    List<String> values=new ArrayList<>(f[6].isEmpty()?Collections.emptyList():Arrays.asList(f[6].split("\\|")));
    String[] adjusted=f[8].split("\\|"),raw=f[7].split("\\|");
    Map<String,Double> scores=new HashMap<>(),rawScores=new HashMap<>();
    for(int i=0;i<values.size();i++){scores.put(values.get(i),Double.valueOf(adjusted[i]));rawScores.put(values.get(i),Double.valueOf(raw[i]));}
    Map<String,Map<String,Integer>> cache=new HashMap<>();String legacyFirst=values.isEmpty()?"":values.get(0);
    if(width>20&&values.size()>20) {
     String first=values.get(0);double reference=model.rawScore(f[1],first,cache);
     Set<String> visible=new HashSet<>(values.subList(0,Math.min(width,values.size())));
     for(String value:values.subList(20,Math.min(width,values.size())))
      scores.put(value,scores.get(value)+model.alignedCorrection(model.rawScore(f[1],value,cache),reference));
     values.sort(Comparator.comparingDouble((String value)->rawScores.get(value)).reversed());
     values.sort(Comparator.comparingInt((String value)->value.equals(first)?0:1)
       .thenComparingInt(value->visible.contains(value)?0:1)
       .thenComparing(Comparator.comparingDouble((String value)->scores.get(value)).reversed()));
    }
    model.promoteHead(f[1],values,scores,cache);
    if(width==5&&values.size()>20) {
     PhraseRelationRanker scorer=tailModel==null?model:tailModel;
     Map<String,Map<String,Integer>> tailCache=tailModel==null?cache:new HashMap<>();
     double reference=model.rawScore(f[1],legacyFirst,cache);
     String boundary=values.get(19);double floor=scores.get(boundary),boundaryRaw=scorer.rawScore(f[1],boundary,tailCache);
     List<String> eligible=new ArrayList<>();PhraseRelationRanker.Evidence boundaryEvidence=null;
     for(String value:new ArrayList<>(values.subList(20,Math.min(36,values.size())))) {
      double rawScore=scorer.rawScore(f[1],value,tailCache);
      double score=scores.get(value)+scorer.alignedCorrection(rawScore,tailModel==null?reference:boundaryRaw);
      double lift=tailModel==null?model.correction(rawScore,boundaryRaw):rawScore-boundaryRaw;
      if(score<floor+margin||lift<minimumLift)continue;
      if(boundaryEvidence==null)boundaryEvidence=scorer.evidence(f[1],boundary);
      PhraseRelationRanker.Evidence candidate=scorer.evidence(f[1],value);
      boolean supported=tailModel==null?(supportOnly?candidate.supportedOver(boundaryEvidence):model.trustedPromotion(candidate,boundaryEvidence,lift)):
         strictEvidence?candidate.supportedOver(boundaryEvidence):candidate.supportsTailAlternative(boundaryEvidence);
      if(!supported)continue;
      scores.put(value,score);eligible.add(value);
     }
     eligible.sort(Comparator.comparingDouble((String value)->scores.get(value)).reversed());
     if(eligible.size()>cap)eligible=new ArrayList<>(eligible.subList(0,cap));
     if(!eligible.isEmpty()) {
      List<String> tail=new ArrayList<>(values.subList(5,20));tail.addAll(eligible);
      tail.sort(Comparator.comparingDouble((String value)->scores.get(value)).reversed());
      List<String> reordered=new ArrayList<>(values.subList(0,5));reordered.addAll(tail.subList(0,15));
      Set<String> seen=new HashSet<>(reordered);for(String value:values)if(seen.add(value))reordered.add(value);
      values=reordered;
     }
    }
    values=new ArrayList<>(values.subList(0,Math.min(20,values.size())));
    out.write(String.join("\t",Arrays.copyOf(f,4))+"\t"+(values.indexOf(f[3])+1)+"\t"+String.join("|",values)+"\n");
    if(++count%500==0)System.out.println("replayed="+count);
   }
  }
 }
}
'''

def run(scored,output,baseline,width,cap=4,margin=.25,support_only=False,minimum_lift=.5,tail_model=None,strict_evidence=True):
    model=baseline/'app/src/main/java/hk/cantonesemixeng/keyboard/PhraseRelationRanker.java'
    text=model.read_text()
    if 'boolean supportsTailAlternative(' not in text:
        old='        boolean repairs(Evidence reference) {'
        if text.count(old)!=1:raise ValueError('Tail evidence hook changed')
        text=text.replace(old,'''        boolean supportsTailAlternative(Evidence reference) {
            if(kinds.isEmpty()||positive.size()<2)return false;
            for(String key:positive)if(!reference.positive.contains(key))return true;return false;
        }
'''+old);model.write_text(text)
    java=baseline/'CompletionReplay.java';java.write_text(DRIVER)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(baseline/'classes'),'-sourcepath',str(baseline/'app/src/main/java'),
                    '-d',str(baseline/'classes'),str(java)],check=True)
    pending=output.with_suffix('.pending.tsv')
    subprocess.run(['java','-Xmx1g','-cp',str(baseline/'classes'),'hk.cantonesemixeng.keyboard.CompletionReplay',
                    str(baseline/'app/src/main/assets/relation_ranker.b64'),str(scored),str(pending),str(width),
                    str(cap),str(margin),str(support_only).lower(),str(minimum_lift),str(tail_model) if tail_model else '-',str(strict_evidence).lower()],check=True)
    pending.replace(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('scored','output','baseline'):p.add_argument(name,type=Path)
    p.add_argument('--width',type=int,choices=(5,20,36),required=True,help='5=guarded tail,20=legacy,36=wide display')
    p.add_argument('--cap',type=int,choices=(2,4),default=4);p.add_argument('--margin',type=float,choices=(.25,.5),default=.25)
    p.add_argument('--support-only',action='store_true');p.add_argument('--minimum-lift',type=float,choices=(0,.5),default=.5)
    p.add_argument('--tail-model',type=Path);p.add_argument('--tail-evidence',action='store_true')
    a=p.parse_args();run(a.scored,a.output,a.baseline,a.width,a.cap,a.margin,a.support_only,a.minimum_lift,a.tail_model,not a.tail_evidence)
