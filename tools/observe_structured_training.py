#!/usr/bin/env python3
"""Reconstruct TRAIN-only legal gold paths beside an unchanged ordinary search."""
import argparse
import json
from pathlib import Path
import subprocess
from native_phrase_relations import build, DRIVER
from pilot_final_hard_negatives import records
from prepare_joint_ranking import BASELINE, DATA
from prepare_tatoeba_corpus import digest
from run_joint_ranking import empty_archive
from train_phrase_model import ROOT

def gap_cases(pools, prefix, only_uncovered=True):
    allowed=[tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()]
    manifest=json.loads((DATA/'manifest.json').read_text())
    if digest(DATA/'train.tsv')!=manifest['file_sha256']['train.tsv']:raise ValueError('Frozen TRAIN changed')
    observed=list(records(pools))
    if [tuple(r[k] for k in ('source','context','code','gold')) for r in observed]!=allowed:
        raise ValueError('Complete ordered TRAIN pools required')
    covered={tuple(s.split('\t')[:4]) for s in prefix.read_text().splitlines()}
    if not covered<=set(allowed):raise ValueError('Non-training prefixes')
    return [row for row,r in zip(allowed,observed) if (not only_uncovered or row not in covered) and r['gold'] not in r['values']]

def check_cases(cases):
    rows=[tuple(s.split('\t')) for s in cases.read_text().splitlines()]
    allowed={tuple(s.split('\t')) for s in (DATA/'train.tsv').read_text().splitlines()}
    if not rows or len(rows)!=len(set(rows)) or not set(rows)<=allowed:raise ValueError('Unique TRAIN-only cases required')
    return rows

def prepare(work):
    work=empty_archive(work);build(work,BASELINE,original=True)
    quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java';text=quick.read_text()
    hooks=(ROOT/'tools/structured_training_hooks.inc').read_text()
    changes={
        '    private static final int BEAM = 48;':hooks+'\n    private static final int BEAM = 48;',
        '    private List<Path> prune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {':
        '    private List<Path> trainingPruneCore(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {',
        '            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);':
        '            trainingPosition=pos;\n            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);',
        '                if (options.isEmpty()) continue;':
        '                trainingOptions.put(pos+":"+length,new HashSet<>(options.keySet()));\n                if (options.isEmpty()) continue;',
        '                if (target.size() > 1024) lattice.set(pos + length,':
        '                if (target.size() > 1024) { trainingPosition=pos+length; lattice.set(pos + length,',
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));':
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores)); }',
        '        List<Path> completed = pruneFinal(lattice.get(code.length()));':
        '        List<Path> completed = pruneFinal(lattice.get(code.length()));\n        trainingCompleted=new ArrayList<>(completed);',
        '    private List<Path> pruneFinal(List<Path> input) {':
        '''    private List<Path> pruneFinal(List<Path> input) {
        for(Path p:input)if(p.text.equals(trainingGold))trainingGeneratedScore=Math.max(trainingGeneratedScore,p.score);''',
    }
    for old,new in changes.items():
        if text.count(old)!=1:raise ValueError('Training observer hook changed: '+old)
        text=text.replace(old,new)
    text=text.replace('    private void writeTraining(', '    void writeTraining(')
    quick.write_text(text)
    loop=r'''
  Path out=Path.of(args[2]);Files.createDirectories(out);int count=0;
  try(BufferedWriter audit=Files.newBufferedWriter(out.resolve("audit.tsv"));
      BufferedWriter pairs=Files.newBufferedWriter(out.resolve("pairs.tsv"));
      BufferedWriter visible=Files.newBufferedWriter(out.resolve("visible.tsv"))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);if(f.length!=4)throw new IllegalArgumentException("Four TRAIN columns required");
    QuickDecoder.trainingGold=f[3];QuickDecoder.trainingCode=f[2];QuickDecoder.trainingContext=f[1];
    QuickDecoder.trainingCuts.clear();QuickDecoder.trainingOptions.clear();
    QuickDecoder.trainingCompleted=Collections.emptyList();
    QuickDecoder.trainingGeneratedScore=Double.NEGATIVE_INFINITY;
    List<String> values=q.decode(f[2],(c,w)->0,f[1]);
    visible.write(line+"\t"+(values.indexOf(f[3])+1)+"\t"+String.join("|",values)+"\n");
    q.writeTraining(line,audit,pairs);
    if(++count%50==0)System.out.println("training_observed="+count);
   }
  }
 }
}
'''
    java=work/'RelationEvaluation.java';java.write_text(DRIVER[:DRIVER.index('  int count=0;')]+loop)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)

def run(work,cases,output):
    check_cases(cases)
    if output.exists():raise ValueError('Preserve existing observation output')
    pending=output.with_name(output.name+'.pending');pending.mkdir(parents=True,exist_ok=False)
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RelationEvaluation',
        str(work/'app/src/main/assets'),str(cases.resolve()),str(pending.resolve())],check=True)
    if len((pending/'audit.tsv').read_text().splitlines())!=len(check_cases(cases)):raise ValueError('Partial training trace')
    pending.rename(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('select','select-all','prepare','run'))
    p.add_argument('work',type=Path);p.add_argument('--pools',type=Path);p.add_argument('--prefix',type=Path)
    p.add_argument('--cases',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.mode in ('select','select-all'):
        rows=gap_cases(a.pools,a.prefix,only_uncovered=a.mode=='select');a.work.mkdir(parents=True,exist_ok=True)
        (a.work/'cases.tsv').write_text(''.join('\t'.join(r)+'\n' for r in rows));print('TRAIN gap cases:',len(rows))
    elif a.mode=='prepare':prepare(a.work)
    else:run(a.work,a.cases,a.output)
