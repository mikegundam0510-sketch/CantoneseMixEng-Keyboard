package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public class RecentPhraseRankingTest {
    private static DictionaryEngine dictionary;
    private static OfflineLanguageModel model;
    private static QuickDecoder updated;
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(Path.of("src/main/assets", name), StandardCharsets.UTF_8);
    }
    private static QuickDecoder decoder() throws IOException {
        return new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"),
            asset("cantonese_phrases.tsv"), model);
    }
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        model = OfflineLanguageModel.load(Files.newInputStream(Path.of("src/main/assets/language_model.b64")));
        updated = decoder();
    }
    @AfterClass public static void release() { dictionary = null; model = null; updated = null; }
    @Test public void recentPreferenceChangesAmbiguousPhraseAndFadesBackToLifetimeOrder() {
        long now = 1_790_000_000_000L;
        List<String> original = updated.decode("hiru", (c,w) -> 0);
        String chosen = original.get(0).equals("得嘅") ? "我嘅" : "得嘅";
        String other = original.get(0);
        String recent = RecentLearning.update(null, now, 3);
        List<String> lifetime = updated.decode("hiru", (c,w) -> w.equals(chosen) ? 3 : w.equals(other) ? 10 : 0);
        assertEquals(other, lifetime.get(0));
        assertEquals(chosen, updated.decode("hiru", (c,w) -> RecentLearning.weight(
            w.equals(chosen) ? 3 : w.equals(other) ? 10 : 0, w.equals(chosen) ? recent : null, now)).get(0));
        long later = now + 8L * 7 * 24 * 60 * 60 * 1000;
        assertEquals(other, updated.decode("hiru", (c,w) -> RecentLearning.weight(
            w.equals(chosen) ? 3 : w.equals(other) ? 10 : 0, w.equals(chosen) ? recent : null, later)).get(0));
    }
    @Test public void everydayCantoneseAndWrittenExamplesDoNotRegress() {
        String[][] examples = {
            {"ofonaovrmrq", "你今日食咗咩"}, {"mtjnmmy", "研究一下"},
            {"hidpmtjnmmy", "我想研究一下"}, {"ofgbhibhmy", "你幫我睇下"},
            {"hispayesfmm", "我聽日返緊工"}, {"rryogbhiskye", "唔該幫我改返"},
            {"hinjhumbymmy", "等陣先再試下"}, {"hidporkbkbtcod", "我想知有冇其他"},
            {"hiypogyqrihu", "我諗住遲啲先"}, {"hirdspaatoa", "我哋聽日開會"},
            {"vkmmnkmrvordrjjj", "收工又可以踩單車"}, {"hidprdrjjj", "我想踩單車"},
            {"hispardrjjj", "我聽日踩單車"}, {"hirdmrvo", "我哋可以"}
        };
        for (String[] example : examples) {
            List<String> values = updated.decode(example[0], (c,w) -> 0);
            assertEquals(example[0], example[1], values.get(0));
            for (String value : values) assertFalse(dictionary.matchQuickCodes(example[0], value).isEmpty());
        }
    }
}
