package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;
import java.util.*;

public class ContextLearningTest {
    private InputCandidate character(String code,String text) {
        return new InputCandidate(code,Collections.singletonList(new InputCandidate.Segment(code,text,false)),false);
    }
    @Test public void singleChoicesTeachShortSequencesWithoutEditorContext() {
        SingleSelectionHistory history=new SingleSelectionHistory();
        InputCandidate first=character("me","覆"),second=character("rm","咗"),third=character("br","同");
        history.confirm("mermbr",first,"rmbr",history.contextFor("mermbr",""),null);
        String context=history.contextFor("rmbr","");
        assertEquals(Collections.singleton("S:rm:覆:咗"),ContextLearning.selectedKeys(context,second,true,false));
        history.confirm("rmbr",second,"br",context,null);
        assertEquals(new HashSet<>(Arrays.asList("S:br:咗:同","S:br:覆咗:同")),
            ContextLearning.selectedKeys(history.contextFor("br",""),third,true,false));
        history.confirm("br",third,"",history.contextFor("br",""),null);
        assertTrue(ContextLearning.selectedKeys(history.contextFor("me",""),first,true,false).isEmpty());
    }
    @Test public void disabledAndProtectedFieldsProduceNoRecords() {
        assertTrue(ContextLearning.selectedKeys("覆",character("rm","咗"),false,false).isEmpty());
        assertTrue(ContextLearning.selectedKeys("覆",character("rm","咗"),true,true).isEmpty());
        assertTrue(ContextLearning.selectedKeys("覆",InputCandidate.translation("word","咗"),true,false).isEmpty());
        assertTrue(ContextLearning.selectedKeys("覆",character("wrong-code","咗"),true,false).isEmpty());
    }
    @Test public void englishAndPunctuationBreakTheSequence() {
        assertTrue(ContextLearning.selectedKeys("覆A",character("rm","咗"),true,false).isEmpty());
        InputCandidate mixed=new InputCandidate("",Arrays.asList(new InputCandidate.Segment("w","word",true),
            new InputCandidate.Segment("rm","咗",false)),false);
        assertTrue(ContextLearning.selectedKeys("覆",mixed,true,false).isEmpty());
        assertTrue(ContextLearning.selectedKeys("覆，",character("rm","咗"),true,false).isEmpty());
    }
    @Test public void recordsNeverContainAWholeLongSentenceAndHandleSupplementaryHan() {
        String han=new String(Character.toChars(0x20000));
        Set<String> keys=ContextLearning.selectedKeys("唔會保存呢個私人整句覆"+han,character("rm","咗"),true,false);
        assertEquals(new HashSet<>(Arrays.asList("S:rm:"+han+":咗","S:rm:覆"+han+":咗")),keys);
    }
    @Test public void aSpecificRejectionOverridesTheShorterPositiveContext() {
        Map<String,Integer> counts=new HashMap<>();counts.put("S:rm:覆:咗",20);counts.put("S:rm:我覆:咗",-8);
        assertEquals(-8,ContextLearning.weight("我覆","rm","咗",k->counts.getOrDefault(k,0)));
        assertEquals(20,ContextLearning.weight("佢覆","rm","咗",k->counts.getOrDefault(k,0)));
        ContextLearning.Preferences preferences=new ContextLearning.Preferences(counts.keySet(),k->counts.getOrDefault(k,0));
        assertFalse(preferences.favored("我覆","rm").contains("咗"));
        assertTrue(preferences.favored("佢覆","rm").contains("咗"));
    }
    @Test public void contextChangesDoNotCarryTheSamePreference() {
        Map<String,Integer> counts=Collections.singletonMap("S:rm:覆:咗",20);
        ContextLearning.Preferences preferences=new ContextLearning.Preferences(counts.keySet(),k->counts.getOrDefault(k,0));
        assertEquals(0,preferences.weight("個","rm","咗"));
        assertEquals(0,preferences.weight("覆","ri","咗"));
        assertEquals(0,preferences.weight("覆，","rm","咗"));
    }
    @Test public void sequenceCapacityDoesNotEvictOldCharacterOrPhraseRecords() {
        Map<String,Object> counts=new HashMap<>();counts.put("QC:of:你",1);counts.put("W:唔該",1);
        for(int i=0;i<512;i++)counts.put("S:aa:我:"+i,10+i);
        String evicted=ContextLearning.evictionKey(counts,"S:rm:覆:咗");
        assertEquals("S:aa:我:0",evicted);
        counts.remove(evicted);counts.put("S:rm:覆:咗",1);
        assertEquals(512,counts.keySet().stream().filter(k->k.startsWith("S:")).count());
        assertTrue(counts.containsKey("QC:of:你"));assertTrue(counts.containsKey("W:唔該"));
        assertNull(ContextLearning.evictionKey(counts,"S:rm:覆:咗"));
    }
    @Test public void singleReselectionRetainsOnlyTheOriginalShortContext() {
        SingleSelectionHistory history=new SingleSelectionHistory();
        InputCandidate old=new InputCandidate("merm",Arrays.asList(new InputCandidate.Segment("me","反",false),
            new InputCandidate.Segment("rm","啲",false)),false);
        history.confirm("merm",character("me","覆"),"rm","頭先",old,"已經確認我想");
        assertEquals("我想",history.correctionContext("後面"));
        history.confirm("rm",character("rm","咗"),"",history.contextFor("rm",""),null);
        assertEquals("後面",history.correctionContext("後面"));
    }
    @Test public void completeSupportedSequenceRespectsRejectionAndBoundaries() {
        InputCandidate choice=new InputCandidate("merm",Arrays.asList(new InputCandidate.Segment("me","覆",false),
            new InputCandidate.Segment("rm","咗",false)),false);
        Map<String,Integer> counts=new HashMap<>();counts.put("S:rm:覆:咗",12);
        ContextLearning.Preferences preferences=new ContextLearning.Preferences(counts.keySet(),k->counts.getOrDefault(k,0));
        assertTrue(ContextLearning.supports("",choice,preferences));
        assertTrue(ContextLearning.supports("我，",choice,preferences));
        assertFalse(ContextLearning.supports("我",choice,preferences));
        counts.put("S:rm:覆:咗",-8);
        assertFalse(ContextLearning.supports("",choice,preferences));
    }
    @Test public void preferredCharacterOutsideTheUsualTwentyFourCanEnterSearch() throws Exception {
        StringBuilder entries=new StringBuilder("...\n"), frequencies=new StringBuilder();
        for(int i=0;i<1000;i++) {
            String c=new String(Character.toChars(0x4e00+i));
            entries.append(c).append("\taaa\n");frequencies.append(c).append("\t100000\n");
        }
        entries.append("你\toof\n");
        DictionaryEngine dictionary=new DictionaryEngine(new java.io.StringReader(entries.toString()),
            new java.io.StringReader(""),new java.io.StringReader(frequencies.toString()));
        String rare=dictionary.quickCandidates("aa").get(999),wanted=rare+"你";
        QuickDecoder decoder=new QuickDecoder(dictionary,new java.io.StringReader(""));
        Set<String> keys=ContextLearning.selectedKeys("你",InputCandidate.chinese(dictionary,"aaof",wanted),true,false);
        ContextLearning.Preferences preferences=new ContextLearning.Preferences(keys,k->keys.contains(k) ? 12 : 0);
        assertFalse(decoder.decode("aaof",(c,w)->0,"你").contains(wanted));
        assertEquals(wanted,decoder.decode("aaof",(c,w)->0,"你",preferences).get(0));
        assertFalse(dictionary.matchQuickCodes("aaof",wanted).isEmpty());
    }
    @Test public void correctionRejectsOnlyChangedContextsForTheSameCompleteInput() {
        InputCandidate previous=new InputCandidate("mermbr",Arrays.asList(new InputCandidate.Segment("me","反",false),
            new InputCandidate.Segment("rm","咗",false),new InputCandidate.Segment("br","同",false)),false);
        InputCandidate selected=previous.replace(0,"覆");
        Set<String> rejected=ContextLearning.rejectedKeys("我",previous,selected);
        assertEquals(new HashSet<>(Arrays.asList("S:me:我:反","S:rm:反:咗","S:rm:我反:咗","S:br:反咗:同")),rejected);
        assertFalse(rejected.contains("S:br:咗:同"));
        assertTrue(ContextLearning.rejectedKeys("我",previous,character("me","覆")).isEmpty());
        assertTrue(ContextLearning.rejectedKeys("我",previous,InputCandidate.english("mermbr","word")).isEmpty());
        assertTrue(ContextLearning.rejectedKeys("我",previous,previous).isEmpty());
    }
}
