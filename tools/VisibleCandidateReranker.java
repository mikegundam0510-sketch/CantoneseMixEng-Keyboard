package hk.cantonesemixeng.keyboard;

import java.util.*;
import java.util.function.ToDoubleFunction;

/** Reorders an already selected display; it cannot add or discard candidates. */
public final class VisibleCandidateReranker {
    private VisibleCandidateReranker() {}

    /** Least-squares non-increasing projection of the established display scores. */
    static double[] orderedScores(double[] scores) {
        double[] means=new double[scores.length];
        int[] counts=new int[scores.length];
        int blocks=0;
        for(double score:scores) {
            means[blocks]=score;counts[blocks]=1;blocks++;
            while(blocks>1 && means[blocks-2]<means[blocks-1]) {
                int a=counts[blocks-2],b=counts[blocks-1],total=a+b;
                means[blocks-2]=means[blocks-2]*((double)a/total)+means[blocks-1]*((double)b/total);
                counts[blocks-2]=total;blocks--;
            }
        }
        double[] result=new double[scores.length];int at=0;
        for(int i=0;i<blocks;i++) for(int j=0;j<counts[i];j++) result[at++]=means[i];
        return result;
    }

    public static List<String> rerank(List<String> visible, Map<String,Double> scores,
            ToDoubleFunction<String> evidence) {
        List<String> unchanged=new ArrayList<>(visible);
        if(visible.size()<2 || visible.size()>20 || scores==null || evidence==null) return unchanged;
        double[] raw=new double[visible.size()];
        for(int i=0;i<raw.length;i++) {
            Double value=scores.get(visible.get(i));
            if(value==null || !Double.isFinite(value)) return unchanged;
            raw[i]=value;
        }
        double[] base=orderedScores(raw);
        Map<String,Double> combined=new HashMap<>();
        for(int i=0;i<base.length;i++) {
            double value=base[i]+evidence.applyAsDouble(visible.get(i));
            if(!Double.isFinite(value)) return unchanged;
            combined.put(visible.get(i),value);
        }
        // Stable ties retain the established order, including neutral evidence.
        unchanged.sort(Comparator.comparingDouble((String text)->combined.get(text)).reversed());
        return unchanged;
    }
}
