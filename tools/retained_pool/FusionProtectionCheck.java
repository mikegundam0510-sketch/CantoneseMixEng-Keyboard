package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.ToIntBiFunction;

/** Check actual current-generator baseline, optional expansion and user choices. */
public final class FusionProtectionCheck {
    private static List<String> text(List<InputCandidate> items) {
        List<String> result=new ArrayList<>();for(InputCandidate item:items)result.add(item.text);return result;
    }
    public static void main(String[] args) throws Exception {
        FusionIntegratedEvaluation.assets=Path.of(args[0]);
        DictionaryEngine d=new DictionaryEngine(FusionIntegratedEvaluation.a("cangjie5.base.dict.yaml"),
            FusionIntegratedEvaluation.a("english.txt"),FusionIntegratedEvaluation.a("character_frequencies.tsv"));
        QuickDecoder baseline=FusionIntegratedEvaluation.decoder(d,false),enabled=FusionIntegratedEvaluation.decoder(d,true);
        DirectCodeGenerator legacy=DirectCodeGenerator.load(Files.newInputStream(Path.of(args[0]).resolve("code_generator.b64")));
        DirectCodeGenerator expanded=DirectCodeGenerator.load(Files.newInputStream(Path.of(args[0]).resolve("expanded_generator.b64")));
        QuickDecoder wrongAlphabet=FusionIntegratedEvaluation.decoder(d,legacy,legacy);
        QuickDecoder noLegacy=FusionIntegratedEvaluation.decoder(d,null,expanded);
        QuickDecoder noModels=FusionIntegratedEvaluation.decoder(d,null,null);
        int checked=0;boolean active=false;
        for(String line:Files.readAllLines(Path.of(args[1]))) {
            String[] f=line.split("\t",-1);String code=f[2],context=f[1];
            List<String> parent=Arrays.asList(f[3].split("\\|"));
            List<String> old=baseline.decode(code,(c,w)->0,context);
            if(!old.equals(parent))throw new AssertionError("Missing expansion differs from actual deployed generator");
            if(!wrongAlphabet.decode(code,(c,w)->0,context).equals(old))throw new AssertionError("No additions fallback differs");
            if(!noLegacy.decode(code,(c,w)->0,context).equals(noModels.decode(code,(c,w)->0,context)))
                throw new AssertionError("Expansion ran without original provider");
            List<String> updated=enabled.decode(code,(c,w)->0,context);active|=!updated.equals(old);
            if(!enabled.decodeBaseline(code,(c,w)->0,context,null).equals(baseline.decodeBaseline(code,(c,w)->0,context,null)))
                throw new AssertionError("Mixed bypass differs");
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
        if(checked!=4 || !active)throw new AssertionError("Incomplete active expansion fixtures");
        System.out.println("protection_cases=4 active=true deployed_fallback=true no_additions=true no_legacy=true legacy_confirmed=true positive_negative_context=true mixed_translation=true");
    }
}
