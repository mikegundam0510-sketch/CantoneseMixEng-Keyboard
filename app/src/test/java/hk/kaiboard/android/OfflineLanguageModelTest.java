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
    @Test public void researchPhraseAndSymbolContainingCodesStayChineseAndReachable() {
        assertEquals("研究一下", decoder.decode("mtjnmmy", (c,w)->0).get(0));
        for (String code : Arrays.asList("mtjnmyqv", "mtjnmy", "mtjnmmy", "myqv", "mtjnmyq")) {
            List<String> values = decoder.decode(code, (c,w)->0);
            assertFalse(code, values.isEmpty());
            for (String value : values) {
                assertTrue(code + " / " + value, QuickDecoder.hanText(value));
                assertFalse(code + " / " + value, dictionary.matchQuickCodes(code, value).isEmpty());
            }
        }
        // Explicit symbol lookup remains available to the user.
        assertTrue(dictionary.quickCandidates("yq").contains("♂"));
    }
    @Test public void hongKongFragmentsComposeNaturalUnlistedSentences() {
        String[][] cases = {
            {"hidpmtjnmmy", "我想研究一下"},
            {"ofgbhibhmy", "你幫我睇下"},
            {"hispayesfmm", "我聽日返緊工"},
            {"rryogbhiskye", "唔該幫我改返"},
            {"hinjhumbymmy", "等陣先再試下"},
            {"hidporkbkbtcod", "我想知有冇其他"},
            {"hiypogyqrihu", "我諗住遲啲先"},
            {"hirdspaatoa", "我哋聽日開會"}
        };
        for (String[] example : cases) {
            assertEquals(example[0], example[1], decoder.decode(example[0], (c,w)->0).get(0));
            assertFalse(dictionary.matchQuickCodes(example[0], example[1]).isEmpty());
        }
    }
    @Test public void hongKongUsageBonusCrossesTokenBoundariesAndStopsAtPunctuation() {
        assertEquals(decoder.languageScore("", "幫我睇下"),
            decoder.languageScore("", "幫我") + decoder.languageScore("幫我", "睇下"), 1e-9);
        assertEquals(decoder.languageScore("", "睇下"), decoder.languageScore("幫我，", "睇下"), 1e-9);
        assertTrue(decoder.languageScore("幫我", "睇下") > model.score("幫我", "睇下"));
    }
    @Test public void productionDecoderReturnsExactReachableDistinctCandidates() {
        for (String code : Arrays.asList("ofvd", "ofvdrf", "haeu", "rryo", "ofonaovrmrq", "hisuvmjuisgehr", "abcdef")) {
            List<String> values=decoder.decode(code,(c,w)->0,"我今日");
            assertFalse(code,values.isEmpty()); assertEquals(values.size(),new HashSet<>(values).size());
            for (String value:values) assertFalse(code+" / "+value,dictionary.matchQuickCodes(code,value).isEmpty());
        }
        assertEquals("你好",decoder.decode("ofvd",(c,w)->0).get(0));
    }

    @Test public void laterCodesDisambiguateEarlierQuickCharactersInUnlistedSentences() {
        String[][] cases = {
            {"vkmmnkmrvordrjjj", "收工又可以踩單車"},
            {"hidprdrjjj", "我想踩單車"},
            {"hispardrjjj", "我聽日踩單車"},
            {"hirdmrvo", "我哋可以"}
        };
        for (String[] example : cases) {
            List<String> values = decoder.decode(example[0], (c,w)->0);
            assertEquals(example[0], example[1], values.get(0));
            assertEquals(values.size(), new HashSet<>(values).size());
            for (String value : values)
                assertFalse(example[0] + " / " + value, dictionary.matchQuickCodes(example[0], value).isEmpty());
        }
        // The whole sentence is composed; only reusable verb/object fragments are authored.
        List<String> values = decoder.decode("vkmmnkmrvordrjjj", (c,w)->0);
        assertTrue(values.contains("收工又可以咪單車"));
        assertEquals(Arrays.asList("vk","mm","nk","mr","vo","rd","rj","jj"),
            dictionary.matchQuickCodes("vkmmnkmrvordrjjj", values.get(0)));
        assertEquals("踩單車", decoder.decode("rdrjjj", (c,w)->0, "收工又可以").get(0));
    }
    @Test public void collocationEvidenceCrossesTokensAndResetsAtPunctuation() {
        assertEquals(decoder.languageScore("可以", "踩單車"),
            decoder.languageScore("可以", "踩") + decoder.languageScore("可以踩", "單車"), 1e-9);
        assertTrue(decoder.languageScore("踩", "單車") > model.score("踩", "單車"));
        assertEquals(decoder.languageScore("", "單車"), decoder.languageScore("踩，", "單車"), 1e-9);
    }


    @Test public void candidateEngineExposesRerankedSentenceWithEditableCharacterCodes() throws Exception {
        CandidateEngine engine = new CandidateEngine(dictionary, decoder, new EnglishEngine(asset("english.txt")));
        InputCandidate candidate = engine.chinese("vkmmnkmrvordrjjj", "", true, true, false, (c,w)->0).get(0);
        assertEquals("收工又可以踩單車", candidate.text);
        assertEquals("vkmmnkmrvordrjjj", candidate.effectiveCode());
        assertEquals("rd", candidate.segments.get(5).code);
        assertEquals("踩", candidate.segments.get(5).text);
        assertFalse(candidate.corrected);
    }


    @Test public void corpusPhraseEvidenceAppliesWithoutTheAuthoredHkList() throws Exception {
        QuickDecoder general = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), null,
            asset("cantonese_phrases.tsv"), model);
        String[][] boundaries = {{"打","電話"}, {"修","理"}, {"開","會"}, {"食","飯"}};
        for (String[] boundary : boundaries) {
            String left = boundary[0], right = boundary[1];
            assertTrue(left + right, general.languageScore(left,right) > model.score(left,right));
            assertEquals(general.languageScore("",left+right),
                general.languageScore("",left)+general.languageScore(left,right),1e-9);
        }
        assertEquals("我想打電話", general.decode("hidpqnmuyr",(c,w)->0).get(0));
    }
    @Test public void recentCjkCharactersNeverReceiveTheNonHanZeroScore() {
        for (int cp : new int[]{0x9FFF, 0x2EBF0, 0x31350, 0x323B0, 0x33479}) {
            String text = new String(Character.toChars(cp));
            assertTrue(QuickDecoder.hanText(text));
            assertEquals(text, OfflineLanguageModel.contextTail("hello" + text));
            assertTrue(Double.isFinite(model.score("",text)));
            assertTrue(model.score("",text) < 0);
            assertEquals(model.score("",text), model.score("香港","，"+text),1e-9);
        }
    }
    @Test public void generalContextRanksDifferentActivitiesAndObjects() {
        String[][] cases = {
            {"hidpwcbemf","我想買股票"},
            {"hidpbhmuah","我想睇電影"},
            {"hidpohmgrjjj","我想修理單車"},
            {"vkmmnkmrvooorrry","收工又可以飲咖啡"},
            {"vkmmnkmrvoqraujm","收工又可以搭巴士"}
        };
        for (String[] item : cases) {
            List<String> values = decoder.decode(item[0],(c,w)->0);
            assertEquals(item[0],item[1],values.get(0));
            for (String value : values)
                assertFalse(dictionary.matchQuickCodes(item[0],value).isEmpty());
        }
    }

}
