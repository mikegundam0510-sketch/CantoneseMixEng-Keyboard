package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;
import java.util.*;

public class RecentLearningTest {
    private static final long NOW = 1_790_000_000_000L;
    private static final long WEEK = 7L * 24 * 60 * 60 * 1000;

    @Test public void legacyCountsRemainUnchangedUntilNewSelections() {
        assertEquals(12, RecentLearning.weight(12, null, NOW));
        assertEquals(0, RecentLearning.weight(0, RecentLearning.update(null, NOW, 1), NOW));
    }
    @Test public void recentUseCanOvertakeSimilarLifetimePreferenceThenDecay() {
        String recent = null;
        for (int i = 0; i < 3; i++) recent = RecentLearning.update(recent, NOW, 1);
        assertTrue(RecentLearning.weight(3, recent, NOW) > RecentLearning.weight(10, null, NOW));
        assertTrue(RecentLearning.weight(3, recent, NOW + 8 * WEEK) < RecentLearning.weight(10, null, NOW));
        assertEquals(3, RecentLearning.weight(3, recent, NOW + 100 * WEEK));
        assertEquals(100, RecentLearning.weight(100, null, NOW + 100 * WEEK));
    }
    @Test public void recentLayerHalvesEachWeekAndReselectionRemovesItsContribution() {
        String recent = RecentLearning.update(null, NOW, 2);
        assertEquals(8, RecentLearning.weight(2, recent, NOW));
        assertEquals(5, RecentLearning.weight(2, recent, NOW + WEEK));
        assertEquals(4, RecentLearning.weight(1, RecentLearning.update(recent, NOW, -1), NOW));
        assertNull(RecentLearning.update(RecentLearning.update(null, NOW, 1), NOW, -1));
    }
    @Test public void saturationMalformedHistoryAndClockRollbackAreBounded() {
        String recent = null;
        for (int i = 0; i < 1000; i++) recent = RecentLearning.update(recent, NOW, 1);
        assertEquals(1096, RecentLearning.weight(1000, recent, NOW));
        assertEquals(1096, RecentLearning.weight(1000, recent, NOW - WEEK));
        for (String invalid : Arrays.asList("broken", "1:NaN", "1:Infinity", "-1:10", "1:-4"))
            assertEquals(12, RecentLearning.weight(12, invalid, NOW));
    }
    @Test public void weightedSingleCharacterRankingPreservesTiesAndUsesRecency() {
        String recent = RecentLearning.update(null, NOW, 1);
        List<String> original = Arrays.asList("你", "佢", "我");
        assertEquals(Arrays.asList("佢", "你", "我"), LearningRanker.rank(original,
            word -> RecentLearning.weight(5, word.equals("佢") ? recent : null, NOW)));
        assertEquals(original, LearningRanker.rank(original, word -> 5));
    }
}
