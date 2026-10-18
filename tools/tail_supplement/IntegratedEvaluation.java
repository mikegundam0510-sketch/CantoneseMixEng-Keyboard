package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Full candidate decoder, using only context/code. Gold-free five-column inputs. */
public final class IntegratedEvaluation {
    static Path assets;
    static Reader a(String name)throws Exception{return Files.newBufferedReader(assets.resolve(name));}
    static QuickDecoder decoder(DictionaryEngine d,DirectCodeGenerator generator)throws Exception {
        return new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),a("hk_chat_phrases.tsv"),
            CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))),
            SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))),
            PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))),
            PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))),
            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))),generator);
    }
    public static void main(String[] args)throws Exception {
        assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
        QuickDecoder q=decoder(d,DirectCodeGenerator.load(Files.newInputStream(assets.resolve("code_generator.b64"))));
        int count=0;
        try(BufferedReader in=Files.newBufferedReader(Path.of(args[1]));BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
            String line;while((line=in.readLine())!=null) {
                String[] f=line.split("\t",-1);if(f.length!=5)throw new IllegalArgumentException("Target-free inputs required");
                List<String> parent=f[3].isEmpty()?Collections.emptyList():Arrays.asList(f[3].split("\\|"));
                List<String> result=q.decode(f[2],(c,w)->0,f[1]);
                int pinned=Math.min(18,parent.size());
                if(!result.subList(0,pinned).equals(parent.subList(0,pinned)))throw new AssertionError("Native first18 changed");
                if(result.size()>20||new HashSet<>(result).size()!=result.size())throw new AssertionError("Display bound");
                int added=0;for(String text:result) {
                    if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact candidate");
                    if(!parent.contains(text))added++;
                }
                if(added>2)throw new AssertionError("Supplement bound");
                out.write(String.join("\t",Arrays.copyOf(f,3))+"\t"+String.join("|",result)+"\n");
                if(++count%100==0)System.out.println("full_decoded="+count);
            }
        }
        System.out.println("full_cases="+count+" pinned18=true exact=true max20=true");
    }
}
