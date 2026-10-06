package hk.kaiboard.android;

import java.nio.file.*;
import java.io.*;
import java.util.*;

/** Exact production decoder evaluation; no Android or neural runtime required. */
public final class ContextAccuracy {
    public static void main(String[] args) throws Exception {
        Path assets = Path.of(args[0]);
        var d = new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
            Files.newBufferedReader(assets.resolve("english.txt")), Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
        var q = new QuickDecoder(d, Files.newBufferedReader(assets.resolve("quick_phrases.tsv")),
            Files.newBufferedReader(assets.resolve("hk_phrases.tsv")), Files.newBufferedReader(assets.resolve("cantonese_phrases.tsv")),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))));
        List<String[]> cases = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of(args[1]))) {
            if (line.isBlank() || line.startsWith("#")) continue;
            String[] f = line.split("\t", -1);
            String expected = args[2].equals("heldout") ? f[2] : f[1];
            String code = args[2].equals("heldout") ? f[1] : f.length > 2 ? f[2] : expected.codePoints()
                .mapToObj(cp -> d.quickCodesFor(new String(Character.toChars(cp))).get(0)).reduce("", String::concat);
            cases.add(new String[]{f[0], code, expected});
        }
        // Warm classes and decoder; these host CPU figures are not Android acceptance.
        for (String[] c : cases) q.decode(c[1], (code, word) -> 0, c[0]);
        for (String[] c : cases) {
            long start = System.nanoTime();
            List<String> candidates = q.decode(c[1], (code, word) -> 0, c[0]);
            double ms = (System.nanoTime() - start) / 1e6;
            for (String candidate : candidates)
                if (d.matchQuickCodes(c[1], candidate).isEmpty()) throw new AssertionError("Unreachable candidate");
            String choices = candidates.stream().map(SemanticPrompt::quote).reduce((a,b) -> a + "," + b).orElse("");
            System.out.println("{\"context\":" + SemanticPrompt.quote(c[0]) + ",\"code\":" + SemanticPrompt.quote(c[1])
                + ",\"expected\":" + SemanticPrompt.quote(c[2]) + ",\"milliseconds\":" + ms + ",\"candidates\":[" + choices + "]}");
        }
    }
}
