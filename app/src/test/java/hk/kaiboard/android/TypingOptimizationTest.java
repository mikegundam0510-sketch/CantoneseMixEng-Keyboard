package hk.kaiboard.android;

import org.junit.Test;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class TypingOptimizationTest {
    private static void check(boolean value, String reason) {
        if (!value) throw new AssertionError(reason);
    }
    private static Reader asset(String name) throws Exception {
        return Files.newBufferedReader(Path.of("src/main/assets",name),StandardCharsets.UTF_8);
    }
    @Test public void regression() throws Exception { run(); }
    public static void main(String[] args) throws Exception { run(); }
    private static void run() throws Exception {
        DictionaryEngine dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        for (String source : List.of("nf","ofn","onnf")) {
            List<InputCandidate> repairs = ChineseAutocorrect.cangjieRepairs(dictionary,source);
            check(repairs.stream().anyMatch(c->c.text.equals("你") && c.effectiveCode().equals("onf")),"missing/swapped/repeated radical: "+source);
            check(repairs.stream().allMatch(c->c.source.equals(source) && c.corrected),"repair source preserved");
            check(repairs.stream().map(c->c.text).distinct().count()==repairs.size(),"duplicate repairs");
        }
        for (String invalid : List.of("","a","123","onf!","abcdef"))
            check(ChineseAutocorrect.cangjieRepairs(dictionary,invalid).isEmpty(),"invalid radical source");
        QuickDecoder plain = new QuickDecoder(dictionary,new StringReader(""));
        QuickDecoder local = new QuickDecoder(dictionary,new StringReader(""),asset("hk_phrases.tsv"));
        check(local.languageScore("研究","一下")-plain.languageScore("研究","一下")>0,"HK phrases influence fallback scores");
        CandidateEngine candidates = new CandidateEngine(dictionary,local,new EnglishEngine(asset("english.txt")));
        check(candidates.chinese("my","研究一",false,true,false,(c,w)->0).get(0).text.equals("下"),"research context prioritizes 下");
        EnglishChineseEngine meanings = new EnglishChineseEngine(new StringReader("can\t可以\t10\ncan\t能夠\t5\ncan\t罐\t1\n"));
        check(meanings.lookup("CAN","",(a,b)->0).equals(List.of("可以","能夠","罐")),"idle exact meaning order");
        check(meanings.lookup("CAN","飲汽水",(context,text)->context.isEmpty()?0:text.equals("罐")?10:0).get(0).equals("罐"),"meaning follows context");
        check(meanings.lookup("CAN","研究",(a,b)->Double.NaN).equals(List.of("可以","能夠","罐")),"nonfinite context does not scramble meanings");
        check(meanings.lookup("zzqxxxy","研究",(a,b)->0).isEmpty(),"no invented meanings");
        InputCandidate good = new InputCandidate("abcd",List.of(new InputCandidate.Segment("abfd","乙",false)),true);
        check(ChineseAutocorrect.choose("abcd","研究",List.of(InputCandidate.chinese(dictionary,"abcd","甲")),List.of(good),t->t.equals("甲")?Double.NaN:5)==good,"nonfinite exact score does not block a finite repair");
        check(ChineseAutocorrect.choose("abcd","",List.of(),List.of(good),t->5)==null,"empty context never auto repairs");
        long started=System.nanoTime();
        for(int i=0;i<100;i++) ChineseAutocorrect.cangjieRepairs(dictionary,"onnf");
        check((System.nanoTime()-started)/1_000_000 < 3000,"bounded repair latency");
        System.out.println("Typing optimization checks passed");
    }
}
