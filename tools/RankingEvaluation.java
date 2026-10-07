package hk.kaiboard.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Fixed held-out conversation evaluation; excludes UI and personal history. */
public final class RankingEvaluation {
    private static Path assets;
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(assets.resolve(name), StandardCharsets.UTF_8);
    }
    public static void main(String[] args) throws Exception {
        assets = Path.of(args[0]);
        DictionaryEngine dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"),
            asset("english.txt"), asset("character_frequencies.tsv"));
        QuickDecoder decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"),
            asset("hk_phrases.tsv"), asset("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))));
        int count = 0, top1 = 0, top5 = 0, reachable = 0;
        double reciprocalRank = 0;
        long started = System.nanoTime();
        try (BufferedWriter out = Files.newBufferedWriter(Path.of(args[2]), StandardCharsets.UTF_8)) {
            for (String line : Files.readAllLines(Path.of(args[1]), StandardCharsets.UTF_8)) {
                if (line.isEmpty() || line.startsWith("#")) continue;
                String[] fields = line.split("\t", -1);
                List<String> values = decoder.decode(fields[1], (code, word) -> 0, fields[0]);
                int rank = values.indexOf(fields[2]) + 1;
                count++;
                if (rank == 1) top1++;
                if (rank > 0 && rank <= 5) top5++;
                if (rank > 0) { reachable++; reciprocalRank += 1.0 / rank; }
                for (String value : values)
                    if (dictionary.matchQuickCodes(fields[1], value).isEmpty())
                        throw new AssertionError("Inexact candidate: " + fields[1] + " / " + value);
                out.write(line + "\t" + rank + "\t" + String.join("|", values) + "\n");
            }
        }
        System.out.printf(Locale.ROOT, "cases=%d top1=%d top5=%d top20=%d mrr=%.6f elapsed_ms=%d%n",
            count, top1, top5, reachable, reciprocalRank / count, (System.nanoTime()-started)/1000000);
    }
}
