"""Trace a fixed gold dataset using a temporary JVM decoder; never runs in the app.

Activate the Android environment first, then:
  python3 tools/decoder_diagnostics.py --revision 21ff17a --cases tools/lm_heldout_cases.tsv --output /tmp/decoder.tsv
The archived engine and assets belong to the requested commit. Instrumentation
observes option eligibility and prefix survival without changing search decisions.
Prefix events explain observed path losses, not sentence validity; alternative
tokenizations can bypass an individual lost prefix.
Requires the hk.cantonesemixeng.keyboard namespace (0.6.39 onward).
"""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import shutil

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = 'hk.cantonesemixeng.keyboard'
SOURCE = 'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'

DRIVER = r'''
package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public final class DecoderDiagnostics {
 public static void main(String[] args)throws Exception {
  Path assets=Path.of(args[0]);
  DictionaryEngine dictionary=new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),Files.newBufferedReader(assets.resolve("english.txt")),Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
  QuickDecoder decoder=new QuickDecoder(dictionary,Files.newBufferedReader(assets.resolve("quick_phrases.tsv")),Files.newBufferedReader(assets.resolve("hk_phrases.tsv")),Files.newBufferedReader(assets.resolve("cantonese_phrases.tsv")),OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64")))__PHRASE_ARGS__);
  int count=0;
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   out.write("# context\tcode\ttarget\tdisplayed_rank\traw_final_rank\treason\tcandidates\texact_code\tprefix_events\n");
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    if(line.isEmpty()||line.startsWith("#"))continue;
    String[] fields=line.split("\t",-1);
    if(fields.length!=3)throw new IllegalArgumentException("Expected context, code and target");
    if(!fields[1].matches("[a-zA-Z]{3,48}"))throw new IllegalArgumentException("Expected 3 to 48 code letters");
    QuickDecoder.diagnosticTarget=fields[2];QuickDecoder.diagnosticGenerated=false;QuickDecoder.diagnosticRawRank=0;QuickDecoder.diagnosticEvents.clear();
    boolean exact=!dictionary.matchQuickCodes(fields[1],fields[2]).isEmpty();
    List<String> candidates=decoder.decode(fields[1],(code,word)->0,fields[0]);
    for(String candidate:candidates) if(dictionary.matchQuickCodes(fields[1],candidate).isEmpty())
        throw new AssertionError("Inexact candidate: "+fields[1]+" / "+candidate);
    int rank=candidates.indexOf(fields[2])+1;
    String reason=rank==1?"first":rank>0?"ranked_later":QuickDecoder.diagnosticRawRank>20?"outside_twenty":QuickDecoder.diagnosticRawRank>0?"confidence_filtered":QuickDecoder.diagnosticGenerated?"completed_path_pruned":"not_generated";
    out.write(line+"\t"+rank+"\t"+QuickDecoder.diagnosticRawRank+"\t"+reason+"\t"+String.join("|",candidates)+"\t"+exact+"\t"+String.join(";",QuickDecoder.diagnosticEvents)+"\n");
    if(++count%50==0)System.out.println("diagnosed="+count);
   }
  }
 }
}
'''


def instrument(source):
    extended = 'private List<Path> pruneFinal' in source
    hooks = {
        '    private static final int BEAM = 48;': '''    static String diagnosticTarget = "";
    static boolean diagnosticGenerated;
    static int diagnosticRawRank;
    static List<String> diagnosticEvents = new ArrayList<>();
    private static boolean diagnosticGold(String text) {
        return diagnosticTarget.startsWith(text);
    }
    private static void diagnosticBoundary(String phase,int pos,List<Path> before,List<Path> after) {
        Set<String> seen=new HashSet<>(),kept=new HashSet<>();
        for(Path path:after)kept.add(path.text);
        List<Path> sorted=new ArrayList<>(before);
        sorted.sort(Comparator.comparingDouble((Path path)->path.score).reversed());
        int rank=0;double floor=Double.NEGATIVE_INFINITY;
        for(Path path:sorted) if(seen.add(path.text) && ++rank==48) {floor=path.score;break;}
        seen.clear();rank=0;
        for(Path path:sorted) if(seen.add(path.text)) {
            rank++;
            if(diagnosticGold(path.text)) diagnosticEvents.add(phase+","+pos+","+path.text+","+rank+","+kept.contains(path.text)+","+(path.score-floor));
        }
    }
    private static void diagnosticHints(int pos,List<Token> hints) {
        for(Token token:hints)diagnosticEvents.add("H,"+pos+","+token.text);
    }
    private void diagnosticOptions(int pos,int length,String part,List<Path> paths,Map<String,Double> options,List<Token> known) {
        Set<String> seen=new HashSet<>();
        for(Path path:paths) if(diagnosticGold(path.text) && seen.add(path.text)) {
            String remaining=diagnosticTarget.substring(path.text.length());
            int characters=remaining.codePointCount(0,remaining.length());
            for(int size=1;size<=Math.min(8,characters);size++) {
                String word=remaining.substring(0,remaining.offsetByCodePoints(0,size));
                if(dictionary.matchQuickCodes(part,word).isEmpty())continue;
                int wordRank=0;for(Token token:known) {wordRank++;if(token.text.equals(word))break;}
                if(wordRank==0 || !known.get(wordRank-1).text.equals(word))wordRank=0;
                int characterRank=size==1?dictionary.quickCandidates(part).indexOf(word)+1:0;
                diagnosticEvents.add("O,"+pos+","+path.text+","+length+","+word+","+options.containsKey(word)+","+wordRank+","+characterRank);
            }
        }
    }
    private static final int BEAM = 48;''',
        'target.add(new Path(prefix.text + choice.getKey(), prefix.score + score + wordBonus + bonus));': '''String joined=prefix.text+choice.getKey();
                        if(diagnosticGold(joined)) diagnosticEvents.add("G,"+(pos+length)+","+joined+","+prefix.text+","+choice.getKey());
                        if(pos+length==code.length() && joined.equals(diagnosticTarget)) diagnosticGenerated=true;
                        target.add(new Path(joined,prefix.score+score+wordBonus+bonus));''',
        '        List<Path> completed = prune(lattice.get(code.length()));': '''        List<Path> diagnosticPaths=lattice.get(code.length());
        diagnosticPaths.sort(Comparator.comparingDouble((Path path)->path.score).reversed());
        Set<String> diagnosticSeen=new HashSet<>();diagnosticRawRank=0;
        for(Path path:diagnosticPaths) if(diagnosticSeen.add(path.text) && path.text.equals(diagnosticTarget)) {
            diagnosticRawRank=diagnosticSeen.size();break;
        }
        List<Path> completed = prune(lattice.get(code.length()));''',
        '            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);': '''            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);
            diagnosticBoundary("B",pos,lattice.get(pos),paths);
            diagnosticHints(pos,following.get(pos));''',
        '                if (options.isEmpty()) continue;': '''                diagnosticOptions(pos,length,part,paths,options,known);
                if (options.isEmpty()) continue;''',
        '''                if (target.size() > 1024) lattice.set(pos + length,
                    prune(target, context, following.get(pos + length), modelScores));''': '''                if (target.size() > 1024) {
                    List<Path> reduced=prune(target,context,following.get(pos+length),modelScores);
                    diagnosticBoundary("I",pos+length,target,reduced);
                    lattice.set(pos+length,reduced);
                }''',
        '        double bestScore = completed.isEmpty() ? Double.NEGATIVE_INFINITY : completed.get(0).score;': '''        diagnosticBoundary("F",code.length(),lattice.get(code.length()),completed);
        double bestScore = completed.isEmpty() ? Double.NEGATIVE_INFINITY : completed.get(0).score;''',
    }
    if extended:
        before='        List<Path> completed = prune(lattice.get(code.length()));'
        after=hooks.pop(before).replace(before,'        List<Path> completed = pruneFinal(lattice.get(code.length()));')
        hooks['        List<Path> completed = pruneFinal(lattice.get(code.length()));']=after
        before='''                if (target.size() > 1024) lattice.set(pos + length,
                    prune(target, context, following.get(pos + length), modelScores));'''
        hooks.pop(before)
        hooks['''                if (target.size() > 1024) lattice.set(pos + length,
                    pos + length == code.length() && sentenceRanker != null
                        ? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));''']='''                if(target.size()>1024) {
                    List<Path> reduced=pos+length==code.length() && sentenceRanker!=null
                        ? pruneFinal(target) : prune(target,context,following.get(pos+length),modelScores);
                    diagnosticBoundary("I",pos+length,target,reduced);
                    lattice.set(pos+length,reduced);
                }'''
    # B = boundary pruning, I = intermediate compaction, F = final pruning.
    # O = exact gold extension and option membership, G = observed generation,
    # H = existing suffix hints. All observers are temporary archive-only hooks.
    for before, after in hooks.items():
        if source.count(before) != 1:
            raise ValueError('Decoder structure changed; update the diagnostic hook: ' + before)
        source = source.replace(before, after)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--cases', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--working-tree', action='store_true', help='Observe tracked working files instead of an archive')
    args = parser.parse_args()
    cases, output = args.cases.resolve(), args.output.resolve()
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.revision + '^{commit}'], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', 'archive', revision, 'app/src/main/java', 'app/src/main/assets'], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='decoder-diagnostics-') as directory:
        work = Path(directory)
        if args.working_tree:
            for name in subprocess.check_output(['git','ls-files','app/src/main/java','app/src/main/assets'],cwd=ROOT,text=True).splitlines():
                target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        else:
            with tarfile.open(fileobj=io.BytesIO(archive)) as data:
                data.extractall(work, filter='data')
        engine = work / SOURCE
        engine.write_text(instrument(engine.read_text()), encoding='utf-8')
        driver = work / 'DecoderDiagnostics.java'
        phrase_args = ''
        if (work / 'app/src/main/java/hk/cantonesemixeng/keyboard/PhraseLanguageModel.java').exists():
            phrase_args = ',PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),Files.newBufferedReader(assets.resolve("hk_chat_phrases.tsv"))'
        if (work / 'app/src/main/java/hk/cantonesemixeng/keyboard/CandidateRanker.java').exists():
            phrase_args += ',CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64")))'
        if (work / 'app/src/main/assets/word_ranker.b64').exists():
            phrase_args += ',CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64")))'
        if (work / 'app/src/main/assets/sentence_ranker.b64').exists():
            phrase_args += ',SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64")))'
        driver.write_text(DRIVER.replace('__PHRASE_ARGS__', phrase_args), encoding='utf-8')
        classes = work / 'classes'
        subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(work/'app/src/main/java'), '-d', str(classes), str(driver)], check=True)
        subprocess.run(['java', '-Xmx1g', '-cp', str(classes), PACKAGE+'.DecoderDiagnostics', str(work/'app/src/main/assets'), str(cases), str(output)], check=True)
    print('Diagnosed commit', revision, '->', output)


if __name__ == '__main__':
    main()
