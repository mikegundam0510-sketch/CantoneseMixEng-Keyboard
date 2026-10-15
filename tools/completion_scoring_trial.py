#!/usr/bin/env python3
"""Archived completion-scoring experiments; no app working-tree changes."""
import argparse
from pathlib import Path
import subprocess
from native_phrase_relations import build,run

BASELINE='99708f9'
TAIL=r'''
    private void recoverDisplayedTail(List<String> values,Map<String,Double> scores,String context,
            double reference,Map<String,Map<String,Integer>> cache,java.util.function.ToIntBiFunction<String,String> learned,String code) {
        if(relationRanker==null||!relationRanker.headPromotion()||scores==null||values.size()<=20)return;
        String boundary=values.get(19);double floor=scores.get(boundary),boundaryRaw=relationRanker.rawScore(context,boundary,cache);
        List<String> eligible=new ArrayList<>();PhraseRelationRanker.Evidence boundaryEvidence=null;
        for(String value:new ArrayList<>(values.subList(20,Math.min(36,values.size())))) {
            double raw=relationRanker.rawScore(context,value,cache);
            double score=scores.get(value)+relationRanker.alignedCorrection(raw,reference);
            double lift=relationRanker.correction(raw,boundaryRaw);
            if(score<floor+.25||lift<.5)continue;
            if(boundaryEvidence==null)boundaryEvidence=relationRanker.evidence(context,boundary);
            if(!relationRanker.trustedPromotion(relationRanker.evidence(context,value),boundaryEvidence,lift))continue;
            scores.put(value,score);eligible.add(value);
        }
        eligible.sort(Comparator.comparingDouble((String value)->scores.get(value)).reversed());
        if(eligible.size()>4)eligible=new ArrayList<>(eligible.subList(0,4));
        if(eligible.isEmpty())return;
        List<String> tail=new ArrayList<>(values.subList(5,20));tail.addAll(eligible);
        tail.sort(Comparator.comparingInt((String value)->knownWord(value)?learned.applyAsInt(code,value):0).reversed()
            .thenComparing(Comparator.comparingDouble((String value)->scores.get(value)).reversed()));
        List<String> reordered=new ArrayList<>(values.subList(0,5));reordered.addAll(tail.subList(0,15));
        Set<String> seen=new HashSet<>(reordered);for(String value:values)if(seen.add(value))reordered.add(value);
        values.clear();values.addAll(reordered);
    }
'''
SCORING=r'''
    private List<Path> pruneFinal(List<Path> input,String context,Map<String,Double> cache) {
        if(model==null||sentenceRanker==null||relationRanker==null||!relationRanker.expandedPool())return pruneFinal(input);
        input.sort(Comparator.comparingDouble((Path p)->p.score).reversed());
        List<Path> candidates=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(Path p:input)if(seen.add(p.text)){candidates.add(p);if(candidates.size()==192)break;}
        if(candidates.size()<=128)return candidates;
        List<Path> result=new ArrayList<>(candidates.subList(0,__CORE__));
        List<Path> alternatives=new ArrayList<>(candidates.subList(__CORE__,candidates.size()));
        Map<Path,Double> scores=new IdentityHashMap<>();
        for(Path p:alternatives)scores.put(p,p.score+completedCorrection(context,p.text,cache));
        alternatives.sort(Comparator.comparingDouble((Path p)->scores.get(p)).reversed().thenComparing(p->p.text));
        for(Path p:alternatives){result.add(p);if(result.size()==finalPool)break;}
        return result;
    }
    private double completedCorrection(String context,String text,Map<String,Double> cache) {
        Double value=cache.get(text);
        if(value==null){value=sentenceRanker.score(context,text);if(cache.size()>=512)cache.clear();cache.put(text,value);}
        return value;
    }
'''

def source(text,trial):
    if trial=='tail-guard':
        changes={
            '        Map<String,Double> finalScores=null;':'        double displayedTailReference=0;\n        Map<String,Double> finalScores=null;',
            '                    double reference=relationRanker.rawScore(context,protectedWinner,headFeatures);':
            '                    double reference=relationRanker.rawScore(context,protectedWinner,headFeatures);\n                    displayedTailReference=reference;',
            '        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));':
            '        recoverDisplayedTail(result,finalScores,context,displayedTailReference,headFeatures,learned,code);\n        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));',
            '    /** Existing positive sentence relations outrank a less-supported statistical replacement. */':
            TAIL+'\n    /** Existing positive sentence relations outrank a less-supported statistical replacement. */',
        }
        for before,after in changes.items():
            if text.count(before)!=1:raise ValueError('Tail recovery hook changed: '+before)
            text=text.replace(before,after)
        return text
    if trial=='display36':
        old='Math.min(20,legacy.size())'
        if text.count(old)!=2:raise ValueError('Displayed-pool hook changed')
        return text.replace(old,'Math.min(36,legacy.size())')
    if trial=='raw144':
        old='this.finalPool=relationRanker!=null&&relationRanker.expandedPool()?128:96;'
        if text.count(old)!=1:raise ValueError('Pool hook changed')
        return text.replace(old,old.replace('?128:96','?144:96'))
    changes={
        '        List<List<Token>> following = new ArrayList<>();':
        '        Map<String,Double> completedCorrections=new HashMap<>();\n        List<List<Token>> following = new ArrayList<>();',
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));':
        '? pruneFinal(target,context,completedCorrections) : prune(target, context, following.get(pos + length), modelScores));',
        '        List<Path> completed = pruneFinal(lattice.get(code.length()));':
        '        List<Path> completed = pruneFinal(lattice.get(code.length()),context,completedCorrections);',
        'path.score + sentenceRanker.score(context, path.text)':
        'path.score + completedCorrection(context,path.text,completedCorrections)',
        '    private List<Path> pruneFinal(List<Path> input) {':
        SCORING.replace('__CORE__','1' if trial=='score-cut' else '128')+'\n    private List<Path> pruneFinal(List<Path> input) {',
    }
    if trial=='score-reserve':
        changes['this.finalPool=relationRanker!=null&&relationRanker.expandedPool()?128:96;']=\
            'this.finalPool=relationRanker!=null&&relationRanker.expandedPool()?144:96;'
    for before,after in changes.items():
        if text.count(before)!=1:raise ValueError('Scoring hook changed: '+before)
        text=text.replace(before,after)
    return text

def prepare(work,trial):
    build(work,BASELINE,original=True)
    java=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    java.write_text(source(java.read_text(),trial))
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),
                    '-d',str(work/'classes'),str(work/'RelationEvaluation.java')],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trial',choices=('score-cut','score-reserve','raw144','display36','tail-guard'))
    p.add_argument('work',type=Path);p.add_argument('--cases',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();prepare(a.work,a.trial)
    if a.cases and a.output:run(a.work,a.cases,a.output)
