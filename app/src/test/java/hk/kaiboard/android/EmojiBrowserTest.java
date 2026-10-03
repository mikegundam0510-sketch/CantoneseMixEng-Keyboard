package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class EmojiBrowserTest {
    private static EmojiCatalog catalog;
    @BeforeClass public static void load() throws Exception {
        catalog=new EmojiCatalog(new InputStreamReader(new FileInputStream("src/main/assets/emoji.tsv"),StandardCharsets.UTF_8));
    }
    @Test public void allGroupsHaveJumpTargetsAndScrollMapsToSameGroup() {
        EmojiBrowserModel model=new EmojiBrowserModel(catalog,9,"","");
        assertEquals(10,model.starts.size());
        for(int group=-1;group<9;group++) {
            int position=model.starts.get(group);
            assertTrue(model.rows.get(position).heading);
            assertEquals(group,model.groupAt(position));
        }
        for(int i=0;i<model.rows.size();i++) {
            assertEquals(model.rows.get(i).group,model.groupAt(i));
            assertTrue(model.rows.get(i).entries.size()<=9);
        }
        assertEquals(8,model.groupAt(model.rows.size()-1));
    }
    @Test public void noEmojiIsLostWhenToneFamiliesAreCollapsed() {
        Set<String> reachable=new HashSet<>();
        for(int group=0;group<catalog.groupCount();group++)
            for(EmojiCatalog.Entry entry:catalog.browseGroup(group))
                for(EmojiCatalog.Entry variant:catalog.skinVariants(entry.symbol))reachable.add(variant.symbol);
        assertEquals(catalog.size(),reachable.size());
    }
    @Test public void thumbHasDefaultAndFiveTonesFromAnyVariant() {
        List<EmojiCatalog.Entry> variants=catalog.skinVariants("👍🏽");
        assertEquals(6,variants.size());
        Set<String> symbols=new HashSet<>();for(EmojiCatalog.Entry entry:variants)symbols.add(entry.symbol);
        assertTrue(symbols.containsAll(Arrays.asList("👍","👍🏻","👍🏼","👍🏽","👍🏾","👍🏿")));
    }
    @Test public void toneSelectionPreservesProfessionAndGender() {
        for(EmojiCatalog.Entry entry:catalog.skinVariants("👩🏽‍⚕️")){
            assertTrue(entry.symbol.contains("👩"));assertTrue(entry.symbol.contains("⚕"));
            assertFalse(entry.symbol.contains("👨"));
        }
        assertEquals(6,catalog.skinVariants("👩🏽‍⚕️").size());
        assertEquals(1,catalog.skinVariants("🇭🇰").size());
    }
    @Test public void searchAndNarrowLayoutsKeepRowsBounded() {
        EmojiBrowserModel model=new EmojiBrowserModel(catalog,5,"👍🏽","thumbs up");
        assertFalse(model.rows.isEmpty());
        for(EmojiBrowserModel.Row row:model.rows) {
            assertTrue(row.entries.size()<=5);
            for(EmojiCatalog.Entry e:row.entries)assertTrue(e.name.toLowerCase(Locale.ROOT).contains("thumbs up"));
        }
        assertTrue(new EmojiBrowserModel(catalog,5,"","not-an-emoji-query-xyz").rows.isEmpty());
    }
}
