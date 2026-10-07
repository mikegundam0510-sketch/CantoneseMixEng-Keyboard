package hk.kaiboard.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Controlled preference-change scenarios, not observed user accuracy. */
public final class PersonalRankingEvaluation {
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
        Set<String> codes = new TreeSet<>();
        for (String line : Files.readAllLines(assets.resolve("hk_phrases.tsv"), StandardCharsets.UTF_8)) {
            String[] fields = line.split("\t");
            if (fields.length == 3 && fields[0].length() >= 3 && fields[0].length() <= 6) codes.add(fields[0]);
        }
        long now = 1_790_000_000_000L, later = now + 8L * 7 * 24 * 60 * 60 * 1000;
        String recent = RecentLearning.update(null, now, 3);
        int cases = 0, before = 0, after = 0, restored = 0;
        try (BufferedWriter out = Files.newBufferedWriter(Path.of(args[1]), StandardCharsets.UTF_8)) {
            out.write("code\tprevious_preference\trecent_preference\told_top1\tnew_top1\tafter_8_weeks_top1\n");
            for (String code : codes) {
                List<String> base = decoder.decode(code, (c,w) -> 0);
                List<String> known = new ArrayList<>();
                for (String value : base) if (decoder.knownWord(value)) known.add(value);
                if (known.size() < 2) continue;
                String old = known.get(0), chosen = known.get(1);
                List<String> lifetime = decoder.decode(code, (c,w) -> w.equals(old) ? 10 : w.equals(chosen) ? 3 : 0);
                List<String> current = decoder.decode(code, (c,w) -> RecentLearning.weight(
                    w.equals(old) ? 10 : w.equals(chosen) ? 3 : 0, w.equals(chosen) ? recent : null, now));
                List<String> faded = decoder.decode(code, (c,w) -> RecentLearning.weight(
                    w.equals(old) ? 10 : w.equals(chosen) ? 3 : 0, w.equals(chosen) ? recent : null, later));
                if (lifetime.get(0).equals(chosen)) before++;
                if (current.get(0).equals(chosen)) after++;
                if (faded.get(0).equals(old)) restored++;
                for (String value : current)
                    if (dictionary.matchQuickCodes(code, value).isEmpty()) throw new AssertionError(value);
                out.write(String.join("\t", code, old, chosen, lifetime.get(0), current.get(0), faded.get(0))+"\n");
                if (++cases == 20) break;
            }
        }
        if (cases != 20 || after != 20 || restored != 20)
            throw new AssertionError("Personal ranking acceptance failed");
        System.out.printf("simulated_cases=%d lifetime_only_recent_top1=%d recent_layer_top1=%d lifetime_restored_after_8_weeks=%d%n",
            cases, before, after, restored);
    }
}
