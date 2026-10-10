package hk.kaiboard.android;

import java.util.*;
import java.util.function.ToIntFunction;

/** Bounded code-aligned two/three-character choices; never a sentence key. */
final class ContextLearning {
    static final int MAX_RECORDS=512;
    private ContextLearning() {}
    static String tail(String text) {
        int at=text.length(), count=0;
        while(at>0 && count<2 && OfflineLanguageModel.han(text.codePointBefore(at))) {
            at-=Character.charCount(text.codePointBefore(at));count++;
        }
        return text.substring(at);
    }
    static String key(String code,String before,String character) {
        return "S:"+code.toLowerCase(Locale.ROOT)+":"+before+":"+character;
    }
    static Set<String> selectedKeys(String context,InputCandidate candidate,boolean enabled,boolean protectedField) {
        Set<String> result=new LinkedHashSet<>();
        if(!enabled || protectedField || candidate==null) return result;
        String history=tail(context);
        for(InputCandidate.Segment segment:candidate.segments) {
            if(segment.english || segment.translated || !LearningRanker.isLearnable(segment.text)
                    || !segment.code.matches("[a-zA-Z]{1,5}")) { history="";continue; }
            addKeys(result,history,segment.code,segment.text);
            history=tail(history+segment.text);
        }
        return result;
    }
    private static void addKeys(Set<String> result,String history,String code,String character) {
        int count=history.codePointCount(0,history.length());
        for(int size=1;size<=count;size++)
            result.add(key(code,history.substring(history.offsetByCodePoints(0,count-size)),character));
    }
    static int weight(String context,String code,String character,ToIntFunction<String> counts) {
        String history=tail(context);
        Set<String> keys=new LinkedHashSet<>();addKeys(keys,history,code,character);
        int result=0;
        // The longer matching context wins; an explicit rejection must stay negative.
        for(String key:keys) {
            int value=counts.applyAsInt(key);
            if(value!=0) result=value;
        }
        return result;
    }
    static String evictionKey(Map<String,?> values,String incoming) {
        if(values.containsKey(incoming)) return null;
        List<String> keys=new ArrayList<>();
        for(String key:values.keySet()) if(key.startsWith("S:")) keys.add(key);
        if(keys.size()<MAX_RECORDS) return null;
        return Collections.min(keys,Comparator.comparingInt((String key)->
            values.get(key) instanceof Integer ? (Integer)values.get(key) : 0).thenComparing(key->key));
    }
    static boolean supports(String context,InputCandidate candidate,Preferences preferences) {
        if(preferences==null || candidate==null) return false;
        String history=tail(context);boolean matched=false;
        for(InputCandidate.Segment segment:candidate.segments) {
            if(segment.english || segment.translated || !LearningRanker.isLearnable(segment.text)
                    || !segment.code.matches("[a-zA-Z]{1,5}")) return false;
            if(!history.isEmpty()) {
                if(preferences.weight(history,segment.code,segment.text)<=0) return false;
                matched=true;
            }
            history=tail(history+segment.text);
        }
        return matched;
    }
    static Set<String> rejectedKeys(String context,InputCandidate previous,InputCandidate selected) {
        if(previous==null || selected==null || previous.source.isEmpty() || !previous.source.equals(selected.source)
                || previous.text.equals(selected.text) || previous.englishOnly() || selected.englishOnly()
                || selected.segments.stream().allMatch(s->s.translated)) return new LinkedHashSet<>();
        Set<String> result=selectedKeys(context,previous,true,false);
        result.removeAll(selectedKeys(context,selected,true,false));
        return result;
    }
    static final class Preferences {
        private final Map<String,Set<String>> choices=new HashMap<>();
        private final ToIntFunction<String> counts;
        Preferences(Collection<String> keys,ToIntFunction<String> counts) {
            this.counts=counts;
            for(String key:keys) {
                String[] parts=key.split(":",-1);
                if(parts.length==4 && parts[0].equals("S") && parts[1].matches("[a-z]{1,5}")
                        && !parts[2].isEmpty() && parts[2].equals(tail(parts[2])) && LearningRanker.isLearnable(parts[3]))
                    choices.computeIfAbsent(parts[1]+":"+parts[2],k->new LinkedHashSet<>()).add(parts[3]);
            }
        }
        int weight(String context,String code,String character) {
            return ContextLearning.weight(context,code,character,counts);
        }
        Set<String> favored(String context,String code) {
            String history=tail(context);int count=history.codePointCount(0,history.length());
            Set<String> result=new LinkedHashSet<>();
            for(int size=1;size<=count;size++) {
                String before=history.substring(history.offsetByCodePoints(0,count-size));
                for(String character:choices.getOrDefault(code+":"+before,Collections.emptySet()))
                    if(weight(history,code,character)>0) result.add(character);
            }
            return result;
        }
    }
}
