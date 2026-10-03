package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.util.*;

public class CustomPhrasesTest {
    @Test public void manualPhrasesRoundTripWithChineseEmojiAndSpaces() {
        LinkedHashMap<String, String> input = new LinkedHashMap<>();
        input.put("HK", "香港 🇭🇰"); input.put("hello", "Hello there!");
        Map<String, String> output = CustomPhrases.parse(CustomPhrases.save(input));
        assertEquals("香港 🇭🇰", output.get("hk")); assertEquals("Hello there!", output.get("hello"));
    }
    @Test public void rejectsDelimitersInvalidCodesAndUnboundedEntries() {
        assertFalse(CustomPhrases.valid("hk1", "香港"));
        assertFalse(CustomPhrases.valid("", "香港"));
        assertFalse(CustomPhrases.valid("a".repeat(25), "香港"));
        assertFalse(CustomPhrases.valid("hk", " "));
        assertFalse(CustomPhrases.valid("hk", "a\nb"));
        assertFalse(CustomPhrases.valid("hk", "a\tb"));
        assertFalse(CustomPhrases.valid("hk", "a\rb"));
        assertFalse(CustomPhrases.valid("hk", "a".repeat(101)));
        assertTrue(CustomPhrases.parse("corrupt\nhk1\tinvalid\nhk\t香港\n").size() == 1);
    }
    @Test public void savedCollectionIsBoundedAndDuplicateKeysAreNormalized() {
        StringBuilder input = new StringBuilder();
        for (int i = 0; i < 150; i++) input.append("x").append((char)('a' + i / 26)).append((char)('a' + i % 26)).append("\t香港\n");
        assertEquals(100, CustomPhrases.parse(input.toString()).size());
        assertEquals("新", CustomPhrases.parse("hk\t舊\nHK\t新").get("hk"));
    }
}
