package hk.kaiboard.android;
import org.junit.Test;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public class ChineseAutocorrectTest {
    static int checks;
    static void check(boolean value, String message) {
        checks++; if (!value) throw new AssertionError(message);
    }
    static InputCandidate c(String source, String fixed, String text, boolean corrected) {
        return new InputCandidate(source,List.of(new InputCandidate.Segment(fixed,text,false)),corrected);
    }
    static Reader asset(String name) throws Exception {
        return Files.newBufferedReader(Path.of("src/main/assets",name),StandardCharsets.UTF_8);
    }
    @Test public void coreAndRealModelChecks() throws Exception {
        var exact = List.of(c("abcd","abcd","甲",false));
        var best = c("abcd","abfd","乙",true);
        var runner = c("abcd","abgd","丙",true);
        var scores = Map.of("甲",0.0,"乙",5.0,"丙",1.0);
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(best,runner),scores::get)==best,"clear winner");
        check(ChineseAutocorrect.choose("abcd","",exact,List.of(best),scores::get)==null,"no context");
        check(ChineseAutocorrect.choose("a","研究",exact,List.of(best),scores::get)==null,"single radical");
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(best),s->s.equals("乙")?1.0:0.0)==null,"weak improvement");
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(best,runner),s->s.equals("甲")?0.0:5.0)==null,"ambiguous repairs");
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(c("xy","abfd","乙",true)),scores::get)==null,"stale source");
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(c("abcd","abfd","甲",true)),scores::get)==null,"same text");
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(InputCandidate.english("abcd","can")),s->100)==null,"English excluded");
        check(ChineseAutocorrect.choose("abcd","研究",exact,List.of(best),s->Double.NaN)==null,"invalid scores");
        DictionaryEngine dictionary=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        check(dictionary.hasCangjiePrefix("oin"),"valid Cangjie extension");
        check(!dictionary.hasCangjiePrefix("zzzzzz"),"invalid Cangjie extension");
        var repairs=ChineseAutocorrect.cangjieRepairs(dictionary,"oimf");
        check(repairs.stream().anyMatch(r->r.text.equals("你")&&r.effectiveCode().equals("onf"))==false,"only one substitution");
        repairs=ChineseAutocorrect.cangjieRepairs(dictionary,"omf");
        check(repairs.stream().anyMatch(r->r.text.equals("你")&&r.effectiveCode().equals("onf")),"Cangjie adjacent typo reaches 你");
        for(var r:repairs)check(r.source.equals("omf")&&r.corrected&&!r.englishOnly(),"mapping preserved");
        QuickDecoder decoder=new QuickDecoder(dictionary,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),OfflineLanguageModel.load(Files.newInputStream(Path.of("src/main/assets/language_model.b64"))));
        QuickTypos typos=new QuickTypos(dictionary,decoder);
        var quickRepairs=typos.suggest("od",Collections.<InputCandidate>emptyList(),"我想見");
        check(quickRepairs.stream().anyMatch(r->r.text.equals("你")),"Quick adjacent typo reaches 你");
        check(decoder.decode("mtjnmmy",(code,text)->0).contains("研究一下"),"existing exact phrase preserved");
        check(ChineseAutocorrect.choose("ab","研究",List.of(c("ab","ab","甲",false)),List.of(c("ab","ad","乙",true)),scores::get)==null,"valid short code protected");
        int automaticCases=0;
        String[] contexts={"我想見","我想食","我想飲","研究","唔","香","開","多"};
        for(String context:contexts)for(String source:List.of("oa","oz","oq","iz","zz","pp","qx","wz","xx","za","xs","xz","qa","qs","qz","gq","fq","xq","zq","bz","od","vr","mm","qo","ha","rr","ab","on","of","my")) {
            var baselines=new ArrayList<InputCandidate>();
            for(String text:dictionary.quickCandidates(source))baselines.add(InputCandidate.chinese(dictionary,source,text));
            var options=typos.suggest(source,baselines.subList(0,Math.min(3,baselines.size())),context);
            var winner=ChineseAutocorrect.choose(source,context,baselines,options,text->decoder.languageScore(context,text));
            if(winner!=null && decoder.supportsCorrection(context,winner.text)) {automaticCases++;System.out.println(context+" + "+source+" -> "+winner.text);}
        }
        check(automaticCases>0,"actual model can automatically correct");
        System.out.println("PASS: "+checks+" checks; "+automaticCases+" real-model automatic cases");
    }
}
