package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class OfflineLanguageModelTest {
    private static OfflineLanguageModel model;
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static Reader asset(String name) throws IOException {
        return new InputStreamReader(new FileInputStream("src/main/assets/"+name), StandardCharsets.UTF_8);
    }
    @BeforeClass public static void load() throws Exception {
        model = OfflineLanguageModel.load(new FileInputStream("src/main/assets/language_model.b64"));
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"), asset("cantonese_phrases.tsv"), model);
    }
    @Test public void boundedMemoryAndFiniteScores() {
        assertTrue(model.entryCount()>400000); assertTrue(model.arrayBytes()<9*1024*1024);
        for (String s : Arrays.asList("你好", "今日食咗咩", "𠮩𠹌", "abc，香港"))
            assertTrue(Double.isFinite(model.score("我今日",s)));
    }
    @Test public void contextStopsAtNonHanAndSupportsSupplementaryCharacters() {
        assertEquals("今日食咗", OfflineLanguageModel.contextTail("我今日食咗"));
        assertEquals("香港", OfflineLanguageModel.contextTail("你好，香港"));
        assertEquals("", OfflineLanguageModel.contextTail("中文https://"));
        assertEquals("𠮩𠹌", OfflineLanguageModel.contextTail("hello𠮩𠹌"));
    }
    @Test public void splitScoringRetainsFourCharacterContext() {
        String context="我今日", left="食咗", right="咩嘢";
        assertEquals(model.score(context,left+right), model.score(context,left)+model.score(context+left,right),1e-9);
        assertNotEquals(model.score("我今日", "食咗咩"), model.score("佢聽日", "食咗咩"),1e-5);
    }
    @Test public void punctuationClearsHistory() {
        assertEquals(model.score("", "香港"), model.score("你好", "，香港"),1e-9);
    }
    @Test public void malformedModelIsRejected() throws Exception {
        try { OfflineLanguageModel.load(new ByteArrayInputStream("broken".getBytes(StandardCharsets.UTF_8))); fail(); }
        catch (IOException expected) { }
    }
    @Test public void productionDecoderReturnsExactReachableDistinctCandidates() {
        for (String code : Arrays.asList("ofvd", "ofvdrf", "haeu", "rryo", "ofonaovrmrq", "hisuvmjuisgehr", "abcdef")) {
            List<String> values=decoder.decode(code,(c,w)->0,"我今日");
            assertFalse(code,values.isEmpty()); assertEquals(values.size(),new HashSet<>(values).size());
            for (String value:values) assertFalse(code+" / "+value,dictionary.matchQuickCodes(code,value).isEmpty());
        }
        assertEquals("你好",decoder.decode("ofvd",(c,w)->0).get(0));
    }
}
