package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class MixedInputTest {
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static EnglishEngine english;
    private static CandidateEngine engine;
    private static Reader asset(String name) throws Exception {
        return new InputStreamReader(new FileInputStream("src/main/assets/"+name),StandardCharsets.UTF_8);
    }
    @BeforeClass public static void load() throws Exception {
        dictionary=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        decoder=new QuickDecoder(dictionary,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"));
        english=new EnglishEngine(asset("english.txt"));engine=new CandidateEngine(dictionary,decoder,english);
    }
    @Test public void mixedBrandSentencePreservesSourceAndEnglishCasing() {
        String code="onaovrrovMcdonaldrh";
        List<InputCandidate> choices=engine.mixed(code,"",Collections.emptyList(),(c,w)->0);
        assertFalse(choices.isEmpty());
        assertEquals("今日食唔食Mcdonald呀",choices.get(0).text);
        assertEquals(code,choices.get(0).source);
        for(InputCandidate candidate:choices) {
            assertEquals(code.toLowerCase(Locale.ROOT),candidate.effectiveCode().toLowerCase(Locale.ROOT));
            for(InputCandidate.Segment s:candidate.segments)
                if(!s.english)assertFalse(dictionary.matchQuickCodes(s.code,s.text).isEmpty());
        }
    }
    @Test public void shortQuickCodesDoNotAutomaticallyBecomeEnglishWords() {
        assertFalse(english.likelyEnglish("on",Collections.emptyList()));
        assertFalse(english.likelyEnglish("of",Collections.emptyList()));
        assertTrue(english.likelyEnglish("Mcdonald",Collections.emptyList()));
        assertTrue(english.likelyEnglish("report",Collections.emptyList()));
        assertTrue(english.likelyEnglish("AQHI",Collections.emptyList()));
        assertTrue(english.likelyEnglish("hellp",Collections.emptyList()));
        assertFalse(english.likelyEnglish("OFONAOVRMRQ",Collections.emptyList()));
    }
    @Test public void spellingRepairsAreOptionalAndOriginalInputStaysFirst() {
        assertEquals("hellp",english.suggest("hellp",Collections.emptyList(),true).get(0));
        assertTrue(english.suggest("hellp",Collections.emptyList(),true).contains("hello"));
        assertFalse(english.suggest("hellp",Collections.emptyList(),false).contains("hello"));
        assertTrue(EnglishEngine.oneEdit("repotr","report"));
        assertTrue(EnglishEngine.oneEdit("repor","report"));
        assertFalse(EnglishEngine.oneEdit("abc","report"));
    }
    @Test public void personalEnglishIsRecognizedAndCanBeRemovedWithoutChangingBaseDictionary() {
        assertFalse(english.likelyEnglish("Nebulon",Collections.emptyList()));
        assertTrue(english.likelyEnglish("Nebulon",Arrays.asList("Nebulon")));
        assertFalse(english.likelyEnglish("Nebulon",Collections.emptyList()));
    }
    @Test public void contextChangesCandidateOrderWithoutChangingCodeValidity() {
        List<InputCandidate> words=engine.chinese("oa","開",false,true,true,(c,w)->0);
        assertEquals("會",words.get(0).text);
        for(InputCandidate candidate:words)assertTrue(dictionary.lookup("oa",true,true,false).contains(candidate.text));
    }
    @Test public void segmentReplacementPreservesAllOtherChineseAndEnglishParts() {
        InputCandidate candidate=engine.mixed("onaovrrovMcdonaldrh","",Collections.emptyList(),(c,w)->0).get(0);
        int index=candidate.segments.size()-1;
        InputCandidate edited=candidate.replace(index,"呵");
        assertEquals(candidate.source,edited.source);
        assertEquals("今日食唔食Mcdonald呵",edited.text);
        for(int i=0;i<index;i++)assertSame(candidate.segments.get(i),edited.segments.get(i));
    }
    @Test public void quickRepairsRequireOneNeighborSubstitutionAndNeverMutateExactCandidates() {
        QuickTypos typos=new QuickTypos(dictionary,decoder);
        List<InputCandidate> repaired=typos.suggest("od",(InputCandidate)null,"");
        assertTrue(repaired.stream().anyMatch(c->c.text.equals("你")));
        for(InputCandidate candidate:repaired) {
            assertTrue(candidate.corrected);assertEquals("od",candidate.source);
            String effective=candidate.effectiveCode();int changed=0;
            for(int i=0;i<effective.length();i++)if(effective.charAt(i)!=candidate.source.charAt(i)){
                changed++;assertTrue(QuickTypos.neighbors(candidate.source.charAt(i)).indexOf(effective.charAt(i))>=0);
            }
            assertEquals(1,changed);assertFalse(dictionary.matchQuickCodes(effective,candidate.text).isEmpty());
        }
    }
    @Test public void continuousTypoRepairsLeaveUnchangedSegmentsIntact() {
        List<InputCandidate> baselines=engine.chinese("odvd","",true,true,false,(c,w)->0);
        List<InputCandidate> repaired=new QuickTypos(dictionary,decoder).suggest("odvd",baselines,"");
        assertTrue(repaired.stream().anyMatch(c->c.text.equals("你好")));
    }
    @Test public void reselectionIsInvalidAfterMovingCursorSelectingTextOrEditingSuffix() {
        InputCandidate c=InputCandidate.chinese(dictionary,"ofvd","你好");
        ReselectionRecord record=new ReselectionRecord(c,5,"之前的你好");
        assertTrue(record.valid(5,5,"之前的你好"));
        assertFalse(record.valid(4,4,"之前的你好"));
        assertFalse(record.valid(3,5,"之前的你好"));
        assertFalse(record.valid(5,5,"之前的你嗎"));
        assertFalse(record.valid(5,5,null));
    }
}
