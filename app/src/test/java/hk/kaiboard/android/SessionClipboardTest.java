package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;

public class SessionClipboardTest {
    @Test public void deduplicatesAndBoundsNewestFirst() {
        SessionClipboard c = new SessionClipboard();
        for (int i=0;i<12;i++) c.add("clip"+i,true);
        assertEquals(10,c.items().size()); assertEquals("clip11",c.items().get(0));
        c.add("clip5",true); assertEquals(10,c.items().size()); assertEquals("clip5",c.items().get(0));
        c.items().clear(); assertEquals(10,c.items().size());
    }
    @Test public void restrictedEditorReplacesHistoryAndClearRemovesAll() {
        SessionClipboard c = new SessionClipboard(); c.add("old",true); c.add("current",false);
        assertEquals(java.util.Collections.singletonList("current"),c.items());
        c.clear(); assertTrue(c.items().isEmpty());
    }
    @Test public void rejectsEmptyAndOversizedTextAndAllowsDeletion() {
        SessionClipboard c = new SessionClipboard(); c.add(" ",true); c.add("x".repeat(20001),true);
        assertTrue(c.items().isEmpty()); c.add("hello",true); c.remove("hello"); assertTrue(c.items().isEmpty());
    }
}
