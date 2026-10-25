package hk.cantonesemixeng.keyboard;

import java.util.*;
import java.util.function.Predicate;
import java.util.function.ToIntBiFunction;

/** Pure third-key decision; committing these automatic choices must not train usage. */
final class WordTopOut {
    private WordTopOut() {}
    static List<InputCandidate> choices(DictionaryEngine dictionary,WordLexicon words,String input,char next,
            ToIntBiFunction<String,String> usage,Predicate<String> englishPrefix) {
        if(dictionary==null||words==null||input==null||!input.matches("[a-z]{2,48}")||next<'a'||next>'z')
            return Collections.emptyList();
        String extended=input+next;
        if(words.captures(extended,usage)||englishPrefix.test(extended))return Collections.emptyList();
        List<InputCandidate> result=new ArrayList<>();
        for(int at=0;at+1<input.length();at+=2) {
            String code=input.substring(at,at+2);
            List<String> singles=LearningRanker.rank(dictionary.quickCandidates(code),word->usage.applyAsInt(code,word));
            String first=null;for(String word:singles)if(LearningRanker.isLearnable(word)){first=word;break;}
            if(first==null)return Collections.emptyList();
            result.add(InputCandidate.chinese(dictionary,code,first));
        }
        return result;
    }
}
