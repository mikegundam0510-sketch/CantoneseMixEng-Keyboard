package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPOutputStream;

public class PhraseRelationRankerTest {
    private static PhraseRelationRanker model(Map<String,String> lexicon,Map<String,Float> weights,float strength)throws IOException {
        return model(lexicon,weights,strength,false);
    }
    private static PhraseRelationRanker model(Map<String,String> lexicon,Map<String,Float> weights,float strength,boolean aligned)throws IOException {
        return model(lexicon,weights,strength,aligned,0,0);
    }
    private static PhraseRelationRanker model(Map<String,String> lexicon,Map<String,Float> weights,float strength,boolean aligned,float margin,float lift)throws IOException {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(bytes))) {
            out.writeInt(margin!=0?0x50525233:aligned?0x50525232:0x50525231);out.writeInt(lexicon.size());out.writeInt(weights.size());out.writeFloat(strength);out.writeFloat(2);
            if(margin!=0){out.writeFloat(margin);out.writeFloat(lift);}
            for(Map.Entry<String,String> e:lexicon.entrySet()) {
                byte[] key=e.getKey().getBytes(StandardCharsets.UTF_8);out.writeShort(key.length);out.write(key);
                out.writeByte(e.getValue().charAt(0));out.writeShort(2);
            }
            for(Map.Entry<String,Float> e:weights.entrySet()) {
                byte[] key=e.getKey().getBytes(StandardCharsets.UTF_8);out.writeShort(key.length);out.write(key);out.writeFloat(e.getValue());
            }
            if(margin!=0){out.writeInt(0);out.writeFloat(0);out.writeFloat(2);}
        }
        return PhraseRelationRanker.load(new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray())));
    }
    private static Map<String,String> lexicon() {
        Map<String,String> result=new HashMap<>();for(String verb:Arrays.asList("交","食","買","見","用"))result.put(verb,"V");
        result.put("錢包","N");result.put("𠮷哥","N");return result;
    }
    @Test public void supportedHeadSwapPreservesAllFiveChoicesAndRejectsWeakEvidence()throws Exception {
        Map<String,String> lex=new HashMap<>(lexicon());lex.put("功課","N");
        Map<String,Float> weights=new LinkedHashMap<>();weights.put("SV|你|交",1f);weights.put("VO|交|D",1f);weights.put("VQ|交|Y",1f);
        PhraseRelationRanker active=model(lex,weights,1,true,.5f,.5f);
        List<String> original=Arrays.asList("係交功課未","你交功課未","我交功課未","你未交功課","佢未交功課","佢交功課未");
        Map<String,Double> scores=new HashMap<>();for(int i=0;i<original.size();i++)scores.put(original.get(i),10.0-i);
        scores.put(original.get(1),12.0);List<String> values=new ArrayList<>(original);
        Map<String,Map<String,Integer>> cache=new HashMap<>();
        for(String value:original)assertEquals(active.rawScore("",value),active.rawScore("",value,cache),0);
        List<String> cached=new ArrayList<>(original);active.promoteHead("",cached,scores,cache);
        active.promoteHead("",values,scores);assertEquals(original.get(1),values.get(0));assertEquals(original.get(0),values.get(1));
        assertEquals(values,cached);
        assertEquals(new HashSet<>(original.subList(0,5)),new HashSet<>(values.subList(0,5)));
        List<String> later=new ArrayList<>(original);later.remove(original.get(1));later.add(original.get(1));
        active.promoteHead("",later,scores);assertEquals(original.get(1),later.get(0));assertEquals(original.get(0),later.get(1));
        assertEquals(new HashSet<>(original),new HashSet<>(later));
        scores.put(original.get(1),10.25);values=new ArrayList<>(original);active.promoteHead("",values,scores);assertEquals(original,values);
        scores.put(original.get(1),12.0);values=new ArrayList<>(original);
        model(lex,weights,1,true).promoteHead("",values,scores);assertEquals(original,values);
        model(lex,weights,0,true,.5f,.5f).promoteHead("",values,scores);assertEquals(original,values);
        values=new ArrayList<>(Arrays.asList("三流","你交功課未"));scores.put("三流",0.0);scores.put("你交功課未",100.0);
        active.promoteHead("",values,scores);assertEquals("Numeral intent must survive an apparently stronger grammar score","三流",values.get(0));
    }
    @Test public void invalidHeadPromotionBoundsAreRejected()throws Exception {
        for(float value:new float[]{.49f,1.01f,Float.NaN,Float.POSITIVE_INFINITY}) {
            try{model(lexicon(),Collections.emptyMap(),1,true,value,.5f);fail();}catch(IOException expected){}
            try{model(lexicon(),Collections.emptyMap(),1,true,.5f,value);fail();}catch(IOException expected){}
        }
    }
    @Test public void alignedTailsCanReceiveNegativeEvidenceWithinTheRealLimit()throws Exception {
        PhraseRelationRanker m=model(lexicon(),Collections.singletonMap("VO|食|F",1f),.5f,true);
        assertTrue(m.aligned());assertFalse(model(lexicon(),Collections.emptyMap(),.5f).aligned());
        assertEquals(-1,m.alignedCorrection(-100,100),0);
        assertEquals(1,m.alignedCorrection(100,-100),0);
        assertEquals(.5,m.alignedCorrection(m.rawScore("","我食飯"),m.rawScore("","我食錢包")),0);
        assertEquals(-.5,m.alignedCorrection(m.rawScore("","我食錢包"),m.rawScore("","我食飯")),0);
        assertEquals(0,m.correction(-100,100),0);
        assertEquals(m.evidence("","你交咗功課未").raw,m.rawScore("","你交咗功課未"),0);
    }

    private static Reader asset(String name)throws IOException {
        return new InputStreamReader(new FileInputStream("src/main/assets/"+name),StandardCharsets.UTF_8);
    }
    private static QuickDecoder decoder(DictionaryEngine d,PhraseRelationRanker relation)throws Exception {
        return new QuickDecoder(d,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(new FileInputStream("src/main/assets/language_model.b64")),
            PhraseLanguageModel.load(new FileInputStream("src/main/assets/phrase_model.b64")),asset("hk_chat_phrases.tsv"),
            CandidateRanker.load(new FileInputStream("src/main/assets/candidate_ranker.b64")),
            CandidateRanker.loadWords(new FileInputStream("src/main/assets/word_ranker.b64")),
            SentenceRanker.load(new FileInputStream("src/main/assets/sentence_ranker.b64")),
            PrefixRanker.load(new FileInputStream("src/main/assets/prefix_ranker.b64")),relation);
    }
    @Test public void alignedCorrectionPreservesLegacyFirstEvenWithOpposingWeights()throws Exception {
        DictionaryEngine d=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        Map<String,Float> weights=new LinkedHashMap<>();weights.put("G|PV",-1.5f);weights.put("G|OO",1.5f);weights.put("G|VV",1.5f);
        QuickDecoder before=decoder(d,null),after=decoder(d,model(lexicon(),weights,1.5f,true));
        for(String code:Arrays.asList("ofonaovrmrq","ofykrmmsydwljpvwjd","dpofvivcjutrmyyjvcqnjd")) {
            List<String> old=before.decode(code,(c,w)->0),updated=after.decode(code,(c,w)->0);
            assertEquals(old.get(0),updated.get(0));assertTrue(updated.size()<=20);
            assertEquals("Reranking must keep every existing visible candidate",new HashSet<>(old),new HashSet<>(updated));
            for(String value:updated)assertFalse(d.matchQuickCodes(code,value).isEmpty());
        }
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
