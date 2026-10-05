package hk.kaiboard.android;

import org.junit.Test;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class MixedAutocorrectBoundaryTest {
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    @Test public void regression() throws Exception { run(); }
    public static void main(String[] args) throws Exception { run(); }
    private static void run() throws Exception {
        EnglishEngine english = new EnglishEngine(Files.newBufferedReader(Path.of("src/main/assets/english.txt"), StandardCharsets.UTF_8));
        for (String word : List.of("effect", "EFFECT", "aqhibrandxyz")) {
            StringBuilder composing = new StringBuilder();
            for (char next : word.toCharArray()) {
                String code = composing.toString();
                // A strong contextual Chinese repair must not turn an unfinished English prefix into committed Chinese.
                InputCandidate repaired = new InputCandidate(code, List.of(new InputCandidate.Segment(code,"涼皮",false)), true);
                InputCandidate winner = ChineseAutocorrect.choose(code, "星期五", List.of(), List.of(repaired), text -> 100.0);
                if (winner != null) check(!ChineseAutocorrect.allowTrigger(true, false, true), "mixed English prefix is protected: " + code);
                composing.append(next);
            }
            check(composing.toString().equals(word), "complete original casing preserved");
        }
        int count;
        try (java.util.stream.Stream<String> lines = Files.lines(Path.of("src/main/assets/english.txt"), StandardCharsets.UTF_8)) {
            count = (int) lines.filter(EnglishEngine::validWord).count();
        }
        check(count >= 30000, "expanded offline vocabulary");
        for (String word : List.of("environment", "notification", "effect", "permission", "Bluetooth", "Qobuz", "Eletech", "AQHI"))
            check(english.likelyEnglish(word, List.of()), "expanded word recognized: " + word);
        check(english.suggest("qob", List.of(), false).contains("Qobuz"), "brand completion casing");
        check(english.suggest("enviro", List.of(), false).contains("environment"), "expanded prefix completion");
        List<String> original = english.suggest("eff", List.of(), true);
        check(original.get(0).equals("eff"), "literal stays first");
        english.suggest("custom", List.of("custombrand"), false);
        check(!english.suggest("custom", List.of(), false).contains("custombrand"), "personal removal clears indexed cache");
        long started = System.nanoTime();
        for (int i = 0; i < 1000; i++) { english.likelyEnglish("hellp", List.of()); english.suggest("hellp", List.of(), true); }
        check((System.nanoTime() - started) / 1_000_000 < 3000, "bounded repeated search latency");
        check(english.likelyEnglish("effect", List.of()), "effect is English at confirmation");
        check(english.likelyEnglish("EFFECT", List.of()), "uppercase effect is English");
        check(english.suggest("eff", List.of(), true).contains("effect"), "effect completion");
        check(ChineseAutocorrect.allowTrigger(false, false, true), "Chinese correction still allowed at space boundary");
        check(ChineseAutocorrect.allowTrigger(true, true, true), "explicit Chinese input retains continuation correction");
        check(ChineseAutocorrect.allowTrigger(true, false, false), "Chinese-only mode retains continuation correction");
        System.out.println("Mixed autocorrection boundary checks passed");
    }
}
