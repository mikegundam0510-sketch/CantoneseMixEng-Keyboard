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
    @Test public void singleModePreferencesImproveWholeSentenceRanking() {
        String target = "等你哋確認下", input = code(target);
        List<String> baseline = decoder.decode(input, (c,w) -> 0, "");
        Map<String,Integer> counts = new HashMap<>();
        for (int attempt=0;attempt<3;attempt++) {
            SingleSelectionHistory history = new SingleSelectionHistory();
            String remaining = input;
            for (InputCandidate.Segment segment : InputCandidate.chinese(dictionary,input,target).segments) {
                InputCandidate choice = new InputCandidate(segment.code,Collections.singletonList(segment),false);
                String context = history.contextFor(remaining, "");
                counts.merge(LearningRanker.key(segment.code,true,true,segment.text),1,Integer::sum);
                for (String word : PhraseLearning.selectedWords(context,choice,decoder::knownWord,true,false))
                    counts.merge(PhraseLearning.key(word),1,Integer::sum);
                String next = remaining.substring(segment.code.length());
                history.confirm(remaining,choice,next,context,null); remaining=next;
            }
        }
        List<String> learned = decoder.decode(input,(c,w) -> counts.getOrDefault(
            LearningRanker.isLearnable(w) ? LearningRanker.key(c,true,true,w) : PhraseLearning.key(w),0), "");
        assertEquals(target,learned.get(0));
        assertTrue(baseline.indexOf(target) >= learned.indexOf(target));
        assertFalse(counts.containsKey(PhraseLearning.key(target)));
        for (String key : counts.keySet()) if(key.startsWith("W:")) assertTrue(decoder.knownWord(key.substring(2)));
    }
    @Test public void explicitCorrectionCanReverseLegacyWholeWordPreference() {
        String input="hiru";
        long now=1_790_000_000_000L;
        String rejected=CorrectionLearning.update(null,now,1);
        rejected=CorrectionLearning.update(rejected,now,-.25);
        rejected=CorrectionLearning.update(rejected,now,1);
        final int oldWeight=CorrectionLearning.adjust(100,rejected,now);
        final int newWeight=RecentLearning.weight(2,RecentLearning.update(null,now,2),now);
        assertEquals("得嘅",decoder.decode(input,(c,w) -> w.equals("得嘅") ? 100 : 0,"").get(0));
        List<String> corrected=decoder.decode(input,(c,w) -> w.equals("得嘅") ? oldWeight : w.equals("我嘅") ? newWeight : -2,"");
        assertEquals("我嘅",corrected.get(0));
        for(String value : corrected) assertFalse(dictionary.matchQuickCodes(input,value).isEmpty());
    }
}
