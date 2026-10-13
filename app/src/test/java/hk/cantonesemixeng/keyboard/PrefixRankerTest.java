package hk.cantonesemixeng.keyboard;
import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import java.lang.reflect.*;

public class PrefixRankerTest {
    private static Reader asset(String name)throws IOException {
        return new InputStreamReader(new FileInputStream("src/main/assets/"+name),StandardCharsets.UTF_8);
    }
    private static QuickDecoder bundled(DictionaryEngine d,PrefixRanker prefix)throws IOException {
        return new QuickDecoder(d,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(new FileInputStream("src/main/assets/language_model.b64")),
            PhraseLanguageModel.load(new FileInputStream("src/main/assets/phrase_model.b64")),asset("hk_chat_phrases.tsv"),
            CandidateRanker.load(new FileInputStream("src/main/assets/candidate_ranker.b64")),
            CandidateRanker.loadWords(new FileInputStream("src/main/assets/word_ranker.b64")),
            SentenceRanker.load(new FileInputStream("src/main/assets/sentence_ranker.b64")),prefix);
    }
    @Test public void bundledPrefixAssetRecoversAnExactCandidateAndKeepsExplicitPersonalChoices()throws Exception {
        DictionaryEngine d=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        PrefixRanker prefix=PrefixRanker.load(new FileInputStream("src/main/assets/prefix_ranker.b64"));
        QuickDecoder before=bundled(d,null),after=bundled(d,prefix);
        // Evaluation-only public words.hk example; see tools/data/daily_prefix/NOTICE.txt.
        String code="ofrkdehkosvdohoshuci",gold="你噉樣笑佢好傷佢自尊";
        assertFalse(before.decode(code,(c,w)->0).contains(gold));
        List<String> values=after.decode(code,(c,w)->0);
        assertEquals(5,values.indexOf(gold)+1);assertTrue(values.size()<=20);
        assertEquals(values.size(),new HashSet<>(values).size());
        for(String v:values)assertFalse(d.matchQuickCodes(code,v).isEmpty());
        assertEquals("你好",after.decode("ofvd",(c,w)->w.equals("你好")?100:0).get(0));
    }
    private static PrefixRanker model(Map<String,Float> weights,float strength)throws IOException {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(bytes))) {
            out.writeInt(0x50524b31);out.writeInt(weights.size());out.writeFloat(strength);out.writeFloat(2);
            for(Map.Entry<String,Float> e:weights.entrySet()) {
                byte[] key=e.getKey().getBytes(StandardCharsets.UTF_8);out.writeShort(key.length);out.write(key);out.writeFloat(e.getValue());
            }
        }
        return PrefixRanker.load(new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray())));
    }
    @Test public void actualFollowingWordHintsDistinguishTheSamePrefix()throws Exception {
        PrefixRanker m=model(Collections.singletonMap("B|0|咗|份報",1f),1);
        assertEquals(1,m.correction("你","交咗",Arrays.asList("份報告")),0);
        assertEquals(0,m.correction("你","交咗",Arrays.asList("同事")),0);
        assertEquals(0,m.correction("你","交咗",Collections.emptyList()),0);
    }
    @Test public void editorBoundariesSupplementaryGlyphsAndRepetitionRemainBounded()throws Exception {
        PrefixRanker m=model(new LinkedHashMap<String,Float>(){{put("K|你|2|咗",1f);put("W|𠮩𠹌",.5f);}},1);
        assertEquals(1,m.correction("你交","咗",Collections.emptyList()),0);
        assertEquals(0,m.correction("你交，","咗",Collections.emptyList()),0);
        assertEquals(.5,m.correction("𠮩","𠹌",Collections.emptyList()),0);
        assertEquals(0,m.correction("你交"+"好".repeat(12),"咗",Collections.emptyList()),0);
        PrefixRanker repeated=model(Collections.singletonMap("W|你你",1.5f),1.5f);
        assertEquals(3,repeated.correction("","你".repeat(20),Collections.emptyList()),0);
        assertEquals(0,model(Collections.singletonMap("W|你你",1.5f),0).correction("","你你",Collections.emptyList()),0);
    }
    @Test public void malformedBoundsAndFullSentenceKeysAreRejected()throws Exception {
        for(Map<String,Float> bad:Arrays.asList(Collections.singletonMap("W|完整句子唔應該記住",1f),
                Collections.singletonMap("B|0|完整句子|我",1f),Collections.singletonMap("C|2|P|N",1f),
                Collections.singletonMap("E|未",Float.NaN))) {
            try{model(bad,1);fail("Invalid prefix model accepted");}catch(IOException expected){}
        }
        try{model(Collections.emptyMap(),Float.POSITIVE_INFINITY);fail();}catch(IOException expected){}
    }
    @Test @SuppressWarnings("unchecked") public void survivalReserveKeepsTheOriginalBeamAndRejectsDistantUnsupportedPaths()throws Exception {
        DictionaryEngine d=new DictionaryEngine(new InputStreamReader(new FileInputStream(
            "src/main/assets/cangjie5.base.dict.yaml"),StandardCharsets.UTF_8),new StringReader(""));
        PrefixRanker m=model(new LinkedHashMap<String,Float>(){{put("W|我你",1f);put("W|我佢",1f);}},1);
        QuickDecoder q=new QuickDecoder(d,new StringReader(""),null,null,null,null,null,null,null,1.5,null,m);
        Class<?> path=Class.forName("hk.cantonesemixeng.keyboard.QuickDecoder$Path");
        Constructor<?> make=path.getDeclaredConstructor(String.class,double.class);make.setAccessible(true);
        List<Object> input=new ArrayList<>();
        for(int i=0;i<48;i++)input.add(make.newInstance("我"+new String(Character.toChars(0x4E00+i)),-i*.01));
        List<Object> core=new ArrayList<>(input);
        Object close=make.newInstance("我你",-.5),far=make.newInstance("我佢",-10),unknown=make.newInstance("我好",-.6);
        input.add(close);input.add(far);input.add(unknown);
        Method prune=QuickDecoder.class.getDeclaredMethod("prune",List.class,String.class,List.class,
            Class.forName("hk.cantonesemixeng.keyboard.QuickDecoder$ModelScoreCache"));prune.setAccessible(true);
        List<Object> result=(List<Object>)prune.invoke(q,input,"",Collections.emptyList(),null);
        assertEquals(core,result.subList(0,48));assertTrue(result.contains(close));
        assertFalse(result.contains(far));assertFalse(result.contains(unknown));assertEquals(49,result.size());
        // Pairwise training distinguishes less-negative correct evidence from
        // a worse same-code boundary; absolute-positive gating would lose it.
        PrefixRanker relative=model(new LinkedHashMap<String,Float>(){{
            put("W|我"+new String(Character.toChars(0x4E00+47)),-1f);put("W|我你",-.5f);put("E|你",.1f);
        }},1);
        QuickDecoder revised=new QuickDecoder(d,new StringReader(""),null,null,null,null,null,null,null,1.5,null,relative);
        List<Object> compared=(List<Object>)prune.invoke(revised,input,"",Collections.emptyList(),null);
        assertEquals(core,compared.subList(0,48));assertTrue(compared.contains(close));assertFalse(compared.contains(unknown));
    }
}
