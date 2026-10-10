package hk.kaiboard.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.junit.*;
import static org.junit.Assert.*;

public class ContinuousClauseRankingTest {
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(Path.of("src/main/assets", name), StandardCharsets.UTF_8);
    }
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"),
            asset("cantonese_phrases.tsv"), OfflineLanguageModel.load(Files.newInputStream(Path.of("src/main/assets/language_model.b64"))));
    }
    @AfterClass public static void release() { dictionary = null; decoder = null; }
    @Test public void reportedContinuousSentenceRanksFirstWithoutPersonalHistory() {
        String code = "dpofvivcjutrmyyjvcqnjd";
        List<String> result = decoder.decode(code, (c,w) -> 0);
        assertEquals("想你繼續完善下連續打字", result.get(0));
        assertEquals(result.size(), new HashSet<>(result).size());
        for (String candidate : result) assertFalse(dictionary.matchQuickCodes(code, candidate).isEmpty());
    }
    @Test public void requestPatternsGeneralizeToOtherSubjectsAndActions() throws Exception {
        for (String line : Files.readAllLines(Path.of("../tools/continuous_clause_cases.tsv"), StandardCharsets.UTF_8)) {
            String[] fields = line.split("\\t", -1);
            List<String> result = decoder.decode(fields[1], (c,w) -> 0, fields[0]);
            assertEquals(fields[1], fields[2], result.get(0));
            for (String candidate : result) assertFalse(dictionary.matchQuickCodes(fields[1], candidate).isEmpty());
        }
    }
    @Test public void requestAndActionEvidenceCrossesWordBoundaries() {
        for (String[] parts : new String[][]{{"想你", "繼續"}, {"想佢", "幫我"}, {"修改", "下"}, {"檢查", "下"}}) {
            assertEquals(decoder.languageScore("", parts[0]+parts[1]),
                decoder.languageScore("", parts[0]) + decoder.languageScore(parts[0], parts[1]), 1e-9);
            assertEquals(decoder.languageScore("", parts[1]), decoder.languageScore(parts[0]+"，", parts[1]), 1e-9);
        }
    }
}
