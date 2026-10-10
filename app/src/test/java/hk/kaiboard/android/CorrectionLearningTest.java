package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;
import java.util.*;

public class CorrectionLearningTest {
    private static final long NOW = 1_790_000_000_000L;
    private static InputCandidate candidate(String second) {
        return new InputCandidate("dpof", Arrays.asList(new InputCandidate.Segment("dp", "想", false),
            new InputCandidate.Segment("of", second, false)), false);
    }
    @Test public void recordsOnlyChangedCharacterAndKnownWordAfterReplacement() {
        Set<String> keys = CorrectionLearning.rejectedKeys(candidate("係"), candidate("你"),
            w -> Arrays.asList("想係", "想你").contains(w), true, true, true, false);
        assertEquals(new HashSet<>(Arrays.asList("QC:of:係", "W:想係")), keys);
    }
    @Test public void disabledProtectedSameChoiceAndDifferentCodeDoNotInspectWords() {
        InputCandidate old = candidate("係"), selected = candidate("你");
        assertTrue(CorrectionLearning.rejectedKeys(old, selected, w -> {throw new AssertionError();}, true,true,false,false).isEmpty());
        assertTrue(CorrectionLearning.rejectedKeys(old, selected, w -> {throw new AssertionError();}, true,true,true,true).isEmpty());
        assertTrue(CorrectionLearning.rejectedKeys(old, old, w -> {throw new AssertionError();}, true,true,true,false).isEmpty());
        assertTrue(CorrectionLearning.rejectedKeys(old, InputCandidate.english("other", "word"),
            w -> {throw new AssertionError();},true,true,true,false).isEmpty());
    }
    @Test public void englishTranslationsAndUnlistedSentencesAreNotPersisted() {
        assertTrue(CorrectionLearning.rejectedKeys(candidate("係"), InputCandidate.english("dpof", "word"),
            w -> {throw new AssertionError();},true,true,true,false).isEmpty());
        InputCandidate old = new InputCandidate("abcd", Collections.singletonList(new InputCandidate.Segment("abcd", "私人未收錄句子", false)), false);
        InputCandidate selected = new InputCandidate("abcd", Collections.singletonList(new InputCandidate.Segment("abcd", "另一句未收錄內容", false)), false);
        assertTrue(CorrectionLearning.rejectedKeys(old, selected, w -> false,true,true,true,false).isEmpty());
    }
    @Test public void twoRepeatedCorrectionsOvercomeLargeLegacyPreferenceWithoutErasingIt() {
        String rejected = CorrectionLearning.update(null, NOW, 1);
        rejected = CorrectionLearning.update(rejected, NOW, -.25); // Tentative selection of the old word.
        rejected = CorrectionLearning.update(rejected, NOW, 1); // Explicitly replaced again.
        int oldWeight = CorrectionLearning.adjust(100, rejected, NOW);
        int selectedWeight = RecentLearning.weight(2, RecentLearning.update(null, NOW, 2), NOW);
        assertTrue(selectedWeight > oldWeight);
        assertEquals(100, CorrectionLearning.adjust(100, rejected, NOW + 8L * 7 * 24 * 60 * 60 * 1000));
    }
    @Test public void correctionStrengthIsBoundedAndAcceptedUsesRecoverConfidence() {
        String rejected = null;
        for (int i=0;i<100;i++) rejected=CorrectionLearning.update(rejected,NOW,1);
        assertEquals(-64, CorrectionLearning.adjust(0,rejected,NOW));
        for (int i=0;i<32;i++) rejected=CorrectionLearning.update(rejected,NOW,-.25);
        assertNull(rejected);
        assertEquals(12, CorrectionLearning.adjust(12,"broken",NOW));
        assertEquals(12, CorrectionLearning.adjust(12,null,NOW));
    }
}
