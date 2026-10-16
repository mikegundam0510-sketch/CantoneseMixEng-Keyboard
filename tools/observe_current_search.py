#!/usr/bin/env python3
"""Observe current-parent first lost prefixes and final rivals; never change search."""
import argparse
import json
from pathlib import Path
import subprocess

import observe_joint_ranking as previous
from clean_ranking_observations import cases, run, merge, merge_shadow
from export_prefix_pairs import OBSERVER
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

BASELINE = '3aa8870'
DATA = ROOT / 'tools/data/current_search'

HOOKS = r'''
    static String observedSource, observedContext, observedCode, observedGold;
    static int observedPosition;
    static final List<SearchCheckpoint> checkpoints=new ArrayList<>();
    static final class SearchCheckpoint {
        int position,rank;boolean lost;String positive;
        List<String> rivals=new ArrayList<>();List<Double> margins=new ArrayList<>();
        double violation(){return -Collections.min(margins);}
    }
    private boolean continuable(String text,int pos) {
        return text.codePointCount(0,text.length())>=2 && !text.equals(observedGold)
            && observedGold.startsWith(text)
            && !dictionary.matchQuickCodes(observedCode.substring(pos),observedGold.substring(text.length())).isEmpty();
    }
    private List<Path> prune(List<Path> input,String context,List<Token> following,ModelScoreCache cache) {
        List<Path> result=currentSearchPrune(input,context,following,cache);
        int pos=observedPosition;
        if(pos<=0||pos>=observedCode.length()||input.size()<=BEAM)return result;
        List<Path> raw=new ArrayList<>(input);raw.sort(Comparator.comparingDouble((Path p)->p.score).reversed());
        Set<String> seen=new HashSet<>();List<Path> unique=new ArrayList<>();
        for(Path p:raw)if(seen.add(p.text))unique.add(p);
        if(unique.size()<=BEAM)return result;
        Path positive=null;int rank=0;
        for(int i=0;i<unique.size();i++)if(continuable(unique.get(i).text,pos)) {
            positive=unique.get(i);rank=i+1;break;
        }
        if(positive==null)return result;
        SearchCheckpoint point=new SearchCheckpoint();point.position=pos;point.rank=rank;
        point.positive=positive.text;point.lost=true;
        for(Path p:result)if(continuable(p.text,pos)){point.lost=false;break;}
        List<Path> rivals=new ArrayList<>();rivals.add(unique.get(0));
        for(int i:new int[]{0,BEAM-1})if(i<result.size())rivals.add(result.get(i));
        seen.clear();
        for(Path rival:rivals)if(!observedGold.startsWith(rival.text)&&seen.add(rival.text)) {
            point.rivals.add(rival.text);point.margins.add(positive.score-rival.score);
        }
        if(!point.rivals.isEmpty())checkpoints.add(point);
        return result;
    }
    static void writePrefixPairs(BufferedWriter out)throws IOException {
        List<SearchCheckpoint> ordered=new ArrayList<>(checkpoints);
        ordered.sort(Comparator.comparingInt((SearchCheckpoint p)->p.lost?0:1)
            .thenComparingInt(p->p.position).thenComparing(p->p.positive));
        List<SearchCheckpoint> chosen=new ArrayList<>();
        if(!ordered.isEmpty()) {
            SearchCheckpoint first=ordered.get(0);chosen.add(first);
            ordered.removeIf(p->p.position==first.position&&p.positive.equals(first.positive));
            ordered.sort(Comparator.comparingDouble(SearchCheckpoint::violation).reversed()
                .thenComparingInt(p->p.position).thenComparing(p->p.positive));
            if(!ordered.isEmpty())chosen.add(ordered.get(0));
        }
        for(SearchCheckpoint p:chosen)for(int i=0;i<p.rivals.size();i++)out.write(String.join("\t",
            observedSource,observedContext,observedCode,observedGold,Integer.toString(p.position),
            p.positive,p.rivals.get(i),Double.toHexString(p.margins.get(i)),
            p.lost?"lost":"survived",Integer.toString(p.rank))+"\n");
    }
'''


def prepare(work):
    previous.BASELINE = BASELINE
    previous.prepare(work)
    quick = work / 'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    text = quick.read_text()
    changes = {
        OBSERVER: HOOKS,
        '        observePrefixes(input,following,baselineScores);\n': '',
        '    private List<Path> prune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {':
        '    private List<Path> currentSearchPrune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {',
    }
    for old, new in changes.items():
        if text.count(old) != 1:
            raise ValueError('Current observation anchor changed: ' + old[:80])
        text = text.replace(old, new)
    quick.write_text(text)
    subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(work/'app/src/main/java'),
                    '-d', str(work/'classes'), str(work/'RelationEvaluation.java')], check=True)


def split(work):
    if work.exists():
        raise ValueError('Preserve existing current-parent observations')
    rows = cases()
    work.mkdir(parents=True)
    (work/'reused').mkdir()
    for name in ('pools.tsv', 'prefix.tsv', 'visible.tsv'):
        (work/'reused'/name).write_text('')
    for i in range(3):
        (work/f'train-{i}.tsv').write_text(''.join('\t'.join(r)+'\n' for r in rows[i::3]))
    (work/'reuse.json').write_text(json.dumps(dict(reused=0, new=len(rows),
        training_sha256=digest(ROOT/'tools/data/clean_ranking/train.tsv'),
        baseline_revision=BASELINE, policy='All clean TRAIN re-decoded using current-parent assets; no old-margin cache.'), indent=2)+'\n')


def merge_current(work, output):
    import clean_ranking_observations as old
    old.BASELINE = BASELINE
    merge(work, output)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('prepare', 'split', 'run', 'merge', 'prepare-shadow', 'run-shadow', 'merge-shadow'))
    p.add_argument('work', type=Path)
    p.add_argument('--cases', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--pools', type=Path)
    a = p.parse_args()
    if a.mode == 'prepare': prepare(a.work)
    elif a.mode == 'split': split(a.work)
    elif a.mode == 'merge': merge_current(a.work, a.output)
    elif a.mode == 'prepare-shadow':
        import observe_structured_training as shadow
        shadow.BASELINE=BASELINE
        shadow.prepare(a.work)
    elif a.mode == 'run-shadow': run(a.work,a.cases,a.output,kind='shadow')
    elif a.mode == 'merge-shadow':
        merge_shadow(a.work,a.pools,a.output)
        path=a.output/'observation.json'
        note=json.loads(path.read_text());note['parent_revision']=BASELINE
        path.write_text(json.dumps(note,indent=2)+'\n')
    else: run(a.work, a.cases, a.output)
