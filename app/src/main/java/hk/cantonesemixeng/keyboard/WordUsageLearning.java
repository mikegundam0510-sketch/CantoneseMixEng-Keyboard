package hk.cantonesemixeng.keyboard;

import java.util.*;
import java.util.function.Predicate;

/** Explicit selections only. No editor-derived character chains become learning keys. */
final class WordUsageLearning {
    private WordUsageLearning() {}
    static String key(String code, boolean quick, boolean cangjie, String text) {
        if (code == null || !code.matches("[a-zA-Z]{1,48}") || !QuickDecoder.hanText(text)) return null;
        if (LearningRanker.isLearnable(text)) return LearningRanker.key(code,quick,cangjie,text);
        int size=text.codePointCount(0,text.length());
        return size>=2 && size<=32 ? "U:"+LearningRanker.key(code,quick,cangjie,text) : null;
    }
    static Set<String> selectedKeys(InputCandidate choice, Predicate<String> known,
            boolean quick, boolean cangjie, boolean enabled, boolean protectedField) {
        Set<String> result=new LinkedHashSet<>();
        if (!enabled || protectedField || choice==null || choice.source.isEmpty()) return result;
        boolean chinese=choice.segments.stream().noneMatch(s->s.english||s.translated);
        if (chinese) {
            if (LearningRanker.isLearnable(choice.text) || known.test(choice.text)) {
                String key=key(choice.effectiveCode(),quick,cangjie,choice.text);
                if (key!=null) result.add(key);
            }
        } else {
            // An explicitly selected mixed choice confirms its Chinese parts,
            // but never creates a cross-language phrase or a sentence key.
            for (InputCandidate.Segment part:choice.segments)
                if (!part.english && !part.translated && (LearningRanker.isLearnable(part.text)||known.test(part.text))) {
                    String key=key(part.code,quick,cangjie,part.text);if(key!=null)result.add(key);
                }
        }
        return result;
    }
    static List<String> selectedWords(String context, InputCandidate choice, Predicate<String> known,
            boolean enabled, boolean protectedField) {
        if (!enabled || protectedField || choice==null || !QuickDecoder.hanText(choice.text)
                || choice.segments.stream().anyMatch(s->s.english||s.translated)) return Collections.emptyList();
        if (!choice.source.isEmpty())
            return known.test(choice.text) ? Collections.singletonList(choice.text) : Collections.emptyList();
        // Only a clicked association may use its preceding text. Remember the
        // one completed attested word, not every substring crossing the cursor.
        int[] before=context.codePoints().toArray();
        for(int size=Math.min(7,before.length);size>=1;size--) {
            String word=new String(before,before.length-size,size)+choice.text;
            if(known.test(word))return Collections.singletonList(word);
        }
        return known.test(choice.text)?Collections.singletonList(choice.text):Collections.emptyList();
    }
    static Set<String> rejectedKeys(InputCandidate old,InputCandidate selected,Predicate<String> known,
            boolean quick,boolean cangjie) {
        Set<String> result=new LinkedHashSet<>();
        if(old==null||selected==null||old.source.isEmpty()||!old.source.equals(selected.source)
                ||old.text.equals(selected.text)||old.englishOnly()||selected.englishOnly())return result;
        result.addAll(selectedKeys(old,known,quick,cangjie,true,false));
        result.removeAll(selectedKeys(selected,known,quick,cangjie,true,false));
        Set<String> kept=new HashSet<>(selectedWords("",selected,known,true,false));
        for(String word:selectedWords("",old,known,true,false))if(!kept.contains(word))result.add(PhraseLearning.key(word));
        return result;
    }
}
