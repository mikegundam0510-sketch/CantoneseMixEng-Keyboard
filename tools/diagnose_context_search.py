#!/usr/bin/env python3
"""Archive-only labels observe unchanged inference; never emit training pairs."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

import observe_structured_training as observer
from native_phrase_relations import DRIVER
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

BASELINE='e209474'
DATA=ROOT/'tools/data/context_search'

EXTRA=r'''
    static Set<String> diagnosticEligible=new HashSet<>();
    String diagnosticSummary() {
        int count=trainingGold.codePointCount(0,trainingGold.length());
        TeacherPath legal=teacherPaths(0).getOrDefault(trainingCode.length(),Collections.emptyMap()).get(count);
        TeacherPath selected=teacherPaths(1).getOrDefault(trainingCode.length(),Collections.emptyMap()).get(count);
        TeacherPath potential=teacherPaths(2).getOrDefault(trainingCode.length(),Collections.emptyMap()).get(count);
        boolean completed=false;for(Path p:trainingCompleted)if(p.text.equals(trainingGold))completed=true;
        boolean generated=Double.isFinite(trainingGeneratedScore),eligible=diagnosticEligible.contains(trainingGold);
        int firstLost=0;for(TrainingCut c:trainingCuts)if(!c.before.isEmpty()&&c.after.isEmpty())
            if(firstLost==0||c.pos<firstLost)firstLost=c.pos;
        String stage=legal==null?"no_legal_Han_path":potential==null?"outside_static_option_bounds":
            !generated?(selected==null?"ordinary_options_uncovered":"prefix_search_lost"):
            !completed?"completed_pool_cut":!eligible?"confidence_or_eligible_pool_cut":"outside_display20";
        List<String> segments=new ArrayList<>();
        TeacherPath chosen=selected!=null?selected:potential!=null?potential:legal;
        for(TeacherPath p=chosen;p!=null&&p.parent!=null;p=p.parent)
            segments.add(p.parent.pos+":"+p.part+":"+p.word+":"+p.available);
        Collections.reverse(segments);
        return stage+"\t"+(legal!=null)+"\t"+(potential!=null)+"\t"+(selected!=null)+"\t"+
            generated+"\t"+completed+"\t"+eligible+"\t"+firstLost+"\t"+String.join("|",segments);
    }
'''

LOOP=r'''
  Path out=Path.of(args[2]);Files.createDirectories(out);int count=0;
  try(BufferedWriter audit=Files.newBufferedWriter(out.resolve("audit.tsv"));
      BufferedWriter visible=Files.newBufferedWriter(out.resolve("visible.tsv"))) {
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    String[] f=line.split("\t",-1);if(f.length!=4)throw new IllegalArgumentException("Four columns required");
    QuickDecoder.trainingGold=f[3];QuickDecoder.trainingCode=f[2];QuickDecoder.trainingContext=f[1];
    QuickDecoder.trainingCuts.clear();QuickDecoder.trainingOptions.clear();QuickDecoder.diagnosticEligible.clear();
    QuickDecoder.trainingCompleted=Collections.emptyList();QuickDecoder.trainingGeneratedScore=Double.NEGATIVE_INFINITY;
    List<String> values=q.decode(f[2],(c,w)->0,f[1]);
    if(values.size()>20||new HashSet<>(values).size()!=values.size())throw new AssertionError("Display bound");
    for(String text:values)if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact candidate");
    visible.write(line+"\t"+(values.indexOf(f[3])+1)+"\t"+String.join("|",values)+"\n");
    audit.write(line+"\t"+q.diagnosticSummary()+"\n");
    if(++count%50==0)System.out.println("diagnosed="+count);
   }
  }
 }
}
'''


def prepare(work):
    observer.BASELINE=BASELINE
    observer.prepare(work)
    quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    text=quick.read_text()
    anchor='    private static final int BEAM = 48;'
    assert text.count(anchor)==1
    text=text.replace(anchor,EXTRA+'\n'+anchor)
    anchor='        Map<String,Double> finalScores=null;'
    assert text.count(anchor)==1
    text=text.replace(anchor,'        diagnosticEligible.addAll(result);\n'+anchor)
    quick.write_text(text)
    java=work/'RelationEvaluation.java';java.write_text(DRIVER[:DRIVER.index('  int count=0;')]+LOOP)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)


def cases(output):
    source=ROOT/'tools/reports/clean-language-models-2026-10-16/independent500-candidate.tsv'
    rows=[s.split('\t') for s in source.read_text().splitlines()]
    missing=[r[:4] for r in rows if int(r[4])==0]
    if len(missing)!=264:raise ValueError('Expected the observed264; no new reserve selection')
    output.mkdir(parents=True,exist_ok=False)
    for shard in range(3):(output/f'cases-{shard}.tsv').write_text(''.join('\t'.join(r)+'\n' for r in missing[shard::3]))
    (output/'cases.tsv').write_text(''.join('\t'.join(r)+'\n' for r in missing))
    (output/'baseline.tsv').write_text(''.join('\t'.join(r)+'\n' for r in rows if int(r[4])==0))


def run(work,cases,output):
    if output.exists():raise ValueError('Use fresh diagnostic output')
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RelationEvaluation',
        str(work/'app/src/main/assets'),str(cases),str(output)],check=True)


def report(shards,output):
    expected=(shards/'cases.tsv').read_text().splitlines();merged={n:[None]*len(expected) for n in ('audit','visible')}
    for i in range(3):
        for name in merged:
            values=(shards/f'output-{i}'/(name+'.tsv')).read_text().splitlines()
            if len(values)!=len(expected[i::3]):raise ValueError('Partial diagnostic')
            for j,line in enumerate(values):
                if '\t'.join(line.split('\t')[:4])!=expected[i+3*j]:raise ValueError('Diagnostic order changed')
                merged[name][i+3*j]=line
    if merged['visible']!=(shards/'baseline.tsv').read_text().splitlines():raise ValueError('Observer changed ordinary lists')
    output.mkdir(parents=True,exist_ok=True)
    for name,rows in merged.items():(output/(name+'.tsv')).write_text(''.join(s+'\n' for s in rows))
    counts=Counter(s.split('\t')[4] for s in merged['audit'])
    value=dict(baseline_revision=BASELINE,cases=len(expected),categories=dict(counts),all_ordinary_lists_match=True,
        source_sha256=digest(Path(__file__)),outputs={n:digest(output/(n+'.tsv')) for n in merged},
        columns='source/context/code/gold/stage/legal/static_bound/ordinary_selected_bound/generated/complete/eligible/first_observed_prefix_loss/teacher_segments',
        limits='Observed old500 only, not independent accuracy. Gold is read only by archive diagnostic instrumentation/after-search DP, not ordinary search decisions; no training comparisons or app hooks. Selected-options DP is an upper bound aggregated from actual visits, not an exhaustive causal account. A missing option can follow prior prefix loss. Static bounds are vocabulary24/64 and character64/HK particles. No reconstructed path is inserted into inference.')
    (output/'summary.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path)
    a=s.add_parser('cases');a.add_argument('output',type=Path)
    a=s.add_parser('run');a.add_argument('work',type=Path);a.add_argument('cases',type=Path);a.add_argument('output',type=Path)
    a=s.add_parser('report');a.add_argument('shards',type=Path);a.add_argument('output',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work)
    elif a.mode=='cases':cases(a.output)
    elif a.mode=='run':run(a.work,a.cases,a.output)
    else:report(a.shards,a.output)
