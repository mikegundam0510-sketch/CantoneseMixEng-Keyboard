package hk.kaiboard.android;

import org.junit.Test;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class NextSuggestionsTest {
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    private static Reader asset(String name) throws Exception {
        return Files.newBufferedReader(Path.of("src/main/assets", name), StandardCharsets.UTF_8);
    }
    @Test public void regression() throws Exception { run(); }
    public static void main(String[] args) throws Exception { run(); }
    private static void run() throws Exception {
        DictionaryEngine dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        QuickDecoder decoder = new QuickDecoder(dictionary,
            new StringReader("onfvnd\t你好\t1000000000\nonfvv\t你好嗎\t9000\nvnonfvnd\t我你好\t1\n"), asset("hk_phrases.tsv"));
        check(decoder.nextSuggestions("研究", 12).contains("一下"), "Hong Kong phrase continuation");
        check(decoder.nextSuggestions("研究一", 12).contains("下"), "chained continuation");
        check(decoder.nextSuggestions("你", 12).contains("好"), "single character continuation");
        check(decoder.nextSuggestions("我你", 12).get(0).equals("好"), "longer matching context ranks first");
        check(decoder.nextSuggestions("你好", 12).contains("嗎"), "only uncommitted suffix offered");
        for (String context : List.of("", "研究 ", "研究。", "abc", "123", "𠮷"))
            check(decoder.nextSuggestions(context, 12).isEmpty(), "no guesses across boundaries: " + context);
        check(decoder.nextSuggestions(null, 12).isEmpty(), "null editor context");
        check(decoder.nextSuggestions("你", 0).isEmpty(), "zero limit");
        List<String> suggestions = decoder.nextSuggestions("你", 1);
        check(suggestions.size() == 1, "bounded candidate count");
        check(new HashSet<>(decoder.nextSuggestions("你", 12)).size() == decoder.nextSuggestions("你", 12).size(), "deduplicated tails");
        check(dictionary.lookup("onf", false, true, false).contains("你"), "full Cangjie code remains intact");
        System.out.println("Post-commit suggestion regression checks passed");
    }
}
