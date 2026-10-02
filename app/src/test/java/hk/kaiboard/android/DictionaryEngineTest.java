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
            new InputStreamReader(new FileInputStream("src/main/assets/english.txt"), StandardCharsets.UTF_8));
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
}
