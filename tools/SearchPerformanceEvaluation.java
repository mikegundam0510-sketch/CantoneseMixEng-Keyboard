package hk.kaiboard.android;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Warm, sequential desktop JVM timings; never an Android device latency claim. */
public class SearchPerformanceEvaluation {
    public static void main(String[] args) throws Exception {
        Path assets = Path.of(args[0]);
        DictionaryEngine dictionary = new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
            Files.newBufferedReader(assets.resolve("english.txt")), Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
        QuickDecoder decoder = new QuickDecoder(dictionary, Files.newBufferedReader(assets.resolve("quick_phrases.tsv")),
            Files.newBufferedReader(assets.resolve("hk_phrases.tsv")), Files.newBufferedReader(assets.resolve("cantonese_phrases.tsv")),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))));
        String[] codes = {"ofonaovrmrq", "hmerrrysmlrp", "dpofvivcjutrmyyjvcqnjd", "ofykrmmsydwljpvwjd",
            "vkmmnkmrvordrjjj", "hi".repeat(24)};
        for (int pass = 0; pass < 3; pass++) for (String code : codes) decoder.decode(code, (c,w) -> 0);
        for (String code : codes) {
            double[] times = new double[9];
            for (int pass = 0; pass < times.length; pass++) {
                long start = System.nanoTime();
                List<String> result = decoder.decode(code, (c,w) -> 0);
                times[pass] = (System.nanoTime() - start) / 1e6;
                if (result.size() > 20 || new HashSet<>(result).size() != result.size()) throw new AssertionError(code);
                for (String value : result) if (dictionary.matchQuickCodes(code, value).isEmpty()) throw new AssertionError(value);
            }
            Arrays.sort(times);
            System.out.printf(Locale.ROOT, "%s\t%d\t%.3f\t%.3f%n", code, code.length(), times[4], times[8]);
        }
    }
}
