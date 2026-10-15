#!/usr/bin/env python3
"""Export cold character ranks from the actual frozen Java dictionary."""
import argparse
import json
from pathlib import Path
import subprocess
from native_phrase_relations import build
from prepare_joint_ranking import BASELINE
from prepare_tatoeba_corpus import digest
from run_joint_ranking import empty_archive

JAVA=r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;import java.lang.reflect.*;
public class TrainingCodeExport {
 public static void main(String[] args)throws Exception {
  Path assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
   Files.newBufferedReader(assets.resolve("english.txt")),Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
  Field f=QuickDecoder.class.getDeclaredField("HK_PARTICLES");f.setAccessible(true);String particles=(String)f.get(null);
  Set<String> characters=new TreeSet<>();
  for(String line:Files.readAllLines(assets.resolve("cangjie5.base.dict.yaml"))) {
   String[] row=line.split("\t");if(row.length<2||row[0].codePointCount(0,row[0].length())!=1||!row[1].matches("[a-z]{1,5}"))continue;
   if(OfflineLanguageModel.han(row[0].codePointAt(0)))characters.add(row[0]);
  }
  Map<String,List<String>> cached=new HashMap<>();
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[1]))) {
   for(String c:characters) {
    List<String> codes=new ArrayList<>(d.quickCodesFor(c));Collections.sort(codes);
    for(String code:codes) {
     List<String> letters=cached.computeIfAbsent(code,key->{List<String> values=new ArrayList<>();
      for(String w:d.quickCandidates(key))if(w.codePointCount(0,w.length())==1&&OfflineLanguageModel.han(w.codePointAt(0)))values.add(w);return values;});
     int rank=letters.indexOf(c)+1;if(rank==0)throw new AssertionError("Missing reverse code");
     out.write(c+"\t"+code+"\t"+rank+"\t"+d.frequency(c)+"\t"+particles.contains(c)+"\n");
    }
   }
  }
 }
}
'''

def export(work,output):
    work=empty_archive(work)
    if output.exists():raise ValueError('Preserve existing code inventory')
    build(work,BASELINE,original=True)
    java=work/'TrainingCodeExport.java';java.write_text(JAVA)
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(work/'classes'),'-sourcepath',str(work/'app/src/main/java'),
        '-d',str(work/'classes'),str(java)],check=True)
    output.parent.mkdir(parents=True,exist_ok=True);pending=output.with_suffix('.pending')
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.TrainingCodeExport',
        str(work/'app/src/main/assets'),str(pending)],check=True);pending.replace(output)
    assets=work/'app/src/main/assets'
    report=dict(baseline_revision=BASELINE,output_sha256=digest(output),rows=len(output.read_text().splitlines()),
        asset_sha256={name:digest(assets/name) for name in ('cangjie5.base.dict.yaml','character_frequencies.tsv')},
        java_sha256=digest(java),policy='Actual dictionary cold Han ranks; training admission chooses rank<=24 so character options do not depend on context rescue. This does not guarantee beam survival or display.')
    output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.work,a.output)
