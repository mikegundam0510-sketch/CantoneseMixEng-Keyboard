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
    @Test public void expiresEachItemAtItsOwnDeadline() {
        long[] now = {0};
        SessionClipboard c = new SessionClipboard(() -> now[0]);
        c.setMaxAgeMillis(60000); c.add("first",true);
        now[0] = 30000; c.add("second",true);
        assertEquals(30000, c.nextExpiryMillis());
        now[0] = 60000;
        assertEquals(java.util.Collections.singletonList("second"), c.items());
        assertEquals(30000, c.nextExpiryMillis());
        now[0] = 90000;
        assertTrue(c.items().isEmpty()); assertEquals(-1, c.nextExpiryMillis());
    }
    @Test public void refreshDoesNotExtendExistingExpiryAndDisabledTimerKeepsItems() {
        long[] now = {0};
        SessionClipboard c = new SessionClipboard(() -> now[0]);
        c.setMaxAgeMillis(60000); c.add("same",true);
        now[0] = 59000; c.add("same",true);
        assertEquals(1000, c.nextExpiryMillis());
        now[0] = 60000; assertTrue(c.items().isEmpty());
        c.setMaxAgeMillis(0); c.add("keep",true);
        now[0] += 3600000;
        assertEquals(java.util.Collections.singletonList("keep"), c.items());
        assertEquals(-1, c.nextExpiryMillis());
        c.setMaxAgeMillis(60000); assertTrue(c.items().isEmpty());
    }
}
