package hk.kaiboard.android;

import java.util.*;
import java.util.function.ToIntBiFunction;

/** Exact candidates with editable mappings, including bounded mixed Chinese/English spans. */
public final class CandidateEngine {
    private final DictionaryEngine dictionary;
    private final QuickDecoder quick;
    private final EnglishEngine english;
    public CandidateEngine(DictionaryEngine dictionary, QuickDecoder quick, EnglishEngine english) {
        this.dictionary=dictionary; this.quick=quick; this.english=english;
    }
    public List<InputCandidate> chinese(String code, String context, boolean continuous, boolean useQuick,
            boolean useCangjie, ToIntBiFunction<String,String> learned) {
        LinkedHashMap<String,InputCandidate> result=new LinkedHashMap<>();
        if (useQuick && continuous && code.length()>2)
            for(String text:quick.decode(code,learned,context)) result.put(text,InputCandidate.chinese(dictionary,code,text));
        List<String> singles=dictionary.lookup(code,useQuick,useCangjie,false);
        singles.remove(code);
        if (!context.isEmpty()) singles.sort(Comparator.comparingDouble((String text)->
            QuickDecoder.hanText(text) ? quick.languageScore(context,text) : Double.NEGATIVE_INFINITY).reversed());
        singles=LearningRanker.rank(singles,w->learned.applyAsInt(code,w));
        for(String text:singles)result.putIfAbsent(text,InputCandidate.chinese(dictionary,code,text));
        return new ArrayList<>(result.values());
    }
    double languageScore(String context, String text) { return quick.languageScore(context, text); }

    public List<InputCandidate> mixed(String input,String context,Collection<String> personal,
            ToIntBiFunction<String,String> learned) {
        List<int[]> spans=english.spans(input,personal);
        if(spans.isEmpty() || spans.size()==1 && spans.get(0)[0]==0 && spans.get(0)[1]==input.length())return Collections.emptyList();
        List<List<InputCandidate.Segment>> paths=new ArrayList<>();paths.add(new ArrayList<>());
        int position=0;
        for(int[] span:spans) {
            if(span[0]>position)paths=appendChinese(paths,input.substring(position,span[0]),context,learned);
            for(List<InputCandidate.Segment> path:paths) {
                String word=input.substring(span[0],span[1]);path.add(new InputCandidate.Segment(word,word,true));
            }
            position=span[1];
        }
        if(position<input.length())paths=appendChinese(paths,input.substring(position),context,learned);
        List<InputCandidate> result=new ArrayList<>();
        for(List<InputCandidate.Segment> path:paths)result.add(new InputCandidate(input,path,false));
        return result;
    }
    private List<List<InputCandidate.Segment>> appendChinese(List<List<InputCandidate.Segment>> paths,String code,
            String context,ToIntBiFunction<String,String> learned) {
        List<List<InputCandidate.Segment>> result=new ArrayList<>();
        for(List<InputCandidate.Segment> path:paths) {
            String preceding=context;
            for (InputCandidate.Segment segment : path) preceding+=segment.text;
            List<InputCandidate> options=chinese(code,preceding,true,true,false,learned);
            for(int i=0;i<Math.min(3,options.size());i++) {
                List<InputCandidate.Segment> combined=new ArrayList<>(path);combined.addAll(options.get(i).segments);
                result.add(combined);if(result.size()==12)return result;
            }
        }
        return result;
    }
}

