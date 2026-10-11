"""Trace a fixed gold dataset using a temporary JVM decoder; never runs in the app.

Activate the Android environment first, then:
  python3 tools/decoder_diagnostics.py --revision 21ff17a --cases tools/lm_heldout_cases.tsv --output /tmp/decoder.tsv
The archived engine and assets belong to the requested commit. Instrumentation
only observes completed target paths and their final raw ranks; it cannot prove
why an earlier prefix was lost or that an unfamiliar sentence is invalid.
Requires the hk.cantonesemixeng.keyboard namespace (0.6.39 onward).
"""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile

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
  QuickDecoder decoder=new QuickDecoder(dictionary,Files.newBufferedReader(assets.resolve("quick_phrases.tsv")),Files.newBufferedReader(assets.resolve("hk_phrases.tsv")),Files.newBufferedReader(assets.resolve("cantonese_phrases.tsv")),OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))));
  try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
   out.write("# context\tcode\ttarget\tdisplayed_rank\traw_final_rank\treason\tcandidates\n");
   for(String line:Files.readAllLines(Path.of(args[1]))) {
    if(line.isEmpty()||line.startsWith("#"))continue;
    String[] fields=line.split("\t",-1);
    if(fields.length!=3)throw new IllegalArgumentException("Expected context, code and target");
    if(!fields[1].matches("[a-zA-Z]{3,48}"))throw new IllegalArgumentException("Expected 3 to 48 code letters");
    QuickDecoder.diagnosticTarget=fields[2];QuickDecoder.diagnosticGenerated=false;QuickDecoder.diagnosticRawRank=0;
    List<String> candidates=decoder.decode(fields[1],(code,word)->0,fields[0]);
    int rank=candidates.indexOf(fields[2])+1;
    String reason=rank==1?"first":rank>0?"ranked_later":QuickDecoder.diagnosticRawRank>20?"outside_twenty":QuickDecoder.diagnosticRawRank>0?"confidence_filtered":QuickDecoder.diagnosticGenerated?"completed_path_pruned":"not_generated";
    out.write(line+"\t"+rank+"\t"+QuickDecoder.diagnosticRawRank+"\t"+reason+"\t"+String.join("|",candidates)+"\n");
   }
  }
 }
}
'''


def instrument(source):
    hooks = {
        '    private static final int BEAM = 48;': '''    static String diagnosticTarget = "";
    static boolean diagnosticGenerated;
    static int diagnosticRawRank;
    private static final int BEAM = 48;''',
        'target.add(new Path(prefix.text + choice.getKey(), prefix.score + score + wordBonus + bonus));': '''String joined=prefix.text+choice.getKey();
                        if(pos+length==code.length() && joined.equals(diagnosticTarget)) diagnosticGenerated=true;
                        target.add(new Path(joined,prefix.score+score+wordBonus+bonus));''',
        '        List<Path> completed = prune(lattice.get(code.length()));': '''        List<Path> diagnosticPaths=lattice.get(code.length());
        diagnosticPaths.sort(Comparator.comparingDouble((Path path)->path.score).reversed());
        Set<String> diagnosticSeen=new HashSet<>();diagnosticRawRank=0;
        for(Path path:diagnosticPaths) if(diagnosticSeen.add(path.text) && path.text.equals(diagnosticTarget)) {
            diagnosticRawRank=diagnosticSeen.size();break;
        }
        List<Path> completed = prune(lattice.get(code.length()));''',
    }
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
    args = parser.parse_args()
    cases, output = args.cases.resolve(), args.output.resolve()
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.revision + '^{commit}'], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', 'archive', revision, 'app/src/main/java', 'app/src/main/assets'], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='decoder-diagnostics-') as directory:
        work = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as data:
            data.extractall(work, filter='data')
        engine = work / SOURCE
        engine.write_text(instrument(engine.read_text()), encoding='utf-8')
        driver = work / 'DecoderDiagnostics.java'
        driver.write_text(DRIVER, encoding='utf-8')
        classes = work / 'classes'
        subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(work/'app/src/main/java'), '-d', str(classes), str(driver)], check=True)
        subprocess.run(['java', '-Xmx1g', '-cp', str(classes), PACKAGE+'.DecoderDiagnostics', str(work/'app/src/main/assets'), str(cases), str(output)], check=True)
    print('Diagnosed commit', revision, '->', output)


if __name__ == '__main__':
    main()
