package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPOutputStream;

public class PhraseRelationRankerTest {
    private static PhraseRelationRanker model(Map<String,String> lexicon,Map<String,Float> weights,float strength)throws IOException {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(bytes))) {
            out.writeInt(0x50525231);out.writeInt(lexicon.size());out.writeInt(weights.size());out.writeFloat(strength);out.writeFloat(2);
            for(Map.Entry<String,String> e:lexicon.entrySet()) {
                byte[] key=e.getKey().getBytes(StandardCharsets.UTF_8);out.writeShort(key.length);out.write(key);
                out.writeByte(e.getValue().charAt(0));out.writeShort(2);
            }
            for(Map.Entry<String,Float> e:weights.entrySet()) {
                byte[] key=e.getKey().getBytes(StandardCharsets.UTF_8);out.writeShort(key.length);out.write(key);out.writeFloat(e.getValue());
            }
        }
        return PhraseRelationRanker.load(new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray())));
    }
    private static Map<String,String> lexicon() {
        Map<String,String> result=new HashMap<>();for(String verb:Arrays.asList("交","食","買","見","用"))result.put(verb,"V");
        result.put("錢包","N");result.put("𠮷哥","N");return result;
    }
    @Test public void classifierAndObjectCategoriesDoNotConfuseWalletsDriversOrPeanuts()throws Exception {
        PhraseRelationRanker m=model(lexicon(),new LinkedHashMap<String,Float>(){{put("VO|食|F",1f);put("VO|用|E",1f);}},1);
        assertEquals(1,m.rawScore("","我食花生"),0);
        assertEquals(0,m.rawScore("","我食錢包"),0);
        assertEquals(0,m.rawScore("","我用司機"),0);
        assertEquals(1,m.rawScore("","我用手機"),0);
        assertTrue(m.features("","我買咗碟豬腸粉").containsKey("CN|碟|F"));
    }
    @Test public void subjectAspectRecipientAndQuestionRemainRelatedAcrossWords()throws Exception {
        PhraseRelationRanker m=model(lexicon(),Collections.emptyMap(),1);
        Map<String,Integer> f=m.features("","你交咗功課畀老細未");
        assertTrue(f.containsKey("SV|你|交"));assertTrue(f.containsKey("VO|交|D"));assertTrue(f.containsKey("VQ|交|Y"));
        assertFalse(m.features("","你未交功課").containsKey("VQ|交|Y"));
        assertTrue(m.features("","你未交功課").containsKey("NV|未|交"));
    }
    @Test public void contextBoundariesRepetitionAndSupplementaryNamesAreHandled()throws Exception {
        PhraseRelationRanker m=model(lexicon(),new LinkedHashMap<String,Float>(){{put("VO|交|D",.5f);put("VQ|交|Y",.5f);put("VH|見|哥",1f);}},1);
        assertEquals(1,m.rawScore("你交","功課未"),0);
        assertEquals(0,m.rawScore("你交，","功課未"),0);
        assertEquals(0,m.rawScore("你交"+"好".repeat(12),"功課未"),0);
        assertEquals(1,m.rawScore("我見","𠮷哥"),0);
        assertEquals(0,m.rawScore("我見abc","𠮷哥"),0);
        for(int count:m.features("","你交功課".repeat(30)).values())assertTrue(count<=2);
    }
    @Test public void twoSubjectFeaturesAreOneKindAndSmallLearnedCoefficientsCanCount()throws Exception {
        Map<String,Float> weights=new LinkedHashMap<>();weights.put("SV|你|交",.02f);weights.put("SR|P|交",.02f);weights.put("G|PVN",.8f);
        PhraseRelationRanker m=model(lexicon(),weights,1.5f);
        assertFalse(m.evidence("","你交功課").supportedOver(m.evidence("","係交功課")));
        weights.put("VO|交|D",.02f);m=model(lexicon(),weights,1.5f);
        PhraseRelationRanker.Evidence candidate=m.evidence("","你交功課"),ref=m.evidence("","係交功課");
        assertTrue(candidate.supportedOver(ref));assertTrue(m.trustedPromotion(candidate,ref,m.correction(candidate.raw,ref.raw)));
    }
    @Test public void negationAloneCannotDisplaceAnEquallyStructuredAffirmative()throws Exception {
        PhraseRelationRanker m=model(lexicon(),new LinkedHashMap<String,Float>(){{put("SV|我|交",.02f);put("VO|交|D",.02f);put("NV|唔|交",.8f);}},1.5f);
        PhraseRelationRanker.Evidence yes=m.evidence("","我有交功課"),no=m.evidence("","我唔交功課");
        assertTrue(no.supportedOver(yes));assertFalse(m.trustedPromotion(no,yes,m.correction(no.raw,yes.raw)));
    }
    @Test public void unknownVocabularyIsNotAdverseEvidenceAndCorrectionHasBounds()throws Exception {
        PhraseRelationRanker m=model(lexicon(),Collections.singletonMap("G|OO",-1.5f),1.5f);
        assertFalse(m.evidence("","你交功課").repairs(m.evidence("","龘龘")));
        assertEquals(2.9,m.correction(100,-100),1e-12);assertEquals(0,m.correction(-100,100),0);
        assertEquals(0,model(lexicon(),Collections.emptyMap(),0).correction(100,-100),0);
    }
    @Test public void malformedBoundsUnknownRolesAndWholeSentenceFieldsAreRejected()throws Exception {
        for(Map<String,Float> bad:Arrays.asList(Collections.singletonMap("SV|你交功課畀老細未|交",1f),
                Collections.singletonMap("G|POVQQ",1f),Collections.singletonMap("VO|交|X",1f),Collections.singletonMap("G|PV",Float.NaN))) {
            try{model(lexicon(),bad,1);fail("Invalid relation model accepted");}catch(IOException expected){}
        }
        try{model(Collections.singletonMap("食","!"),Collections.emptyMap(),1);fail();}catch(IOException expected){}
        try{model(lexicon(),Collections.emptyMap(),Float.POSITIVE_INFINITY);fail();}catch(IOException expected){}
    }
}
