package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

public class CandidateGlyphFilterTest {
    @Test public void hidesUnsupportedScalarAndWholePhraseWithoutRejectingWords() {
        String rare = new String(Character.toChars(0x31350));
        CandidateGlyphFilter filter = new CandidateGlyphFilter(cp -> cp != 0x31350);
        assertTrue(filter.canDisplay("香港人日常用字"));
        assertTrue(filter.canDisplay("Hello香港"));
        assertFalse(filter.canDisplay(rare));
        assertFalse(filter.canDisplay("香港" + rare));
    }

    @Test public void supportedSupplementaryWindowsAndCombiningCharactersStay() {
        CandidateGlyphFilter filter = new CandidateGlyphFilter(cp -> true);
        assertTrue(filter.canDisplay(new String(Character.toChars(0x31350))));
        assertTrue(filter.canDisplay("丟吞"));
        assertTrue(filter.canDisplay("cafe\u0301"));
        assertTrue(filter.canDisplay("禰\uDB40\uDD00"));
    }

    @Test public void rejectsReplacementAndBrokenSurrogates() {
        CandidateGlyphFilter filter = new CandidateGlyphFilter(cp -> true);
        assertFalse(filter.canDisplay("\ufffd"));
        assertFalse(filter.canDisplay("\ud840"));
        assertFalse(filter.canDisplay("\udc00"));
        assertFalse(filter.canDisplay(""));
    }

    @Test public void cachesNegativeAndPositiveCoverageAndBypassesAscii() {
        AtomicInteger calls = new AtomicInteger();
        CandidateGlyphFilter filter = new CandidateGlyphFilter(cp -> { calls.incrementAndGet(); return cp == '港'; });
        assertTrue(filter.canDisplay("港港"));
        assertTrue(filter.canDisplay("ABC123"));
        assertFalse(filter.canDisplay("字"));
        assertFalse(filter.canDisplay("字"));
        assertEquals(2, calls.get());
    }

    @Test public void cacheIsBounded() {
        AtomicInteger calls = new AtomicInteger();
        CandidateGlyphFilter filter = new CandidateGlyphFilter(cp -> { calls.incrementAndGet(); return true; });
        for (int cp = 0x4e00; cp <= 0x4e00 + 4096; cp++)
            assertTrue(filter.canDisplay(new String(Character.toChars(cp))));
        filter.canDisplay("一");
        assertEquals(4098, calls.get());
    }

    @Test public void reportedQuickCodeKeepsVisibleChoicesInOriginalOrder() throws Exception {
        DictionaryEngine dictionary = new DictionaryEngine(new InputStreamReader(
            new FileInputStream("src/main/assets/cangjie5.base.dict.yaml"), StandardCharsets.UTF_8),
            new InputStreamReader(new FileInputStream("src/main/assets/english.txt"), StandardCharsets.UTF_8),
            new InputStreamReader(new FileInputStream("src/main/assets/character_frequencies.tsv"), StandardCharsets.UTF_8));
        List<String> original = dictionary.quickCandidates("qm");
        Set<Integer> supported = new HashSet<>();
        for (String word : Arrays.asList("捏", "扯", "抵", "扛")) supported.add(word.codePointAt(0));
        CandidateGlyphFilter filter = new CandidateGlyphFilter(supported::contains);
        List<String> visible = new ArrayList<>(original);
        visible.removeIf(word -> !filter.canDisplay(word));
        assertTrue(visible.containsAll(Arrays.asList("捏", "扯", "抵", "扛")));
        assertTrue(visible.size() < original.size());
        List<String> expected = new ArrayList<>();
        for (String word : original) if (supported.contains(word.codePointAt(0))) expected.add(word);
        assertEquals(expected, visible);
        assertEquals(original, dictionary.quickCandidates("qm"));
    }
}
