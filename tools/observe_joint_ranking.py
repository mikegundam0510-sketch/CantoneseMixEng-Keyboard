#!/usr/bin/env python3
"""Observe real search competitors and completed pools together in an archive."""
import argparse
import json
from pathlib import Path
import subprocess
from export_prefix_pairs import OBSERVER
from native_phrase_relations import build,DRIVER
from prepare_joint_ranking import BASELINE
from prepare_tatoeba_corpus import digest
from run_joint_ranking import empty_archive

EXTRA='''
    static final Map<String,Double> observedRaw=new HashMap<>(),observedAdjusted=new HashMap<>();
    static List<String> observedOrder=Collections.emptyList();
    double observedSupport(String context,String text){return structuralSupport(context,text);}
'''
LOOP=r'''
  Path out=Path.of(args[2]);Files.createDirectories(out);int count=0;
  try(BufferedWriter pools=Files.newBufferedWriter(out.resolve("pools.tsv"));
      BufferedWriter pairs=Files.newBufferedWriter(out.resolve("prefix.tsv"));
      BufferedWriter visible=Files.newBufferedWriter(out.resolve("visible.tsv"))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    if(line.isEmpty()||line.startsWith("#"))continue;String[] f=line.split("\t",-1);
    if(f.length!=4)throw new IllegalArgumentException("Named four-column cases required");
    QuickDecoder.observedSource=f[0];QuickDecoder.observedContext=f[1];
    QuickDecoder.observedCode=f[2];QuickDecoder.observedGold=f[3];
    QuickDecoder.checkpoints.clear();QuickDecoder.observedRaw.clear();QuickDecoder.observedAdjusted.clear();
    QuickDecoder.observedOrder=Collections.emptyList();
    List<String> values=q.decode(f[2],(c,w)->0,f[1]);
    if(values.size()>20||new HashSet<>(values).size()!=values.size())throw new AssertionError("Display bound");
    visible.write(line+"\t"+(values.indexOf(f[3])+1)+"\t"+String.join("|",values)+"\n");
    List<String> full=QuickDecoder.observedOrder;
    List<String> raw=new ArrayList<>(),adjusted=new ArrayList<>(),support=new ArrayList<>();
    for(String text:full) {
     if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact observed candidate");
     raw.add(Double.toHexString(QuickDecoder.observedRaw.get(text)));
     adjusted.add(Double.toHexString(QuickDecoder.observedAdjusted.get(text)));
     support.add(Double.toHexString(q.observedSupport(f[1],text)));
    }
    pools.write(line+"\t"+(full.isEmpty()?"":full.get(0))+"\t"+(full.indexOf(f[3])+1)+"\t"+
        String.join("|",full)+"\t"+String.join("|",raw)+"\t"+String.join("|",adjusted)+"\t"+String.join("|",support)+"\n");
    QuickDecoder.writePrefixPairs(pairs);
    if(++count%100==0)System.out.println("observed="+count);
   }
  }
 }
}
'''

def prepare(work):
    work=empty_archive(work)
    build(work,BASELINE,original=True)
    quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java';text=quick.read_text()
    changes={
        '    private static final int BEAM = 48;':OBSERVER+EXTRA+'\n    private static final int BEAM = 48;',
        '            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);':
        '            observedPosition=pos;\n            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);',
        '                if (target.size() > 1024) lattice.set(pos + length,':
        '                if (target.size() > 1024) { observedPosition=pos+length; lattice.set(pos + length,',
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));':
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores)); }',
        '        if(prefixRanker==null||result.size()<BEAM||input.size()<=result.size())return result;':
        '        observePrefixes(input,following,baselineScores);\n        if(prefixRanker==null||result.size()<BEAM||input.size()<=result.size())return result;',
        '        List<Path> completed = pruneFinal(lattice.get(code.length()));':
        '        List<Path> completed = pruneFinal(lattice.get(code.length()));\n        for(Path p:completed)observedRaw.put(p.text,p.score);',
        '        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));':
        '''        observedOrder=new ArrayList<>(result);
        for(String value:result)observedAdjusted.put(value,finalScores==null?observedRaw.get(value):finalScores.get(value));
        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));''',
    }
    for old,new in changes.items():
        if text.count(old)!=1:raise ValueError('Observer hook changed: '+old)
        text=text.replace(old,new)
    quick.write_text(text)
    driver=DRIVER[:DRIVER.index('  int count=0;')]+LOOP
    java=work/'RelationEvaluation.java';java.write_text(driver)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
    (work/'observer-source.json').write_text(json.dumps({'baseline':BASELINE,'quick_sha256':digest(quick),'driver_sha256':digest(java)},indent=2)+'\n')

def run(work,cases,output):
    output.mkdir(parents=True,exist_ok=True)
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RelationEvaluation',
                    str(work/'app/src/main/assets'),str(cases),str(output)],check=True)

def merge(work,cases,output):
    expected=[tuple(s.split('\t')) for s in cases.read_text().splitlines()]
    if len(set(expected))!=len(expected):raise ValueError('Unique training identities required')
    output.mkdir(parents=True,exist_ok=True);allowed=set(expected);hashes={}
    for name in ('pools.tsv','visible.tsv','prefix.tsv'):
        groups={key:[] for key in expected}
        for shard in range(3):
            path=work/f'train-{shard}'/name;hashes[str(path)]=digest(path)
            for line in path.read_text().splitlines():
                key=tuple(line.split('\t')[:4])
                if key not in allowed:raise ValueError('Unexpected observation')
                groups[key].append(line)
        if name!='prefix.tsv' and any(len(v)!=1 for v in groups.values()):raise ValueError('Partial or duplicate observer output')
        pending=output/(name+'.pending');pending.write_text(''.join(s+'\n' for key in expected for s in groups[key]))
        pending.replace(output/name)
    (output/'observation-manifest.json').write_text(json.dumps(dict(cases_sha256=digest(cases),input_sha256=hashes,
        output_sha256={name:digest(output/name) for name in ('pools.tsv','visible.tsv','prefix.tsv')}),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','run','merge'));p.add_argument('work',type=Path)
    p.add_argument('--cases',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.mode=='prepare':prepare(a.work)
    elif a.cases is None or a.output is None:p.error('run requires --cases and --output')
    elif a.mode=='merge':merge(a.work,a.cases,a.output)
    else:run(a.work,a.cases,a.output)
