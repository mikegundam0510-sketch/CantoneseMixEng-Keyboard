package hk.cantonesemixeng.keyboard;

import java.util.*;

/** Randomized complete displays, including neutral evidence and invalid fallback. */
public final class PinnedHeadCheck {
    public static void main(String[] args) {
        Random random=new Random(20261017);
        for(int trial=0;trial<400;trial++) {
            int n=trial%21;List<String> original=new ArrayList<>();
            Map<String,Double> scores=new HashMap<>(),evidence=new HashMap<>();
            for(int i=0;i<n;i++) {
                String word="字"+i;original.add(word);
                scores.put(word,random.nextDouble()*10-5);evidence.put(word,random.nextDouble()*2-1);
            }
            List<String> snapshot=new ArrayList<>(original);Map<String,Double> scoreCopy=new HashMap<>(scores);
            List<String> result=PinnedHeadReranker.rerank(original,scores,evidence::get);
            if(result.size()!=n||!new HashSet<>(result).equals(new HashSet<>(original)))throw new AssertionError("Display changed");
            if(n>0&&!result.get(0).equals(original.get(0)))throw new AssertionError("First choice changed");
            List<String> neural=VisibleCandidateReranker.rerank(original,scores,evidence::get);
            if(n>0)neural.remove(original.get(0));
            if(!result.subList(Math.min(1,n),n).equals(neural))throw new AssertionError("Relative tail changed");
            if(!PinnedHeadReranker.rerank(original,scores,t->0).equals(original))throw new AssertionError("Neutral order changed");
            if(!PinnedHeadReranker.rerank(original,scores,t->.7).equals(original))throw new AssertionError("Constant order changed");
            if(!PinnedHeadReranker.rerank(original,scores,t->Double.NaN).equals(original))throw new AssertionError("Invalid evidence changed order");
            if(!original.equals(snapshot)||!scores.equals(scoreCopy))throw new AssertionError("Inputs mutated");
        }
        List<String> original=Arrays.asList("甲","乙","丙");
        Map<String,Double> scores=new HashMap<>();for(String s:original)scores.put(s,0d);
        List<String> moved=PinnedHeadReranker.rerank(original,scores,s->s.equals("丙")?1:s.equals("乙")?.5:0);
        if(!moved.equals(Arrays.asList("甲","丙","乙")))throw new AssertionError("Tail does not move");
        System.out.println("randomized_displays=400 original_head=true original_set=true exact_relative_tail=true neutral_and_constant=true invalid_fallback=true immutable_inputs=true tail_moves=true");
    }
}
