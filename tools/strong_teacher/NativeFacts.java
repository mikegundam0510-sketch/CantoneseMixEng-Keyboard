package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Export complete one-character code facts, without a frequency/top-N cutoff. */
public final class NativeFacts {
    public static void main(String[] args)throws Exception {
        Path a=Path.of(args[0]);
        DictionaryEngine d=new DictionaryEngine(Files.newBufferedReader(a.resolve("cangjie5.base.dict.yaml")),
            Files.newBufferedReader(a.resolve("english.txt")),Files.newBufferedReader(a.resolve("character_frequencies.tsv")));
        Set<String> characters=new TreeSet<>();
        for(char first='a';first<='z';first++) {
            characters.addAll(d.quickCandidates(String.valueOf(first)));
            for(char last='a';last<='z';last++)characters.addAll(d.quickCandidates(""+first+last));
        }
        int facts=0,choices=0;
        try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[1]))) {
            for(String text:characters) {
                if(text.codePointCount(0,text.length())!=1 || !OfflineLanguageModel.han(text.codePointAt(0)))continue;
                List<String> codes=new ArrayList<>(d.quickCodesFor(text));Collections.sort(codes);
                for(String code:codes)if(d.matchQuickCodes(code,text).isEmpty())throw new AssertionError("Invalid native alias");
                out.write(text+"\t"+String.join(",",codes)+"\n");facts++;choices+=codes.size();
            }
        }
        int cases=0;
        if(args.length==3)for(String line:Files.readAllLines(Path.of(args[2]))) {
            String[] f=line.split("\t",-1);
            if(d.matchQuickCodes(f[0],f[1]).isEmpty())throw new AssertionError("Generated code mismatch");cases++;
        }
        System.out.println("native_characters="+facts+" aliases="+choices+" checked_strings="+cases);
    }
}
