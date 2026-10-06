package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class DictionaryEngineTest {
    private static DictionaryEngine engine;
    @BeforeClass public static void loadBundledDictionary() throws Exception {
        engine = new DictionaryEngine(new InputStreamReader(new FileInputStream("src/main/assets/cangjie5.base.dict.yaml"), StandardCharsets.UTF_8),
            new InputStreamReader(new FileInputStream("src/main/assets/english.txt"), StandardCharsets.UTF_8),
            new InputStreamReader(new FileInputStream("src/main/assets/character_frequencies.tsv"), StandardCharsets.UTF_8));
    }
    @Test public void writtenAndColloquialCommonCharactersLeadColdStartCandidates() {
        assertEquals("你", engine.quickCandidates("of").get(0));
        assertEquals("食", engine.quickCandidates("ov").get(0));
        assertEquals("咗", engine.quickCandidates("rm").get(0));
        assertEquals("咩", engine.quickCandidates("rq").get(0));
        assertTrue(engine.frequency("你") > engine.frequency("鷦"));
        assertTrue(engine.frequency("食") > engine.frequency("餲"));
    }
    @Test public void dictionaryHasRealCoverage() { assertTrue(engine.entryCount() > 15000); }
    @Test public void quickUsesFirstAndLastCode() {
        assertEquals("of", DictionaryEngine.quickCode("onf"));
        assertEquals("a", DictionaryEngine.quickCode("a"));
        assertEquals("", DictionaryEngine.quickCode(""));
        assertTrue(engine.lookup("of", true, false, true).contains("你"));
        assertTrue(engine.lookup("vd", true, false, false).contains("好"));
        assertTrue(engine.lookup("ha", true, false, false).contains("香"));
        assertTrue(engine.lookup("eu", true, false, false).contains("港"));
    }
    @Test public void cangjieAndQuickCanBeDisabledIndependently() {
        assertTrue(engine.lookup("onf", false, true, false).contains("你"));
        assertFalse(engine.lookup("onf", true, false, false).contains("你"));
        assertFalse(engine.lookup("of", false, true, false).contains("你"));
        assertEquals(Collections.singletonList("of"), engine.lookup("of", false, false, false));
    }
    @Test public void fullCangjieWorksWithoutQuickIncludingReportedCharacter() {
        String[][] cases = {{"onf", "你"}, {"vnd", "好"}, {"hda", "香"},
            {"etcu", "港"}, {"srlb", "屌"}, {"SRLB", "屌"}};
        for (String[] item : cases)
            assertTrue(item[0], engine.lookup(item[0], false, true, false).contains(item[1]));
        assertFalse(engine.lookup("srb", false, true, false).contains("屌"));
        assertFalse(engine.lookup("srlb", false, false, true).contains("屌"));
    }

    @Test public void literalEnglishAndCapitalizationArePreserved() {
        assertTrue(engine.lookup("He", true, true, true).contains("Hello"));
        assertTrue(engine.lookup("HEL", true, true, true).contains("HELLO"));
        assertTrue(engine.lookup("customWord", true, true, true).contains("customWord"));
        assertEquals(Collections.emptyList(), engine.lookup("", true, true, true));
    }
    @Test public void noDuplicateCandidatesAndNoPageLimitInEngine() {
        List<String> result = engine.lookup("aa", true, true, true);
        assertEquals(new HashSet<>(result).size(), result.size());
        assertTrue(engine.lookup("mm", true, true, false).size() > 30);
    }
    @Test public void everyBundledCodeIsReachableByQuick() throws Exception {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream("src/main/assets/cangjie5.base.dict.yaml"), StandardCharsets.UTF_8))) {
            String line; boolean body = false;
            while ((line = reader.readLine()) != null) {
                if (line.equals("...")) { body = true; continue; }
                if (!body) continue;
                String[] fields = line.split("\t");
                if (fields.length >= 2 && fields[1].matches("[a-z]{1,5}"))
                    assertTrue(fields[0], engine.lookup(DictionaryEngine.quickCode(fields[1]), true, false, false).contains(fields[0]));
            }
        }
    }
    @Test public void learningMovesChosenChineseCharacterFirstAndPreservesTies() {
        List<String> ranked = LearningRanker.rank(Arrays.asList("你", "他", "們", "of"), s -> s.equals("們") ? 3 : 0);
        assertEquals(Arrays.asList("們", "你", "他", "of"), ranked);
        assertTrue(LearningRanker.isLearnable("你"));
        assertFalse(LearningRanker.isLearnable("hello"));
        assertFalse(LearningRanker.isLearnable("我的私人句子"));
        assertFalse(LearningRanker.isLearnable("😀"));
        assertFalse(LearningRanker.isLearnable(""));
    }
    @Test public void learningKeysSeparateModesAndNormalizeCodes() {
        assertEquals(LearningRanker.key("OF", true, false, "你"), LearningRanker.key("of", true, false, "你"));
        assertNotEquals(LearningRanker.key("of", true, false, "你"), LearningRanker.key("of", true, true, "你"));
    }

    @Test public void completedDictionaryIncludesHkCharactersAndSupplementaryPlanes() {
        assertTrue(engine.entryCount() >= 130000);
        String[][] cases = {{"rkrd","㗎"}, {"wlln","𠝹"}, {"rgob","𡁻"},
            {"rnn","𠮩"}, {"ribp","𠹌"}, {"iboe","鿿"}, {"rsfr","𫬷"}, {"yjcp","𰻞"}};
        for (String[] item : cases) {
            assertTrue(item[0], engine.lookup(item[0], false, true, false).contains(item[1]));
            String quick = DictionaryEngine.quickCode(item[0]);
            assertTrue(engine.quickCandidates(quick).contains(item[1]));
            assertEquals(Collections.singletonList(quick), engine.matchQuickCodes(quick, item[1]));
        }
        assertTrue(engine.matchQuickCodes("r", "踩").isEmpty());
        // Different regional forms remain accepted.
        assertTrue(engine.lookup("imno",false,true,false).contains("次"));
        assertTrue(engine.lookup("mmno",false,true,false).contains("次"));
    }
    @Test public void everyFullCodeAndItsPrefixesRemainReachable() throws Exception {
        try (BufferedReader reader = new BufferedReader(new FileReader("src/main/assets/cangjie5.base.dict.yaml"))) {
            String line; boolean body = false;
            while ((line = reader.readLine()) != null) {
                if (line.equals("...")) { body = true; continue; }
                if (!body || line.startsWith("#")) continue;
                String[] fields = line.split("\\t");
                if (fields.length < 2 || !fields[1].matches("[a-z]{1,5}")) continue;
                assertTrue(fields[0] + " / " + fields[1],
                    engine.lookup(fields[1],false,true,false).contains(fields[0]));
                for (int n = 1; n <= fields[1].length(); n++)
                    assertTrue(fields[1], engine.hasCangjiePrefix(fields[1].substring(0,n)));
            }
        }
        assertFalse(engine.hasCangjiePrefix(""));
        assertFalse(engine.hasCangjiePrefix("abcdef"));
    }

    @Test public void thirdGenerationAndLegacyCodesRemainReachableAlongsideFifthGeneration() {
        String[][] cases = {{"mwyl", "面"}, {"mwsl", "面"},
            {"qhxm", "捏"}, {"qfbq", "撐"}, {"qfbh", "撐"}};
        for (String[] item : cases) {
            assertTrue(item[0], engine.lookup(item[0], false, true, false).contains(item[1]));
            assertTrue(item[0], engine.quickCandidates(DictionaryEngine.quickCode(item[0])).contains(item[1]));
        }
    }

    @Test public void windowsCodesReachCommonCharactersAndSymbolsInBothModes() {
        String[][] cases = {{"hgi", "丟"}, {"hkr", "吞"}, {"yhhqm", "產"},
            {"yhhhh", "彥"}, {"pim", "勻"}, {"smm", "€"}, {"xm", "═"}};
        for (String[] item : cases) {
            assertTrue(item[0], engine.lookup(item[0], false, true, false).contains(item[1]));
            assertTrue(item[0], engine.lookup(DictionaryEngine.quickCode(item[0]), true, false, false).contains(item[1]));
        }
        assertTrue(engine.lookup("mgi", false, true, false).contains("丟"));
        assertTrue(engine.lookup("mkr", false, true, false).contains("吞"));
        assertFalse(engine.lookup("hgi", false, false, false).contains("丟"));
    }

    @Test public void everyWindowsSupplementCodeReachesTheActualCandidateEngine() throws Exception {
        CandidateEngine candidates = new CandidateEngine(engine, null, null);
        int checked = 0;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                new FileInputStream("../tools/windows_cangjie_compat.tsv"), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("#")) continue;
                String[] fields = line.split("\t");
                assertEquals(2, fields.length);
                String word = fields[0], code = fields[1];
                assertTrue(code + ": " + word, candidates.chinese(code, "", false, false, true, (c,w) -> 0)
                    .stream().anyMatch(candidate -> candidate.text.equals(word)));
                String quick = DictionaryEngine.quickCode(code);
                assertTrue(quick + ": " + word, candidates.chinese(quick, "", false, true, false, (c,w) -> 0)
                    .stream().anyMatch(candidate -> candidate.text.equals(word)));
                checked++;
            }
        }
        assertEquals(4808, checked);
    }

}
