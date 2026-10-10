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
        assertTrue(first>=10);assertTrue(top5>=14);
    }
    @Test public void questionEvidenceSpansTheRecipientButResetsAtPunctuation() {
        String text="你交咗功課畀老細未";
        for(int at=1;at<text.length();at++) assertEquals(decoder.languageScore("",text),
            decoder.languageScore("",text.substring(0,at))+decoder.languageScore(text.substring(0,at),text.substring(at)),1e-9);
        assertEquals(1.5,decoder.languageScore("你交咗功課畀老細","未")-
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
        assertEquals(1.5, decoder.languageScore("你交咗功課畀老細","未未")-
            decoder.languageScore("你未交功課畀老細","未未"),1e-9);
    }
}
