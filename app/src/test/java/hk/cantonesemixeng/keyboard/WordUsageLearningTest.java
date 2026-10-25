package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import java.util.*;
import java.util.function.Predicate;
import static org.junit.Assert.*;

public class WordUsageLearningTest {
    private final Predicate<String> known = text -> Arrays.asList("你好", "返工", "香港").contains(text);
    private InputCandidate choice(String code,String text) {
        return new InputCandidate(code,Collections.singletonList(new InputCandidate.Segment(code,text,false)),false);
    }
    @Test public void selectedWordUsesItsWholeSpellingAndNeverSegmentOrContextKeys() {
        InputCandidate word = new InputCandidate("ofvd",Arrays.asList(
            new InputCandidate.Segment("of","你",false),new InputCandidate.Segment("vd","好",false)),false);
        assertEquals(Collections.singleton("U:QC:ofvd:你好"),WordUsageLearning.selectedKeys(word,known,true,true,true,false));
        assertEquals(Collections.singletonList("你好"),WordUsageLearning.selectedWords("香港",word,known,true,false));
        assertNotEquals(WordUsageLearning.key("ofvd",true,true,"你好"),WordUsageLearning.key("ofvd",true,false,"你好"));
        assertNotEquals(WordUsageLearning.key("ofvd",true,true,"你好"),WordUsageLearning.key("ofv",true,true,"你好"));
    }
    @Test public void singleChoicesDoNotBecomeWordsByLookingAtEditorContext() {
        InputCandidate single=choice("vd","好");
        assertEquals(Collections.singleton("QC:vd:好"),WordUsageLearning.selectedKeys(single,known,true,true,true,false));
        assertTrue(WordUsageLearning.selectedWords("你",single,known,true,false).isEmpty());
        assertTrue(WordUsageLearning.selectedKeys(choice("ofvdofvd","你好你好"),known,true,true,true,false).isEmpty());
    }
    @Test public void onlyClickedAssociationMayCompleteOneAttestedWord() {
        InputCandidate tail=choice("","好");
        assertEquals(Collections.singletonList("你好"),WordUsageLearning.selectedWords("你",tail,known,true,false));
        assertTrue(WordUsageLearning.selectedKeys(tail,known,true,true,true,false).isEmpty());
        assertTrue(WordUsageLearning.selectedWords("無關",tail,known,true,false).isEmpty());
    }
    @Test public void disabledProtectedLiteralAndTranslatedChoicesDoNotTrain() {
        InputCandidate word=choice("ofvd","你好");
        assertTrue(WordUsageLearning.selectedKeys(word,known,true,true,false,false).isEmpty());
        assertTrue(WordUsageLearning.selectedKeys(word,known,true,true,true,true).isEmpty());
        assertTrue(WordUsageLearning.selectedWords("",word,known,false,false).isEmpty());
        assertTrue(WordUsageLearning.selectedWords("",word,known,true,true).isEmpty());
        assertTrue(WordUsageLearning.selectedKeys(InputCandidate.translation("hello","你好"),known,true,true,true,false).isEmpty());
        assertNull(WordUsageLearning.key("of:vd",true,true,"你好"));
    }
    @Test public void correctionOnlyPenalizesDifferentExplicitChoiceOfTheSameCode() {
        assertEquals(Collections.singleton("QC:of:你"),WordUsageLearning.rejectedKeys(choice("of","你"),choice("of","佢"),known,true,true));
        assertTrue(WordUsageLearning.rejectedKeys(choice("of","你"),choice("o","佢"),known,true,true).isEmpty());
        assertTrue(WordUsageLearning.rejectedKeys(choice("of","你"),choice("of","你"),known,true,true).isEmpty());
        assertEquals(new HashSet<>(Arrays.asList("U:QC:ofvd:你好","W:你好")),
            WordUsageLearning.rejectedKeys(choice("ofvd","你好"),choice("ofvd","返工"),known,true,true));
    }
}
