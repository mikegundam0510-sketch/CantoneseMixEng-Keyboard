package hk.kaiboard.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.junit.*;
import static org.junit.Assert.*;

/** Exercise imported code coverage and prediction weights through the real engines. */
public class WordsHkImportTest {
    private static final String MARKER = "# words.hk public-domain supplement;";
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static OfflineLanguageModel model;
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(Path.of("src/main/assets", name), StandardCharsets.UTF_8);
    }
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        model = OfflineLanguageModel.load(Files.newInputStream(Path.of("src/main/assets/language_model.b64")));
        decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"), asset("cantonese_phrases.tsv"), model);
    }
    @AfterClass public static void release() { dictionary = null; decoder = null; model = null; }

    @Test public void everySupplementedPhraseHasExactExistingCharacterCodes() throws Exception {
        boolean supplement = false; int checked = 0;
        for (String line : Files.readAllLines(Path.of("src/main/assets/cantonese_phrases.tsv"))) {
            if (line.startsWith(MARKER)) { supplement = true; continue; }
            if (!supplement || line.isEmpty() || line.startsWith("#")) continue;
            String[] f = line.split("\t");
            assertFalse(line, dictionary.matchQuickCodes(f[0], f[1]).isEmpty());
            assertTrue(line, decoder.knownWord(f[1]));
            assertTrue(line, Integer.parseInt(f[2]) <= 3000);
            checked++;
        }
        assertTrue("Imported data must actually be present", checked > 10000);
    }

    @Test public void characterPriorsAreBoundedAndNeverRemoveAnEntry() throws Exception {
        Map<String, Integer> base = new HashMap<>();
        boolean supplement = false; int checked = 0;
        for (String line : Files.readAllLines(Path.of("src/main/assets/character_frequencies.tsv"))) {
            if (line.startsWith(MARKER)) { supplement = true; continue; }
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] f = line.split("\t"); int value = Integer.parseInt(f[1]);
            if (!supplement) { base.put(f[0], value); continue; }
            int old = Math.max(1, base.getOrDefault(f[0], 1));
            assertTrue(line, value >= Math.round(old / 1.3) && value <= Math.round(old * 1.3));
            assertFalse(line, dictionary.quickCodesFor(f[0]).isEmpty());
            checked++;
        }
        assertTrue(checked > 1000);
        assertTrue(dictionary.frequency("係") >= 25000);
        assertFalse(dictionary.quickCodesFor("㤀").isEmpty());
    }

    @Test public void laterFrequencySupplementUpdatesPredictionsIndependentOfSourceOrder() throws Exception {
        String small = "ofvd\t你好\t1\nofrd\t你哋\t100\n";
        String large = "ofvd\t你好\t1000000000\n";
        QuickDecoder after = new QuickDecoder(dictionary, new StringReader(small), null, new StringReader(large), model);
        QuickDecoder before = new QuickDecoder(dictionary, new StringReader(large), null, new StringReader(small), model);
        assertEquals(before.nextSuggestions("你", 12), after.nextSuggestions("你", 12));
        assertEquals("好", after.nextSuggestions("你", 12).get(0));
        assertEquals(2, after.nextSuggestions("你", 12).size());
    }

    @Test public void observedCorpusEvidenceCrossesTokenBoundariesWithoutDuplicatingVariants() throws Exception {
        QuickDecoder unobserved = new QuickDecoder(dictionary, new StringReader("rcmm\t返工\t10\t0\n"));
        QuickDecoder observed = new QuickDecoder(dictionary,
            new StringReader("rcmm\t返工\t10\t300\nrcm\t返工\t10\t300\n"));
        double gain = observed.languageScore("返", "工") - unobserved.languageScore("返", "工");
        assertTrue(gain > 0 && gain < .75);
        assertEquals(observed.languageScore("", "返工"),
            observed.languageScore("", "返") + observed.languageScore("返", "工"), 1e-9);
        assertEquals(unobserved.languageScore("返，", "工"), observed.languageScore("返，", "工"), 1e-9);
        assertEquals(observed.languageScore("", "工"), observed.languageScore("返A", "工"), 1e-9);
    }

    @Test public void importedWordsRemainAvailableForExplicitLocalLearning() {
        for (String word : List.of("返工", "收工", "功課", "老細", "八達通", "尾班車", "月台"))
            assertTrue(word, decoder.knownWord(word));
        String word = "尾班車";
        StringBuilder input = new StringBuilder();
        for (int cp : word.codePoints().toArray())
            input.append(dictionary.quickCodesFor(new String(Character.toChars(cp))).stream()
                .filter(c -> c.length() == 2).findFirst().orElseThrow());
        String code = input.toString();
        InputCandidate chosen = InputCandidate.chinese(dictionary, code, word);
        assertTrue(PhraseLearning.selectedWords("", chosen, decoder::knownWord, true, false).contains(word));
        assertTrue(PhraseLearning.selectedWords("", chosen, decoder::knownWord, true, true).isEmpty());
    }
}
