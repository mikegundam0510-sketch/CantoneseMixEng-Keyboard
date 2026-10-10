package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;
import java.util.*;

public class SingleSelectionHistoryTest {
    private InputCandidate character(String code, String text) {
        return new InputCandidate(code, Collections.singletonList(new InputCandidate.Segment(code,text,false)),false);
    }
    @Test public void individualConfirmationsTeachKnownWordsEvenWithoutEditorContext() {
        SingleSelectionHistory history = new SingleSelectionHistory();
        InputCandidate first=character("aa","唔"), second=character("bb","該"), third=character("cc","晒");
        history.confirm("aabbcc",first,"bbcc",history.contextFor("aabbcc",""),null);
        String context=history.contextFor("bbcc","");
        assertEquals(Collections.singletonList("唔該"), PhraseLearning.selectedWords(context,second,w -> w.equals("唔該"),true,false));
        history.confirm("bbcc",second,"cc",context,null);
        context=history.contextFor("cc","");
        assertEquals(Collections.singletonList("唔該晒"),PhraseLearning.selectedWords(context,third,w -> w.equals("唔該晒"),true,false));
        assertTrue(PhraseLearning.selectedWords(context,third,w -> false,true,false).isEmpty());
        history.confirm("cc",third,"",context,null);
        assertEquals("新",history.contextFor("zz","新"));
    }
    @Test public void fullReselectionCorrectedInSingleModeProducesCodeAlignedFeedback() {
        SingleSelectionHistory history=new SingleSelectionHistory();
        InputCandidate old=new InputCandidate("hiru",Arrays.asList(new InputCandidate.Segment("hi","得",false),new InputCandidate.Segment("ru","嘅",false)),false);
        assertNull(history.confirm("hiru",character("hi","我"),"ru","",old));
        InputCandidate[] completed=history.confirm("ru",character("ru","嘅"),"",history.contextFor("ru",""),null);
        assertEquals("我嘅",completed[1].text);
        assertEquals(new HashSet<>(Arrays.asList("QC:hi:得","W:得嘅")),CorrectionLearning.rejectedKeys(completed[0],completed[1],w -> w.equals("得嘅"),true,true,true,false));
    }
    @Test public void editedCodeAndExplicitResetDiscardPreviousSpan() {
        SingleSelectionHistory history=new SingleSelectionHistory();
        history.confirm("aabb",character("aa","唔"),"bb","",null);
        assertEquals("新",history.contextFor("bc","新"));
        history.confirm("aabb",character("aa","唔"),"bb","",null);
        history.clear();
        assertEquals("",history.contextFor("bb",""));
    }
    @Test public void englishOrInvalidConsumptionBreaksChain() {
        SingleSelectionHistory history=new SingleSelectionHistory();
        history.confirm("aabb",character("aa","唔"),"bb","",null);
        assertNull(history.confirm("bb",InputCandidate.english("bb","word"),"","唔",null));
        assertEquals("",history.contextFor("bb",""));
        assertNull(history.confirm("aabb",character("aa","唔"),"wrong","",null));
        assertEquals("",history.contextFor("bb",""));
    }
}
