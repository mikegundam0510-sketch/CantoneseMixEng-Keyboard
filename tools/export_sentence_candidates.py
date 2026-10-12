#!/usr/bin/env python3
"""Export exact-code candidates and their actual final path scores from an archive.

Instrumentation is confined to a temporary historical checkout. It observes
scores after final pruning without changing ranking or the shipped application.
"""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile

from train_phrase_model import ROOT

DRIVER = r'''
package hk.cantonesemixeng.keyboard;
import java.io.*; import java.nio.file.*; import java.util.*;
public final class SentenceCandidateExport {
 private static Path assets;
 private static Reader asset(String n)throws IOException{return Files.newBufferedReader(assets.resolve(n));}
 public static void main(String[] args)throws Exception {
  assets=Path.of(args[0]);
  DictionaryEngine d=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
  QuickDecoder q=new QuickDecoder(d,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),
   OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
   PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),asset("hk_chat_phrases.tsv"),
   CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
   CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))));
  int total=0,found=0;
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    if(line.isEmpty()||line.startsWith("#"))continue;
    String[] f=line.split("\t",-1);
    if(f.length==7) {
     List<String> grammar=new ArrayList<>();
     for(String value:f[5].split("\\|")) if(!value.isEmpty()) {
      if(d.matchQuickCodes(f[2],value).isEmpty())throw new AssertionError(value);
      grammar.add(Double.toHexString(q.exportedStructuralSupport(f[1],value)));
     }
     out.write(line+"\t"+String.join("|",grammar)+"\n");total++;if(Integer.parseInt(f[4])>0)found++;continue;
    }
    String source=f.length==4?f[0]:"", context=f[f.length-3],code=f[f.length-2],gold=f[f.length-1];
    if(f.length!=3&&f.length!=4)throw new IllegalArgumentException(line);
    if(d.matchQuickCodes(code,gold).isEmpty())throw new AssertionError("Gold code: "+gold);
    List<String> values=q.decode(code,(c,w)->0,context);
    List<String> scores=new ArrayList<>();
    for(String value:values) {
     if(d.matchQuickCodes(code,value).isEmpty())throw new AssertionError(value);
     Double score=QuickDecoder.exportedSentenceScores.get(value);
     if(score==null||!Double.isFinite(score))throw new AssertionError("Missing path score: "+value);
     scores.add(Double.toHexString(score));
    }
    int rank=values.indexOf(gold)+1; total++;if(rank>0)found++;
    out.write(String.join("\t",source,context,code,gold,Integer.toString(rank),String.join("|",values),String.join("|",scores))+"\n");
    if(total%100==0)System.out.println("cases="+total+" reachable="+found);
   }
  }
  System.out.println("complete cases="+total+" reachable="+found);
 }
}
'''


def export(revision, cases, output):
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', revision + '^{commit}'], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', 'archive', revision, 'app/src/main/java', 'app/src/main/assets'], cwd=ROOT)
    output = output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sentence-export-') as directory:
        work = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as data: data.extractall(work, filter='data')
        source = work / 'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
        text = source.read_text()
        field = '    private static final int BEAM = 48;'
        hook = '        List<Path> completed = prune(lattice.get(code.length()));'
        if text.count(field) != 1 or text.count(hook) != 1:
            raise ValueError('Historical decoder structure changed; update observer')
        text = text.replace(field, '    static final Map<String, Double> exportedSentenceScores = new HashMap<>();\n' + field)
        score_hook = '    public double languageScore(String prefix, String text) {'
        if text.count(score_hook) != 1: raise ValueError('Structural scorer hook changed')
        text = text.replace(score_hook, '    double exportedStructuralSupport(String prefix, String text) {\n'
            '        return Math.max(0, completionBonus(prefix,text) + handoverBonus(prefix,text)\n'
            '            + ClauseRelations.score(prefix,text) + clauseStartStrength * ClauseStartRelations.score(prefix,text));\n'
            '    }\n' + score_hook)
        text = text.replace(hook, hook + '\n        exportedSentenceScores.clear();\n'
                            '        for (Path p : completed) exportedSentenceScores.merge(p.text, p.score, Math::max);')
        source.write_text(text)
        driver = work / 'SentenceCandidateExport.java'; driver.write_text(DRIVER)
        classes = work / 'classes'
        subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(work / 'app/src/main/java'),
                        '-d', str(classes), str(driver)], check=True)
        subprocess.run(['java', '-Xmx1g', '-cp', str(classes), 'hk.cantonesemixeng.keyboard.SentenceCandidateExport',
                        str(work / 'app/src/main/assets'), str(cases.resolve()), str(output)], check=True)
    return revision


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cases', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--revision', default='fac1e878eae03ff76fa3299e65f215299620b8f8')
    a = p.parse_args(); print('Exported', export(a.revision, a.cases, a.output))
