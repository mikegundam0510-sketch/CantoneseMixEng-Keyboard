package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.ToIntBiFunction;

/** Exercise the optional model through the actual enabled decoder and mixed engines. */
public final class ProtectionCheck {
    private static List<String> text(List<InputCandidate> items) {
        List<String> result=new ArrayList<>();for(InputCandidate item:items)result.add(item.text);return result;
    }
    public static void main(String[] args)throws Exception {
        IntegratedEvaluation.assets=Path.of(args[0]);
        DictionaryEngine d=new DictionaryEngine(IntegratedEvaluation.a("cangjie5.base.dict.yaml"),
            IntegratedEvaluation.a("english.txt"),IntegratedEvaluation.a("character_frequencies.tsv"));
        QuickDecoder baseline=IntegratedEvaluation.decoder(d,null);
        QuickDecoder enabled=IntegratedEvaluation.decoder(d,DirectCodeGenerator.load(Files.newInputStream(Path.of(args[0]).resolve("code_generator.b64"))));
        int checked=0;boolean active=false;
        for(String line:Files.readAllLines(Path.of(args[1]))) {
            String[] f=line.split("\t",-1);String code=f[2],context=f[1];
            List<String> parent=f[3].isEmpty()?Collections.emptyList():Arrays.asList(f[3].split("\\|"));
            List<String> old=baseline.decode(code,(c,w)->0,context);
            if(!old.equals(parent))throw new AssertionError("Missing-generator fallback differs from parent");
            if(!enabled.decodeBaseline(code,(c,w)->0,context,null).equals(baseline.decodeBaseline(code,(c,w)->0,context,null)))
                throw new AssertionError("Mixed bypass differs");
            List<String> updated=enabled.decode(code,(c,w)->0,context);active|=!updated.equals(old);
            InputCandidate first=InputCandidate.chinese(d,code,old.get(0));
            Set<String> keys=ContextLearning.selectedKeys(context,first,true,false);
            for(int weight:new int[]{5,-5}) {
                ContextLearning.Preferences preferences=new ContextLearning.Preferences(keys,k->weight);
                if(!enabled.decode(code,(c,w)->0,context,preferences).equals(baseline.decode(code,(c,w)->0,context,preferences)))
                    throw new AssertionError("Confirmed/rejected context differs");
            }
            ToIntBiFunction<String,String> familiar=(c,w)->5;
            if(!enabled.decode(code,familiar,context).equals(baseline.decode(code,familiar,context)))
                throw new AssertionError("Confirmed legacy sequence differs");
            EnglishEngine english=new EnglishEngine(new StringReader("hello\nCAN\n"));
            CandidateEngine before=new CandidateEngine(d,baseline,english),after=new CandidateEngine(d,enabled,english);
            if(!text(before.mixed(code+"hello",context,Collections.emptyList(),(c,w)->0))
                    .equals(text(after.mixed(code+"hello",context,Collections.emptyList(),(c,w)->0))))
                throw new AssertionError("Mixed choices differ");
            EnglishChineseEngine meanings=new EnglishChineseEngine(new StringReader("can\t可以\t1\n"));
            if(!text(meanings.mixedSuffix(code+"CAN",context,before,(c,w)->0))
                    .equals(text(meanings.mixedSuffix(code+"CAN",context,after,(c,w)->0))))
                throw new AssertionError("Translated prefix differs");
            checked++;
        }
        if(!active)throw new AssertionError("Generator never active in wiring fixture");
        System.out.println("protection_cases="+checked+" active=true optional_fallback=true legacy_confirmed=true positive_negative_context=true mixed_translation=true");
    }
}
