package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;

/** Verify Python mask facts against the actual unchanged Android dictionary. */
public final class NativeCodeCheck {
    public static void main(String[] args)throws Exception {
        Path assets=Path.of(args[0]);
        DictionaryEngine d=new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
            Files.newBufferedReader(assets.resolve("english.txt")),Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
        int characters=0,choices=0,cases=0;
        for(String line:Files.readAllLines(Path.of(args[1]))) {
            String[] f=line.split("\t",-1);Set<String> expected=new TreeSet<>();
            if(!f[1].isEmpty())expected.addAll(Arrays.asList(f[1].split(",")));
            if(!expected.equals(new TreeSet<>(d.quickCodesFor(f[0]))))throw new AssertionError("Dictionary code facts differ");
            characters++;choices+=expected.size();
        }
        for(String line:Files.readAllLines(Path.of(args[2]))) {
            String[] f=line.split("\t",-1);List<String> actual=d.matchQuickCodes(f[1],f[2]);
            if(actual.isEmpty()||!String.join("",actual).equals(f[1]))throw new AssertionError("Illegal training alignment");
            cases++;
        }
        System.out.println("vocabulary_code_facts="+characters+" legal_choices="+choices+" actual_dictionary_alignments="+cases+" exact=true");
    }
}
