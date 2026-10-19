package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Actual complete dual-provider decoder. Inputs have no gold text or ranks. */
public final class FusionIntegratedEvaluation {
    static Path assets;
    static Reader a(String name) throws IOException {return Files.newBufferedReader(assets.resolve(name));}
    static QuickDecoder decoder(DictionaryEngine d, boolean expanded) throws Exception {
        return decoder(d, DirectCodeGenerator.load(Files.newInputStream(assets.resolve("code_generator.b64"))),
            expanded ? DirectCodeGenerator.load(Files.newInputStream(assets.resolve("expanded_generator.b64"))) : null);
    }
    static QuickDecoder decoder(DictionaryEngine d, DirectCodeGenerator legacy, DirectCodeGenerator expanded) throws Exception {
        return new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),a("hk_chat_phrases.tsv"),
            CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))),
            SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))),
            PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))),
            PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))),
            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))),legacy,expanded);
    }
    public static void main(String[] args) throws Exception {
        assets=Path.of(args[0]);DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
        boolean expanded=args[3].equals("candidate");
        QuickDecoder q=decoder(d,expanded);
        Set<Integer> additions=DirectCodeGenerator.load(Files.newInputStream(assets.resolve("expanded_generator.b64")))
            .charactersAddedSince(DirectCodeGenerator.load(Files.newInputStream(assets.resolve("code_generator.b64"))));
        if(additions.size()!=245)throw new AssertionError("Unexpected new-character mask");
        int count=0;
        try(BufferedReader in=Files.newBufferedReader(Path.of(args[1]));BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
            String line;while((line=in.readLine())!=null) {
                String[] f=line.split("\t",-1);if(f.length!=5)throw new IllegalArgumentException("Target-free inputs required");
                List<String> parent=f[3].isEmpty()?Collections.emptyList():Arrays.asList(f[3].split("\\|"));
                List<String> result=q.decode(f[2],(c,w)->0,f[1]);
                int pinned=Math.min(18,parent.size());
                if(expanded && (!result.subList(0,pinned).equals(parent.subList(0,pinned))))throw new AssertionError("Deployed first18 changed");
                if(!expanded && !parent.isEmpty() && !result.equals(parent))throw new AssertionError("Actual current parent differs from cached display");
                if(result.size()>20 || new HashSet<>(result).size()!=result.size())throw new AssertionError("Display bounds");
                int added=0;
                for(String text:result) {
                    if(d.matchQuickCodes(f[2],text).isEmpty())throw new AssertionError("Inexact code");
                    if(!parent.contains(text)) {
                        added++;
                        if(expanded && !text.codePoints().anyMatch(additions::contains))throw new AssertionError("Expanded old-only offer");
                    }
                }
                if(expanded && added>2)throw new AssertionError("Too many new offers");
                out.write(String.join("\t",Arrays.copyOf(f,3))+"\t"+String.join("|",result)+"\n");
                if(++count%100==0)System.out.println("full_decoded="+count);
            }
        }
        System.out.println("full_cases="+count+" deployed_first18=true exact=true new_characters_only=true max20=true");
    }
}
