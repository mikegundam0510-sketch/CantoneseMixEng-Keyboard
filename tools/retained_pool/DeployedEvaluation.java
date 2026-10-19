package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Compile against the archived, unmodified deployed parent classes. */
public final class DeployedEvaluation {
    private static Path assets;
    private static Reader a(String n) throws IOException {return Files.newBufferedReader(assets.resolve(n));}
    public static void main(String[] args) throws Exception {
        assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
        QuickDecoder q=new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),a("hk_chat_phrases.tsv"),
            CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))),
            SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))),
            PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))),
            PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))),
            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))),
            DirectCodeGenerator.load(Files.newInputStream(assets.resolve("code_generator.b64"))));
        int count=0;
        try(BufferedReader in=Files.newBufferedReader(Path.of(args[1]));BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
            String line;while((line=in.readLine())!=null) {
                String[] f=line.split("\t",-1);if(f.length!=3)throw new IllegalArgumentException("Context/code only inputs required");
                List<String> values=q.decode(f[2],(c,w)->0,f[1]);
                if(values.size()>20 || values.size()!=new HashSet<>(values).size())throw new AssertionError("Parent display bounds");
                for(String t:values)if(d.matchQuickCodes(f[2],t).isEmpty())throw new AssertionError("Parent code alignment");
                out.write(line+"\t"+String.join("|",values)+"\n");
                if(++count%100==0)System.out.println("parent_decoded="+count);
            }
        }
        System.out.println("actual_deployed_cases="+count);
    }
}
