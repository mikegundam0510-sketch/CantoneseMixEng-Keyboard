#!/usr/bin/env python3
"""Observe close, at-risk same-code prefixes in the frozen decoder, without changing search."""
import argparse
import io
import subprocess
import tarfile
import tempfile
from pathlib import Path
from export_sentence_candidates import DRIVER
from train_phrase_model import ROOT

OBSERVER = r'''
    static String observedSource, observedContext, observedCode, observedGold;
    static int observedPosition;
    static final List<PrefixCheckpoint> checkpoints = new ArrayList<>();
    private static final class PrefixCheckpoint {
        final int position, rank; final String positive, hints;
        final List<String> negatives = new ArrayList<>();
        final List<Double> margins = new ArrayList<>();
        PrefixCheckpoint(int p,int r,String text,String h){position=p;rank=r;positive=text;hints=h;}
    }
    private void observePrefixes(List<Path> input,List<Token> following,Map<Path,Double> scores) {
        if(observedPosition<=0 || observedPosition>=observedCode.length() || input.size()<=BEAM)return;
        List<Path> unique=new ArrayList<>(); Set<String> seen=new HashSet<>();
        for(Path p:input)if(seen.add(p.text))unique.add(p);
        if(unique.size()<BEAM)return;
        double floor=unique.get(BEAM-1).score-4;
        Path positive=null;int rank=0;
        for(int i=0;i<unique.size();i++) {
            Path p=unique.get(i);
            if(p.text.codePointCount(0,p.text.length())<2 || p.text.equals(observedGold)
                || !observedGold.startsWith(p.text))continue;
            if(dictionary.matchQuickCodes(observedCode.substring(observedPosition),observedGold.substring(p.text.length())).isEmpty())continue;
            positive=p;rank=i+1;break;
        }
        if(positive==null || rank<2 || positive.score<floor)return;
        List<String> hints=new ArrayList<>();for(Token t:following)hints.add(t.text);
        PrefixCheckpoint point=new PrefixCheckpoint(observedPosition,rank,positive.text,String.join("|",hints));
        Set<String> rivals=new HashSet<>();
        for(int i:new int[]{0,BEAM-3,BEAM-1,BEAM}) {
            if(i>=unique.size()||point.negatives.size()==3)continue;
            Path n=unique.get(i);
            if(n.text.equals(positive.text) || observedGold.startsWith(n.text) || !rivals.add(n.text))continue;
            point.negatives.add(n.text);
            point.margins.add(scores==null?positive.score-n.score:scores.get(positive)-scores.get(n));
        }
        if(!point.negatives.isEmpty())checkpoints.add(point);
    }
    static void writePrefixPairs(BufferedWriter out)throws IOException {
        checkpoints.sort(Comparator.comparingInt((PrefixCheckpoint p)->p.rank>BEAM?0:1)
            .thenComparingInt(p->-p.position).thenComparingInt(p->-p.rank));
        Set<String> seen=new HashSet<>();int kept=0;
        for(PrefixCheckpoint p:checkpoints) {
            if(!seen.add(p.position+":"+p.positive)||kept==2)continue;kept++;
            for(int i=0;i<p.negatives.size();i++) out.write(String.join("\t",observedSource,observedContext,
                observedCode,observedGold,Integer.toString(p.position),p.positive,p.negatives.get(i),
                Double.toHexString(p.margins.get(i)),p.hints,Integer.toString(p.rank))+"\n");
        }
    }
'''

def export(cases, output, revision='241803b'):
    archive=subprocess.check_output(['git','archive',revision,'app/src/main/java','app/src/main/assets'],cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='prefix-export-') as directory:
        work=Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as data:data.extractall(work,filter='data')
        source=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
        text=source.read_text()
        changes={
            '    private static final int BEAM = 48;':OBSERVER+'\n    private static final int BEAM = 48;',
            '            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);':
            '            observedPosition=pos;\n            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);',
            '                if (target.size() > 1024) lattice.set(pos + length,':
            '                if (target.size() > 1024) { observedPosition=pos+length; lattice.set(pos + length,',
            '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));':
            '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores)); }',
            '        if (following.isEmpty() || input.size() <= BEAM) return prune(input);':
            '        if (following.isEmpty() || input.size() <= BEAM) { List<Path> result=prune(input); observePrefixes(input,following,null);return result; }',
            '        List<Path> result = distinctPaths(input);\n        Set<String> seen':
            '        observePrefixes(input,following,scores);\n        List<Path> result = distinctPaths(input);\n        Set<String> seen',
        }
        for before,after in changes.items():
            if text.count(before)!=1:raise ValueError('Observer hook changed: '+before)
            text=text.replace(before,after)
        source.write_text(text)
        driver=DRIVER.replace('__SEARCH_ARGS__',',SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64")))')
        start=driver.index('    List<String> values=q.decode(')
        end=driver.index('    if(total%100==0)',start)
        driver=driver[:start]+'''    QuickDecoder.observedSource=source;QuickDecoder.observedContext=context;
    QuickDecoder.observedCode=code;QuickDecoder.observedGold=gold;QuickDecoder.checkpoints.clear();
    List<String> values=q.decode(code,(c,w)->0,context);
    QuickDecoder.writePrefixPairs(out);total++;
    if(!QuickDecoder.checkpoints.isEmpty())found++;
'''+driver[end:]
        # The seven-column structural export branch is irrelevant here.
        start=driver.index('    if(f.length==7) {');end=driver.index('    String source=',start)
        driver=driver[:start]+driver[end:]
        java=work/'SentenceCandidateExport.java';java.write_text(driver)
        classes=work/'classes'
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(classes),str(java)],check=True)
        output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['java','-Xmx1g','-cp',str(classes),'hk.cantonesemixeng.keyboard.SentenceCandidateExport',
            str(work/'app/src/main/assets'),str(cases.resolve()),str(work/'complete-pairs.tsv')],check=True)
        # Publish only a complete validated UTF-8 artifact; interrupted exports
        # never leave partial training inputs or share an open output handle.
        complete=(work/'complete-pairs.tsv').read_text()
        if any(len(line.split('\t'))!=10 for line in complete.splitlines()):raise ValueError('Incomplete observed pair')
        output.write_text(complete)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cases',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.cases,a.output)
