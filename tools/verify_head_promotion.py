#!/usr/bin/env python3
"""Compare native PRR3 first-choice gates with independent Python feature scoring."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from evaluate_head_promotion import simulate
from pilot_final_hard_negatives import records
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

DRIVER=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public class HeadGateParity {
 public static void main(String[] args)throws Exception {
  PhraseRelationRanker model=PhraseRelationRanker.load(Files.newInputStream(Path.of(args[0])));
  if(!model.headPromotion())throw new AssertionError("Head gate disabled");
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);List<String> values=new ArrayList<>(f[6].isEmpty()?Collections.emptyList():Arrays.asList(f[6].split("\\|")));
    String[] numbers=f[8].split("\\|");Map<String,Double> scores=new HashMap<>();
    for(int i=0;i<values.size();i++)scores.put(values.get(i),Double.valueOf(numbers[i]));
    model.promoteHead(f[1],values,scores);
    out.write(String.join("|",values.subList(0,Math.min(20,values.size())))+"\n");
   }
  }
 }
}
'''


def verify(scored,model,weights,margin,lift,strength,output):
    rows=list(records(scored));lexicon=json.loads((ROOT/'tools/data/phrase_relations/lexicon.json').read_text())
    orders=[];simulate(rows,json.loads(weights.read_text()),lexicon,margin,lift,{},strength,orders)
    with tempfile.TemporaryDirectory(prefix='head-gate-parity-') as directory:
        work=Path(directory);java=work/'HeadGateParity.java';java.write_text(DRIVER)
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(ROOT/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
        subprocess.run(['java','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.HeadGateParity',str(model.resolve()),str(scored.resolve()),str(work/'native.tsv')],check=True)
        actual=(work/'native.tsv').read_text().splitlines();assert len(actual)==len(orders)
        for order,native in zip(orders,actual):assert '|'.join(order)==native
    result=dict(cases=len(orders),candidate_lists_equal=True,model_sha256=digest(model),scored_sha256=digest(scored))
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['scored','model','weights','output']:p.add_argument(name,type=Path)
    for name in ['margin','lift','strength']:p.add_argument('--'+name,required=True,type=float)
    a=p.parse_args();verify(a.scored,a.model,a.weights,a.margin,a.lift,a.strength,a.output)
