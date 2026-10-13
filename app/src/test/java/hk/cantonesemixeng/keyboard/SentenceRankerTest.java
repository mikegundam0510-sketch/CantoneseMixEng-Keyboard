package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPOutputStream;

public class SentenceRankerTest {
    private static byte[] encoded(Map<String, Float> weights, float strength, float limit, int schema) throws IOException {
        return encoded(weights,strength,limit,schema,-1);
    }
    private static byte[] encoded(Map<String, Float> weights, float strength, float limit, int schema,float longer) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(new GZIPOutputStream(bytes))) {
            data.writeInt(longer<0 ? 0x53524b32 : 0x53524b33); data.writeInt(weights.size()); data.writeInt(schema);
            data.writeFloat(strength); data.writeFloat(limit);
            if(longer>=0) {data.writeFloat(longer);data.writeFloat(1.5f);}
            for (Map.Entry<String, Float> e : weights.entrySet()) {
                byte[] key = e.getKey().getBytes(StandardCharsets.UTF_8);
                data.writeShort(key.length); data.write(key); data.writeFloat(e.getValue());
            }
        }
        return Base64.getEncoder().encode(bytes.toByteArray());
    }
    private static SentenceRanker model(Map<String, Float> weights) throws IOException {
        return SentenceRanker.load(new ByteArrayInputStream(encoded(weights, 1, 3, 2)));
    }
    @Test public void separateLongCorrectionKeepsTheOriginalShortCap() throws Exception {
        Map<String,Float> weights=new LinkedHashMap<String,Float>() {{
            put("W|研究",1.5f);put("W|一下",1.5f);put("E|下",1.5f);put("L|研究|s|下",1.5f);
        }};
        SentenceRanker m=SentenceRanker.load(new ByteArrayInputStream(encoded(weights,1.5f,3,3,.25f)));
        assertEquals(4.775,m.score("","研究一下"),1e-12);
        SentenceRanker off=SentenceRanker.load(new ByteArrayInputStream(encoded(weights,1.5f,3,3,0)));
        assertEquals(4.5,off.score("","研究一下"),0);
        SentenceRanker negative=SentenceRanker.load(new ByteArrayInputStream(encoded(
            Collections.singletonMap("L|你|l|未",-1.5f),1.5f,3,3,.25f)));
        assertEquals(0,negative.score("","你交咗所有嗰啲功課未"),0);
    }
    @Test public void longerActionObjectRelationsUseBoundedContextAndShortUnits() throws Exception {
        SentenceRanker m=SentenceRanker.load(new ByteArrayInputStream(encoded(
            new LinkedHashMap<String,Float>() {{put("L|交|m|功課",1f);put("L|你|l|未",.5f);}},1,3,3)));
        assertEquals(1.5,m.score("","你交咗所有嗰啲功課未"),0);
        assertEquals(1.5,m.score("你交咗所有嗰啲","功課未"),0);
        assertEquals(0,m.score("你交咗所有，","功課未"),0);
        assertEquals(0,m.score("你交咗所有","abc功課未"),0);
        assertEquals(0,m.score("你交"+"所有".repeat(7),"功課未"),0);
    }
    @Test public void relationUsesEditorContextAndResetsAtBoundaries() throws Exception {
        SentenceRanker m = model(Collections.singletonMap("K|你|2|咗", 1f));
        assertEquals(1, m.score("你交", "咗錢"), 0);
        assertEquals(1, m.score("", "你交咗錢"), 0);
        assertEquals(0, m.score("你交，", "咗錢"), 0);
        assertEquals(0, m.score("你交", "abc咗錢"), 0);
        assertEquals(0, m.score("你今日已經又交", "咗錢"), 0);
    }
    @Test public void sentenceBoundariesAreDistinctFromInteriorWords() throws Exception {
        SentenceRanker m = model(new LinkedHashMap<String, Float>() {{ put("S|你", 1f); put("E|未", .5f); }});
        assertEquals(1.5, m.score("", "你交咗錢未"), 0);
        assertEquals(.5, m.score("我想問", "你交咗錢未"), 0);
        assertEquals(1.5, m.score("Zoom ", "你交咗錢未"), 0);
        assertEquals(1, m.score("", "你交咗錢"), 0);
    }
    @Test public void supplementaryCharactersAndUnknownFeaturesRemainUsable() throws Exception {
        SentenceRanker m = model(Collections.singletonMap("W|𠮩𠹌", .75f));
        assertEquals(.75, m.score("𠮩", "𠹌"), 0);
        assertEquals(.75, m.score("", "𠮩𠹌"), 0);
        assertEquals(0, m.score("", "未知名字"), 0);
        assertEquals(0, m.score("我今日", ""), 0);
        String newer = new String(Character.toChars(0x33468));
        assertTrue(SentenceRanker.features("", "你" + newer + "未").containsKey("K|你|2|未"));
    }
    @Test public void wholeCorrectionAndRepeatedEvidenceAreBounded() throws Exception {
        SentenceRanker m = model(new LinkedHashMap<String, Float>() {{ put("W|唔唔", 1.5f); put("W|唔唔唔", 1.5f); }});
        assertEquals(3, m.score("", "唔唔唔唔唔唔"), 0);
        assertEquals(Integer.valueOf(2), SentenceRanker.features("", "唔唔唔唔唔唔").get("W|唔唔"));
        SentenceRanker zero = SentenceRanker.load(new ByteArrayInputStream(encoded(Collections.singletonMap("W|唔唔", 1f), 0, 3, 2)));
        assertEquals(0, zero.score("", "唔唔唔"), 0);
    }
    @Test public void orderingWordsAndDeterminersDoNotBecomeOpenClassRoleEvidence() {
        Map<String, Integer> features = SentenceRanker.features("", "訊息先覆你");
        assertTrue(features.containsKey("R|O|2|M"));
        assertFalse(features.containsKey("R|O|2|O"));
        assertTrue(SentenceRanker.features("", "我睇啲字").containsKey("R|P|2|B"));
    }
    @Test public void malformedOrOverlongFeaturesAreRejected() throws Exception {
        for (Map<String, Float> weights : Arrays.asList(Collections.singletonMap("W|完整句子唔可以儲存", 1f),
                Collections.singletonMap("K|你|9|咗", 1f), Collections.singletonMap("W|研究", Float.NaN))) {
            try { model(weights); fail("Bad feature accepted"); } catch (IOException expected) { }
        }
        try { SentenceRanker.load(new ByteArrayInputStream(encoded(Collections.emptyMap(), 1, 3, 4))); fail(); }
        catch (IOException expected) { }
    }
    private static Reader asset(String name) throws IOException {
        return new InputStreamReader(new FileInputStream("src/main/assets/" + name), StandardCharsets.UTF_8);
    }
    private static QuickDecoder decoder(DictionaryEngine d, OfflineLanguageModel lm, SentenceRanker r) throws IOException {
        return new QuickDecoder(d, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"), asset("cantonese_phrases.tsv"), lm,
            PhraseLanguageModel.load(new FileInputStream("src/main/assets/phrase_model.b64")), asset("hk_chat_phrases.tsv"),
            CandidateRanker.load(new FileInputStream("src/main/assets/candidate_ranker.b64")),
            CandidateRanker.loadWords(new FileInputStream("src/main/assets/word_ranker.b64")), r);
    }
    @Test public void finalCorrectionReordersExistingCandidatesAndPreservesPersonalChoices() throws Exception {
        DictionaryEngine d = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        OfflineLanguageModel lm = OfflineLanguageModel.load(new FileInputStream("src/main/assets/language_model.b64"));
        SentenceRanker r = SentenceRanker.load(new ByteArrayInputStream(encoded(
            new LinkedHashMap<String, Float>() {{ put("S|你", -1.5f); put("S|係", 1.5f); }}, 2, 3, 2)));
        QuickDecoder base = decoder(d, lm, null), changed = decoder(d, lm, r);
        List<String> before = base.decode("ofykrmcijd", (c, w) -> 0), after = changed.decode("ofykrmcijd", (c, w) -> 0);
        assertTrue(after.size()<=20);assertEquals(after.size(),new HashSet<>(after).size());
        // Weaker structural support cannot replace the supported completion question.
        assertEquals(before.get(0), after.get(0));
        for (String value : after) assertFalse(d.matchQuickCodes("ofykrmcijd", value).isEmpty());
        SentenceRanker lexical = SentenceRanker.load(new ByteArrayInputStream(encoded(
            new LinkedHashMap<String, Float>() {{ put("W|好彩", 1.5f); put("W|好睇", -1.5f); }}, 2, 3, 2)));
        List<String> unguarded = base.decode("vdbhalofmchu", (c, w) -> 0);
        List<String> nudged = decoder(d, lm, lexical).decode("vdbhalofmchu", (c, w) -> 0);
        assertTrue(nudged.size()<=20);for(String value:nudged)assertFalse(d.matchQuickCodes("vdbhalofmchu",value).isEmpty());
        assertTrue(nudged.indexOf("好彩即係頭先") < unguarded.indexOf("好彩即係頭先"));
        assertEquals("你好", changed.decode("ofvd", (c, w) -> w.equals("你好") ? 100 : 0).get(0));
        SentenceRanker zero = SentenceRanker.load(new ByteArrayInputStream(encoded(Collections.singletonMap("S|你", 1f), 0, 3, 2)));
        assertEquals(before, decoder(d, lm, zero).decode("ofykrmcijd", (c, w) -> 0));
    }
}
