package hk.kaiboard.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Simulated explicit Single choices, with identical legacy history in both arms. */
public final class ContextLearningEvaluation {
    private static Path assets;
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(assets.resolve(name),StandardCharsets.UTF_8);
    }
    public static void main(String[] args) throws Exception {
        assets=Path.of(args[0]);
        DictionaryEngine dictionary=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        QuickDecoder decoder=new QuickDecoder(dictionary,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))));
        List<String[]> cases=new ArrayList<>();
        for(String line:Files.readAllLines(Path.of(args[1]),StandardCharsets.UTF_8))
            if(!line.isEmpty() && !line.startsWith("#")) cases.add(line.split("\t",-1));
        Map<String,Integer> legacy=new HashMap<>(), sequences=new LinkedHashMap<>();
        for(int repetition=0;repetition<3;repetition++) for(String[] fields:cases) {
            InputCandidate sentence=InputCandidate.chinese(dictionary,fields[1],fields[2]);
            if(sentence.segments.isEmpty() || dictionary.matchQuickCodes(fields[1],fields[2]).isEmpty()) throw new AssertionError(fields[2]);
            SingleSelectionHistory history=new SingleSelectionHistory();String remaining=fields[1];
            for(InputCandidate.Segment part:sentence.segments) {
                String context=history.contextFor(remaining,fields[0]);
                InputCandidate single=InputCandidate.chinese(dictionary,part.code,part.text);
                legacy.merge(part.code+":"+part.text,1,Integer::sum);
                for(String word:PhraseLearning.selectedWords(context,single,decoder::knownWord,true,false))
                    legacy.merge(PhraseLearning.key(word),1,Integer::sum);
                for(String key:ContextLearning.selectedKeys(context,single,true,false)) {
                    String evicted=ContextLearning.evictionKey(sequences,key);
                    if(evicted!=null) sequences.remove(evicted);
                    sequences.merge(key,1,Integer::sum);
                }
                String next=remaining.substring(part.code.length());
                history.confirm(remaining,single,next,context,null);remaining=next;
            }
        }
        long now=123456789L;Map<String,Integer> weights=new HashMap<>();
        Map<String,Integer> all=new HashMap<>(legacy);all.putAll(sequences);
        for(Map.Entry<String,Integer> e:all.entrySet()) {
            String recent=null;for(int i=0;i<e.getValue();i++) recent=RecentLearning.update(recent,now,1);
            weights.put(e.getKey(),RecentLearning.weight(e.getValue(),recent,now));
        }
        ContextLearning.Preferences preferences=new ContextLearning.Preferences(sequences.keySet(),k->weights.getOrDefault(k,0));
        java.util.function.ToIntBiFunction<String,String> learned=(code,word)->
            weights.getOrDefault(decoder.knownWord(word) ? PhraseLearning.key(word) : code+":"+word,0);
        int[] before=new int[3],after=new int[3];double[] mrr=new double[2];long start=System.nanoTime();
        try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]),StandardCharsets.UTF_8)) {
            for(String[] fields:cases) {
                List<String> old=decoder.decode(fields[1],learned,fields[0]);
                List<String> updated=decoder.decode(fields[1],learned,fields[0],preferences);
                int r1=old.indexOf(fields[2])+1,r2=updated.indexOf(fields[2])+1;
                tally(before,r1);tally(after,r2);
                if(r1>0) mrr[0]+=1.0/r1;if(r2>0) mrr[1]+=1.0/r2;
                for(String value:updated) if(dictionary.matchQuickCodes(fields[1],value).isEmpty()) throw new AssertionError(value);
                out.write(String.join("\t",fields)+"\t"+r1+"\t"+r2+"\t"+String.join("|",updated)+"\n");
            }
        }
        System.out.printf(Locale.ROOT,"cases=%d sequence_records=%d legacy=%s contextual=%s mrr=%.6f/%.6f elapsed_ms=%d%n",
            cases.size(),sequences.size(),Arrays.toString(before),Arrays.toString(after),mrr[0]/cases.size(),mrr[1]/cases.size(),(System.nanoTime()-start)/1000000);
    }
    private static void tally(int[] totals,int rank) {
        if(rank==1) totals[0]++;if(rank>0 && rank<=5) totals[1]++;if(rank>0) totals[2]++;
    }
}
