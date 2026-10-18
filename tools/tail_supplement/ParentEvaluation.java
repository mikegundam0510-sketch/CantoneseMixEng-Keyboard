package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Compile against the actual unmodified parent classes; no targets in input. */
public final class ParentEvaluation {
    static Path assets;static Reader a(String n)throws Exception{return Files.newBufferedReader(assets.resolve(n));}
    public static void main(String[] args)throws Exception {
        assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
        QuickDecoder q=new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),a("hk_chat_phrases.tsv"),
            CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))),
            SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))),
            PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))),
            PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))),
            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));
        int count=0;
        try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
            for(String line:Files.readAllLines(Path.of(args[1]))) {
                String[] f=line.split("\t",-1);if(f.length!=3)throw new IllegalArgumentException("Target-free parent input required");
                List<String> result=q.decode(f[2],(c,w)->0,f[1]);
                if(result.size()>20||new HashSet<>(result).size()!=result.size())throw new AssertionError("Parent display");
                for(String text:result)if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Parent exact code");
                out.write(line+"\t"+String.join("|",result)+"\n");if(++count%100==0)System.out.println("parent_decoded="+count);
            }
        }
    }
}
