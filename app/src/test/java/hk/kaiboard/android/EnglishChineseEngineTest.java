package hk.kaiboard.android;
import org.junit.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.Assert.*;
public class EnglishChineseEngineTest {
 private static EnglishChineseEngine meanings;
 @BeforeClass public static void load()throws Exception{meanings=EnglishChineseEngine.load(new FileInputStream("src/main/assets/english_chinese.b64"));}
 @Test public void canCasingAndHongKongMeanings(){
  for(String word:Arrays.asList("can","CAN","Can"))assertEquals("可以",meanings.lookup(word).get(0));
  assertEquals("報告",meanings.lookup("report").get(0));assertEquals("多謝",meanings.lookup("thanks").get(0));assertEquals("電郵",meanings.lookup("email").get(0));
 }
 @Test public void unknownInputNeverInventsMeanings(){
  for(String word:Arrays.asList("zzqxxxy","a b","123",""))assertTrue(meanings.lookup(word).isEmpty());
 }
 @Test public void translationsRetainExactSourceAndDoNotBecomeEnglishLearning(){
  InputCandidate c=InputCandidate.translation("CAN","可以");assertEquals("CAN",c.source);assertEquals("CAN",c.effectiveCode());
  assertFalse(c.englishOnly());assertTrue(c.segments.get(0).translated);
  assertTrue(c.replace(0,"能夠").segments.get(0).translated);assertEquals("CAN",c.replace(0,"能夠").source);
 }
 private Reader asset(String name)throws Exception{return new InputStreamReader(new FileInputStream("src/main/assets/"+name),StandardCharsets.UTF_8);}
 @Test public void quickPrefixAndEnglishSuffixRemainEditable()throws Exception{
  DictionaryEngine d=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
  CandidateEngine c=new CandidateEngine(d,new QuickDecoder(d,asset("quick_phrases.tsv"),asset("hk_phrases.tsv")),new EnglishEngine(asset("english.txt")));
  List<InputCandidate> r=meanings.mixedSuffix("ofCAN","",c,(code,word)->0);
  assertTrue(r.stream().anyMatch(x->x.text.equals("你CAN")));assertTrue(r.stream().anyMatch(x->x.text.equals("你可以")));
  InputCandidate translated=r.stream().filter(x->x.text.equals("你可以")).findFirst().get();assertEquals("ofCAN",translated.source);
  assertEquals("ofCAN",translated.effectiveCode());assertTrue(translated.segments.get(translated.segments.size()-1).translated);
 }
}
