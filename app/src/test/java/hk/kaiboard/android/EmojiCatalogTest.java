package hk.kaiboard.android;
import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class EmojiCatalogTest {
    private static EmojiCatalog catalog;
    @BeforeClass public static void load() throws Exception {
        catalog = new EmojiCatalog(new InputStreamReader(new FileInputStream("src/main/assets/emoji.tsv"),StandardCharsets.UTF_8));
    }
    @Test public void completeGroupedList() { assertEquals(3773,catalog.size()); assertEquals(9,catalog.groupCount()); }
    @Test public void compoundEmojiDeleteAsOneUnit() {
        for(String emoji : new String[]{"😀","❤️","👍🏽","🇭🇰","👨‍👩‍👧‍👦","1️⃣"})
            assertEquals(emoji,emoji.length(),catalog.deletionUnits("hello"+emoji));
        assertEquals(1,catalog.deletionUnits("你好")); assertEquals(0,catalog.deletionUnits(""));
    }
    @Test public void deletionOnlyRemovesLastAdjacentEmoji() { assertEquals("🇭🇰".length(),catalog.deletionUnits("😀🇭🇰")); }
    @Test public void recentEmojiDeduplicateAndRejectUnknownValues() {
        String value = catalog.remember("","😀"); value = catalog.remember(value,"❤️"); value = catalog.remember(value,"😀");
        assertEquals(2,catalog.recent(value).size()); assertEquals("😀",catalog.recent(value).get(0).symbol);
        assertTrue(catalog.recent("private sentence").isEmpty());
    }
}
