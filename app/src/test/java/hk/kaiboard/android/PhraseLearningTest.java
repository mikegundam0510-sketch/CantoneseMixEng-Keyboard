package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public class PhraseLearningTest {
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static Reader asset(String name) throws Exception {
        return Files.newBufferedReader(Path.of("src/main/assets", name), StandardCharsets.UTF_8);
    }
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"),
            asset("cantonese_phrases.tsv"), OfflineLanguageModel.load(Files.newInputStream(Path.of("src/main/assets/language_model.b64"))));
    }
    private static String code(String text) {
        StringBuilder code = new StringBuilder();
        for (int cp : text.codePoints().toArray())
            code.append(dictionary.quickCodesFor(new String(Character.toChars(cp))).get(0));
        return code.toString();
    }
    @Test public void selectedPhraseAndItsKnownPartsAreLearnedOnce() {
        InputCandidate selected = InputCandidate.chinese(dictionary, code("唔該晒"), "唔該晒");
        List<String> words = PhraseLearning.selectedWords("", selected, decoder::knownWord, true, false);
        assertTrue(words.contains("唔該")); assertTrue(words.contains("唔該晒"));
        assertEquals(new HashSet<>(words).size(), words.size());
    }
    @Test public void singleCharacterAndPredictionTailCompleteAKnownWord() {
        InputCandidate tail = new InputCandidate("", Collections.singletonList(new InputCandidate.Segment("", "晒", false)), false);
        assertTrue(PhraseLearning.selectedWords("唔該", tail, decoder::knownWord, true, false).contains("唔該晒"));
        assertTrue(PhraseLearning.selectedWords("唔", InputCandidate.chinese(dictionary, code("該"), "該"),
            decoder::knownWord, true, false).contains("唔該"));
    }
    @Test public void disabledLearningAndProtectedFieldsDoNotReadVocabulary() {
        InputCandidate choice = InputCandidate.chinese(dictionary, code("香港"), "香港");
        assertTrue(PhraseLearning.selectedWords("", choice, w -> { throw new AssertionError(); }, false, false).isEmpty());
        assertTrue(PhraseLearning.selectedWords("", choice, w -> { throw new AssertionError(); }, true, true).isEmpty());
    }
    @Test public void englishTranslationAndPunctuationBreakPhraseLearning() {
        Set<String> vocabulary = new HashSet<>(Arrays.asList("香港", "秘密"));
        assertTrue(PhraseLearning.selectedWords("香", InputCandidate.english("port", "港"), vocabulary::contains, true, false).isEmpty());
        assertTrue(PhraseLearning.selectedWords("香", InputCandidate.translation("port", "港"), vocabulary::contains, true, false).isEmpty());
        assertTrue(PhraseLearning.selectedWords("香，", InputCandidate.chinese(dictionary, code("港"), "港"), vocabulary::contains, true, false).isEmpty());
        assertTrue(PhraseLearning.selectedWords("私人", InputCandidate.chinese(dictionary, "abcd", "未收錄句子"), w -> false, true, false).isEmpty());
    }
    @Test public void commonHongKongWordsRemainReachableByExactCodes() {
        for (String word : Arrays.asList("兩餸飯", "凍檸茶", "搭小巴", "早啲瞓", "得閒再傾", "辛苦晒", "聽日見")) {
            assertTrue(word, decoder.knownWord(word));
            assertTrue(word, decoder.decode(code(word), (c,w) -> w.equals(word) ? 5 : 0, "").contains(word));
        }
    }
    @Test public void chosenExactPhraseMovesFirstWithoutChangingZeroHistoryOrder() {
        String input = "hiru"; // Both 得嘅 and 我嘅 match these actual bundled codes.
        List<String> baseline = decoder.decode(input, (c,w) -> 0, "");
        assertTrue(baseline.contains("得嘅")); assertTrue(baseline.contains("我嘅"));
        String chosen = baseline.get(0).equals("得嘅") ? "我嘅" : "得嘅";
        assertNotEquals(chosen, baseline.get(0));
        List<String> ranked = decoder.decode(input, (c,w) -> w.equals(chosen) ? 10 : 0, "");
        assertEquals(chosen, ranked.get(0));
        for (String word : ranked) assertFalse(dictionary.matchQuickCodes(input, word).isEmpty());
        assertEquals(baseline, decoder.decode(input, (c,w) -> 0, ""));
    }
    @Test public void preferredHongKongContinuationMovesAheadWithinMatchingPrefix() throws Exception {
        QuickDecoder local = new QuickDecoder(dictionary, new StringReader(
            code("唔該晒") + "\t唔該晒\t30000\n" + code("唔該你") + "\t唔該你\t30000\n"));
        List<String> defaults = local.nextSuggestions("唔該", 12);
        String chosen = defaults.get(defaults.size()-1);
        assertEquals(chosen, local.nextSuggestions("唔該", 12, w -> w.equals("唔該" + chosen) ? 50 : 0).get(0));
        assertEquals(defaults, local.nextSuggestions("唔該", 12, w -> 0));
        assertTrue(local.nextSuggestions("唔該。", 12, w -> 100).isEmpty());
    }
    @Test public void keysPreserveLegacyCharacterFormatAndSeparatePhraseCounts() {
        assertEquals("QC:of:你", LearningRanker.key("OF", true, true, "你"));
        assertEquals("W:唔該晒", PhraseLearning.key("唔該晒"));
        assertNotEquals(PhraseLearning.key("香港"), LearningRanker.key(code("香港"), true, true, "香港"));
    }
}
