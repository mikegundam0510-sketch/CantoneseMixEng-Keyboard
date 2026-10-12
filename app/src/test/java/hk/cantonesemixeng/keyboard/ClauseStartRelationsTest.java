package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;

public class ClauseStartRelationsTest {
    @Test public void explicitSubjectsGeneralizeAcrossPredicatesAndAdverbs() {
        for (String text : new String[]{"你交咗", "佢寫緊", "我哋簽過", "你哋啱啱洗咗", "我今日已經完成咗"})
            assertEquals(text, 1, ClauseStartRelations.score("", text), 0);
        assertEquals(0, ClauseStartRelations.score("", "係交咗"), 0);
        assertEquals(0, ClauseStartRelations.score("", "你唔交咗"), 0);
        assertEquals(0, ClauseStartRelations.score("", "某個人名交咗"), 0);
    }

    @Test public void focusAndEmbeddedCopulasRemainLicensed() {
        for (String text : new String[]{"係我交咗", "係佢哋整理咗", "你話係佢交咗", "我想問你簽咗",
                "我唔記得係交咗", "我唔知係寫緊", "係咪做咗", "你係咪洗咗"})
            assertEquals(text, 1, ClauseStartRelations.score("", text), 0);
        for (String text : new String[]{"你係老師", "係香港人", "係幾多錢", "我唔知係邊個"})
            assertEquals(text, 0, ClauseStartRelations.score("", text), 0);
    }

    @Test public void scoreIsIndependentOfLatticeTokenAndEditorSplits() {
        for (String text : new String[]{"你今日已經交咗錢未", "係我洗咗衫", "我唔記得係交咗表未",
                "我想問你哋完成咗文件未", "你交咗錢，我哋寫緊信"})
            for (int at = 0; at <= text.length(); at++)
                assertEquals(text + " at " + at, ClauseStartRelations.score("", text),
                    ClauseStartRelations.score("", text.substring(0, at))
                        + ClauseStartRelations.score(text.substring(0, at), text.substring(at)), 0);
    }

    @Test public void boundariesResetAndTruncatedHeadsAreNotReinvented() {
        assertEquals(1, ClauseStartRelations.score("佢話，", "你交咗錢"), 0);
        assertEquals(1, ClauseStartRelations.score("Zoom ", "你交咗錢"), 0);
        assertEquals(0, ClauseStartRelations.score("今日開會之後我想問你交", "咗錢"), 0);
        String capped = "我唔記得係你今日已經又交";
        assertEquals(12, capped.codePointCount(0, capped.length()));
        assertEquals(0, ClauseStartRelations.score(capped, "咗"), 0);
        assertEquals(1, ClauseStartRelations.score("今日開會之後我想問你交，", "你交咗錢"), 0);
        assertEquals(0, ClauseStartRelations.score("𠮷某人", "你交咗"), 0);
        assertEquals(1, ClauseStartRelations.score("", "你交咗咗錢未未"), 0);
    }

    @Test public void cacheGateNeverHidesAnActualHanContinuationCue() {
        for (String head : new String[]{"你", "我哋", "係佢", "你話係我", "我唔記得係", "我想問你"})
            for (String time : new String[]{"", "今日", "啱啱", "今日已經"})
                for (String verb : new String[]{"交", "完成", "簽", "付"}) {
                    String text = head + time + verb + "咗";
                    for (int at = 0; at < text.length(); at++) {
                        String prefix = text.substring(0, at), next = text.substring(at);
                        if (ClauseStartRelations.score(prefix, next) > 0)
                            assertTrue(prefix, ClauseStartRelations.pending(prefix));
                    }
                }
        assertFalse(ClauseStartRelations.pending("想你繼續"));
        assertFalse(ClauseStartRelations.pending("你交咗"));
        assertFalse(ClauseStartRelations.pending("某個人"));
        assertTrue(ClauseStartRelations.pending("我唔記得係"));
    }
}
