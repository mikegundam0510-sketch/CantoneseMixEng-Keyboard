package hk.kaiboard.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.junit.*;
import static org.junit.Assert.*;

public class ContinuousClauseRankingTest {
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(Path.of("src/main/assets", name), StandardCharsets.UTF_8);
    }
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"),
            asset("cantonese_phrases.tsv"), OfflineLanguageModel.load(Files.newInputStream(Path.of("src/main/assets/language_model.b64"))));
    }
    @AfterClass public static void release() { dictionary = null; decoder = null; }
    @Test public void reportedContinuousSentenceRanksFirstWithoutPersonalHistory() {
        String code = "dpofvivcjutrmyyjvcqnjd";
        List<String> result = decoder.decode(code, (c,w) -> 0);
        assertEquals("想你繼續完善下連續打字", result.get(0));
        assertEquals(result.size(), new HashSet<>(result).size());
        for (String candidate : result) assertFalse(dictionary.matchQuickCodes(code, candidate).isEmpty());
    }
    @Test public void requestPatternsGeneralizeToOtherSubjectsAndActions() throws Exception {
        for (String line : Files.readAllLines(Path.of("../tools/continuous_clause_cases.tsv"), StandardCharsets.UTF_8)) {
            String[] fields = line.split("\\t", -1);
            List<String> result = decoder.decode(fields[1], (c,w) -> 0, fields[0]);
            assertEquals(fields[1], fields[2], result.get(0));
            for (String candidate : result) assertFalse(dictionary.matchQuickCodes(fields[1], candidate).isEmpty());
        }
    }
    @Test public void requestAndActionEvidenceCrossesWordBoundaries() {
        for (String[] parts : new String[][]{{"想你", "繼續"}, {"想佢", "幫我"}, {"修改", "下"}, {"檢查", "下"}}) {
            assertEquals(decoder.languageScore("", parts[0]+parts[1]),
                decoder.languageScore("", parts[0]) + decoder.languageScore(parts[0], parts[1]), 1e-9);
            assertEquals(decoder.languageScore("", parts[1]), decoder.languageScore(parts[0]+"，", parts[1]), 1e-9);
        }
    }
    @Test public void reportedHandoverQuestionRanksFirstWithoutPersonalHistory() {
        String code = "ofykrmmsydwljpvwjd";
        List<String> result = decoder.decode(code, (c,w) -> 0);
        assertEquals("你交咗功課畀老細未",result.get(0));
        for(String candidate:result) assertFalse(dictionary.matchQuickCodes(code,candidate).isEmpty());
        assertFalse(decoder.knownWord("你交咗功課畀老細未"));
    }
    @Test public void completionQuestionsGeneralizeWithoutMemorizingSentences() throws Exception {
        int first=0, top5=0;
        for(String line:Files.readAllLines(Path.of("../tools/hk_completion_cases.tsv"))) {
            String[] fields=line.split("\t",-1);
            List<String> result=decoder.decode(fields[1],(c,w)->0,fields[0]);
            int rank=result.indexOf(fields[2]);
            if(rank==0) first++;
            if(rank>=0 && rank<5) top5++;
            for(String candidate:result) assertFalse(dictionary.matchQuickCodes(fields[1],candidate).isEmpty());
        }
        assertEquals(16,first);assertEquals(16,top5);
    }
    @Test public void handoverPatternsGeneralizeAcrossActionsAndRecipients() throws Exception {
        int first=0, top5=0;
        for(String line:Files.readAllLines(Path.of("../tools/hk_handover_cases.tsv"), StandardCharsets.UTF_8)) {
            String[] fields=line.split("\t",-1);
            List<String> result=decoder.decode(fields[1],(c,w)->0,fields[0]);
            int rank=result.indexOf(fields[2]);
            if(rank==0) first++;
            if(rank>=0 && rank<5) top5++;
            assertEquals(result.size(),new HashSet<>(result).size());
            for(String candidate:result) assertFalse(dictionary.matchQuickCodes(fields[1],candidate).isEmpty());
        }
        assertTrue(first>=29);assertEquals(30,top5);
    }
    @Test public void previouslyMissingAndLowRankedRepliesRankFirst() {
        String[][] examples={{"himermbrjn","我覆咗同事"},{"ofmermbrjnjd","你覆咗同事未"},
            {"hiykyxmsydwljphb","我交齊功課畀老師"},{"ofoirmgehrwljpvwjd","你傳咗報告畀老細未"},
            {"gbhiykyeykoq","幫我交返文件"}};
        for(String[] example:examples) {
            assertEquals(example[1],decoder.decode(example[0],(c,w)->0).get(0));
            assertFalse(decoder.knownWord(example[1]));
        }
    }
    @Test public void repeatedExplicitCorrectionsCanChooseAnotherValidHandover() {
        String code="osykrmykoqwlbrjn", wanted="佢送咗文件畀同事";
        InputCandidate previous=InputCandidate.chinese(dictionary,code,"佢交咗文件畀同事");
        InputCandidate replacement=InputCandidate.chinese(dictionary,code,wanted);
        Set<String> rejected=CorrectionLearning.rejectedKeys(previous,replacement,decoder::knownWord,true,false,true,false);
        long now=123456789;
        String positive=null,negative=null;
        for(int i=0;i<5;i++) {
            positive=RecentLearning.update(positive,now,1);
            negative=CorrectionLearning.update(negative,now,1);
        }
        final int chosenWeight=RecentLearning.weight(5,positive,now);
        final String rejectedState=negative;
        List<String> result=decoder.decode(code,(c,w)->{
            int weight=c.equals("yk") && w.equals("送") ? chosenWeight : 0;
            String key=decoder.knownWord(w) ? PhraseLearning.key(w) : LearningRanker.key(c,true,false,w);
            return CorrectionLearning.adjust(weight,rejected.contains(key) ? rejectedState : null,now);
        });
        assertEquals(wanted,result.get(0));
        assertFalse(decoder.knownWord(wanted));
    }
    @Test public void recipientEvidenceIsIndependentOfLatticeTokenBoundaries() {
        for(String text:new String[]{"我交咗功課畀老師", "你傳咗文件畀同事未", "佢買咗嘢畀朋友",
                "我哋寄咗文件畀你哋", "你帶咗文件俾老師未", "你覆咗同事未", "我交齊功課畀老師"}) {
            for(int at=1;at<text.length();at++) assertEquals(text,
                decoder.languageScore("",text),decoder.languageScore("",text.substring(0,at))+
                decoder.languageScore(text.substring(0,at),text.substring(at)),1e-9);
            assertEquals(decoder.languageScore("",text),decoder.languageScore("我交咗功課畀老師，",text),1e-9);
            assertEquals(decoder.languageScore("",text),decoder.languageScore("我交咗功課畀老師A",text),1e-9);
        }
    }
    @Test public void recipientEvidenceRequiresAnActionAndDoesNotDoubleCountPluralRecipients() throws Exception {
        // Empty phrase statistics give context-independent lexical probabilities.
        QuickDecoder uniform=new QuickDecoder(dictionary,new StringReader(""));
        double lexical=uniform.languageScore("","你");
        assertEquals(3,uniform.languageScore("你交咗功課畀","你")-lexical,1e-9);
        assertEquals(2,uniform.languageScore("交咗功課畀","你")-lexical,1e-9);
        assertEquals(lexical,uniform.languageScore("你未交功課畀","你"),1e-9);
        assertEquals(lexical,uniform.languageScore("你交咗功課界","你"),1e-9);
        assertEquals(lexical,uniform.languageScore("你交咗功課，畀","你"),1e-9);
        assertEquals(uniform.languageScore("","哋"),uniform.languageScore("你交咗功課畀你","哋"),1e-9);
        assertEquals(3,uniform.languageScore("你覆咗同","事")-uniform.languageScore("","事"),1e-9);
        assertEquals(uniform.languageScore("","事"),uniform.languageScore("你覆咗，同","事"),1e-9);
        assertEquals(1.5,uniform.languageScore("你睇咗文件","未")-uniform.languageScore("","未"),1e-9);
    }
    @Test public void questionEvidenceSpansTheRecipientButResetsAtPunctuation() {
        String text="你交咗功課畀老細未";
        for(int at=1;at<text.length();at++) assertEquals(decoder.languageScore("",text),
            decoder.languageScore("",text.substring(0,at))+decoder.languageScore(text.substring(0,at),text.substring(at)),1e-9);
        assertEquals(3,decoder.languageScore("你交咗功課畀老細","未")-
            decoder.languageScore("你未交功課畀老細","未"),1e-9);
        assertEquals(decoder.languageScore("","未"),decoder.languageScore("你交咗功課畀老細，","未"),1e-9);
        assertEquals(decoder.languageScore("資料安排更新方案","未"),
            decoder.languageScore("你交咗功課文件報告資料安排更新方案","未"),1e-9);
    }
    @Test public void weakCombinationsAreNotUsedToFillTwentySlots() {
        List<String> result=decoder.decode("ruaiokrp",(c,w)->0,"到到小息");
        assertEquals("嘅時候呢",result.get(0));
        assertTrue(result.size()<5);
    }
    @Test public void explicitlyLearnedCharacterSequenceSurvivesConfidenceFiltering() {
        String code="ruaiokrp", chosen="嘅時侯呢";
        Set<String> selected=new HashSet<>();
        InputCandidate candidate=InputCandidate.chinese(dictionary,code,chosen);
        for(InputCandidate.Segment part:candidate.segments) selected.add(part.code+":"+part.text);
        assertTrue(decoder.decode(code,(c,w)->selected.contains(c+":"+w) ? 6 : 0,"到到小息").contains(chosen));
    }
    @Test public void completionQuestionDoesNotBoostFutureWordOrRepeatedParticles() {
        assertEquals(decoder.languageScore("你交咗功課畀老細","未來"),
            decoder.languageScore("你交咗功課畀老細","未")+decoder.languageScore("你交咗功課畀老細未","來"),1e-9);
        assertEquals(decoder.languageScore("你未交功課畀老細","未來"),
            decoder.languageScore("你交咗功課畀老細","未來"),1e-9);
        assertEquals(3, decoder.languageScore("你交咗功課畀老細","未未")-
            decoder.languageScore("你未交功課畀老細","未未"),1e-9);
    }
}
