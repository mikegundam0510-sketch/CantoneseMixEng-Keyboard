package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import org.junit.*;
import static org.junit.Assert.*;

public class EnglishEngineTest {
    private EnglishEngine engine;
    @Before public void setup() throws Exception {
        engine = new EnglishEngine(new StringReader("# words\nhello\nhelp\nthe\nphone\nkeyboard\nhello\nnot a word\n"));
    }
    @Test public void completionsPreserveCaseAndSkipExactWord() {
        assertEquals(Arrays.asList("Hello", "Help"), engine.suggest("He", false));
        assertTrue(engine.suggest("HEL", false).contains("HELLO"));
        assertFalse(engine.suggest("hello", true).contains("hello"));
        assertEquals(5, engine.size());
    }
    @Test public void spellingIncludesTranspositionMissingAndExtraLetters() {
        assertTrue(engine.suggest("teh", true).contains("the"));
        assertTrue(engine.suggest("helo", true).contains("hello"));
        assertTrue(engine.suggest("helllo", true).contains("hello"));
        assertTrue(engine.suggest("phine", true).contains("phone"));
        assertTrue(engine.suggest("TEH", true).contains("THE"));
    }
    @Test public void disabledSuggestionsDoNotCorrectAndSearchIsBounded() {
        assertFalse(engine.suggest("teh", false).contains("the"));
        assertEquals(Collections.emptyList(), engine.suggest("", true));
        assertEquals(Collections.emptyList(), engine.suggest("a".repeat(48), true));
        assertFalse(engine.suggest("xxhello", true).contains("hello"));
        assertEquals(Collections.emptyList(), engine.suggest("zz", true));
    }
    @Test public void outputIsUniqueAndLimitedWithLargeVocabulary() throws Exception {
        StringBuilder words = new StringBuilder();
        for (char c = 'a'; c <= 'z'; c++) words.append("test").append(c).append('\n');
        List<String> output = new EnglishEngine(new StringReader(words.toString())).suggest("test", true);
        assertEquals(8, output.size()); assertEquals(8, new HashSet<>(output).size());
    }
}
