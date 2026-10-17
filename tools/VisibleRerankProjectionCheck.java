package hk.cantonesemixeng.keyboard;

import java.util.*;

/** Mathematical and availability contracts, independent of corpus hit rates. */
public final class VisibleRerankProjectionCheck {
    private static void require(boolean value,String message) {
        if(!value)throw new AssertionError(message);
    }
    public static void main(String[] args) {
        double[] expected={4,4,3,3};
        double[] actual=VisibleCandidateReranker.orderedScores(new double[]{3,5,2,4});
        require(Arrays.equals(actual,expected),"Incorrect least-squares projection");
        Random random=new Random(20261017);
        for(int trial=0;trial<200;trial++) {
            List<String> visible=new ArrayList<>();Map<String,Double> scores=new HashMap<>();
            int count=1+random.nextInt(20);double[] raw=new double[count];
            for(int i=0;i<count;i++) {
                String text="candidate"+i;visible.add(text);raw[i]=random.nextGaussian()*5;scores.put(text,raw[i]);
            }
            double[] ordered=VisibleCandidateReranker.orderedScores(raw);
            for(int i=1;i<count;i++)require(ordered[i-1]>=ordered[i],"Projection is not monotone");
            List<String> original=new ArrayList<>(visible);Map<String,Double> oldScores=new HashMap<>(scores);
            require(visible.equals(VisibleCandidateReranker.rerank(visible,scores,t->0)),"Neutral scorer changes order");
            require(visible.equals(VisibleCandidateReranker.rerank(visible,scores,t->.5)),"Constant scorer changes order");
            Map<String,Double> residual=new HashMap<>();
            for(String s:visible)residual.put(s,random.nextDouble()*2-1);
            List<String> ranked=VisibleCandidateReranker.rerank(visible,scores,residual::get);
            require(ranked.size()==count&&new HashSet<>(ranked).equals(new HashSet<>(visible)),"Display set changed");
            require(visible.equals(original)&&scores.equals(oldScores),"Input mutated");
            require(visible.equals(VisibleCandidateReranker.rerank(visible,scores,t->Double.NaN)),"Invalid scorer lacks fallback");
            scores.put(visible.get(0),Double.NaN);
            require(visible.equals(VisibleCandidateReranker.rerank(visible,scores,t->.5)),"Invalid base lacks fallback");
        }
        List<String> pair=Arrays.asList("old","new");Map<String,Double> scores=new HashMap<>();
        scores.put("old",2.);scores.put("new",1.);
        require(VisibleCandidateReranker.rerank(pair,scores,t->t.equals("old")?-1:1).get(0).equals("new"),"Model cannot change a close rank");
        scores.put("new",-1.);
        require(VisibleCandidateReranker.rerank(pair,scores,t->t.equals("old")?-1:1).equals(pair),"Bounded residual closes a larger score gap");
        System.out.println("randomized_displays=200 neutral_and_constant_order=true availability=true immutable_inputs=true finite_fallback=true");
    }
}
