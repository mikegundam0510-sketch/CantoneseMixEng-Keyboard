package hk.kaiboard.android;

import java.util.*;

/** One adjacent-key substitution only. Exact matches stay separate from repairs. */
public final class QuickTypos {
    private final DictionaryEngine dictionary;
    private final QuickDecoder decoder;
    public QuickTypos(DictionaryEngine dictionary,QuickDecoder decoder){this.dictionary=dictionary;this.decoder=decoder;}
    public static String neighbors(char key) {
        String[] rows={"qwertyuiop","asdfghjkl","zxcvbnm"}; double[] offsets={0,.25,.75};
        int row=-1,column=-1;
        for(int r=0;r<rows.length;r++)if(rows[r].indexOf(key)>=0){row=r;column=rows[r].indexOf(key);break;}
        if(row<0)return "";
        StringBuilder result=new StringBuilder();double x=column+offsets[row];
        for(int r=0;r<rows.length;r++)for(int c=0;c<rows[r].length();c++)
            if(rows[r].charAt(c)!=key && Math.abs(r-row)<=1 && Math.abs(c+offsets[r]-x)<=1.05)result.append(rows[r].charAt(c));
        return result.toString();
    }
    public List<InputCandidate> suggest(String source,List<InputCandidate> baselines,String context) {
        List<InputCandidate> options=new ArrayList<>();
        if(baselines.isEmpty())options.addAll(suggest(source,(InputCandidate)null,context));
        for(int i=0;i<Math.min(3,baselines.size());i++)options.addAll(suggest(source,baselines.get(i),context));
        options.sort(Comparator.comparingDouble((InputCandidate c)->decoder.languageScore(context,c.text)).reversed());
        List<InputCandidate> result=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(InputCandidate candidate:options)if(seen.add(candidate.text)){result.add(candidate);if(result.size()==6)break;}
        return result;
    }
    public List<InputCandidate> suggest(String source,InputCandidate baseline,String context) {
        if(source.isEmpty() || source.length()>48 || !source.matches("[A-Za-z]+"))return Collections.emptyList();
        if(baseline==null || baseline.englishOnly()) {
            if(source.length()>2)return Collections.emptyList();
            baseline=new InputCandidate(source,Collections.singletonList(new InputCandidate.Segment(source,"",false)),false);
        }
        List<InputCandidate> options=new ArrayList<>();int offset=0;
        for(int segmentIndex=0;segmentIndex<baseline.segments.size();segmentIndex++) {
            InputCandidate.Segment segment=baseline.segments.get(segmentIndex);
            if(segment.english || segment.code.length()>2){offset+=segment.code.length();continue;}
            for(int i=0;i<segment.code.length();i++)for(char adjacent:neighbors(Character.toLowerCase(segment.code.charAt(i))).toCharArray()) {
                String corrected=segment.code.substring(0,i)+adjacent+segment.code.substring(i+1);
                List<String> letters=dictionary.quickCandidates(corrected);
                for(int n=0;n<Math.min(2,letters.size());n++) {
                    List<InputCandidate.Segment> segments=new ArrayList<>(baseline.segments);
                    segments.set(segmentIndex,new InputCandidate.Segment(corrected,letters.get(n),false));
                    InputCandidate candidate=new InputCandidate(source,segments,true);
                    if(QuickDecoder.hanText(letters.get(n)) && !candidate.text.equals(baseline.text))options.add(candidate);
                }
            }
            offset+=segment.code.length();
        }
        options.sort(Comparator.comparingDouble((InputCandidate c)->decoder.languageScore(context,c.text)).reversed());
        List<InputCandidate> result=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(InputCandidate candidate:options)if(seen.add(candidate.text)){result.add(candidate);if(result.size()==6)break;}
        return result;
    }
}
