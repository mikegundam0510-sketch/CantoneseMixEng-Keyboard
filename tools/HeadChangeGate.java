package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.function.ToDoubleFunction;
import java.util.zip.GZIPInputStream;

/** A small TRAIN-fitted decision about replacing an established first choice. */
public final class HeadChangeGate {
    public static final int DIMENSIONS=20;
    private final double threshold;
    private final double[] mean,scale,weights;
    private HeadChangeGate(double threshold,double[] mean,double[] scale,double[] weights) {
        this.threshold=threshold;this.mean=mean;this.scale=scale;this.weights=weights;
    }
    public static HeadChangeGate load(InputStream encoded)throws IOException {
        try(DataInputStream in=new DataInputStream(new GZIPInputStream(Base64.getMimeDecoder().wrap(encoded)))) {
            if(in.readInt()!=0x48434731||in.readInt()!=DIMENSIONS)throw new IOException("Invalid head gate schema");
            double threshold=in.readDouble();
            if(!Double.isFinite(threshold)||threshold<.5||threshold>=1)throw new IOException("Invalid head gate threshold");
            double[][] arrays=new double[3][DIMENSIONS];
            for(int a=0;a<3;a++)for(int i=0;i<DIMENSIONS;i++) {
                double v=in.readDouble();
                if(!Double.isFinite(v)||Math.abs(v)>1000||(a==1&&v<=0))throw new IOException("Invalid head gate parameter");
                arrays[a][i]=v;
            }
            if(in.read()!=-1)throw new IOException("Trailing head gate data");
            return new HeadChangeGate(threshold,arrays[0],arrays[1],arrays[2]);
        }catch(IllegalArgumentException e){throw new IOException("Invalid head gate encoding",e);}
    }
    public double probability(double[] features) {
        if(features.length!=DIMENSIONS)return Double.NaN;
        double logit=0;
        for(int i=0;i<DIMENSIONS;i++) {
            if(!Double.isFinite(features[i]))return Double.NaN;
            logit+=weights[i]*(features[i]-mean[i])/scale[i];
        }
        if(!Double.isFinite(logit))return Double.NaN;
        return logit>=0?1/(1+Math.exp(-logit)):Math.exp(logit)/(1+Math.exp(logit));
    }
    public boolean approve(double[] features){return probability(features)>=threshold;}

    /** No character, word or complete-sentence identity is stored as a feature. */
    public static double[] features(List<String> visible,Map<String,Double> raw,
            Map<String,Double> neural,ToDoubleFunction<String> support,String challenger) {
        String head=visible.get(0);int at=visible.indexOf(challenger),n=visible.size();
        if(at<1)throw new IllegalArgumentException("Existing nonleading challenger required");
        double[] base=new double[n];for(int i=0;i<n;i++)base[i]=raw.get(visible.get(i));
        base=VisibleCandidateReranker.orderedScores(base);
        double h=neural.get(head),c=neural.get(challenger),diff=(c-h)/2;
        double gap=Math.tanh((raw.get(challenger)-raw.get(head))/4),projected=(base[at]-base[0])/2;
        double hs=Math.tanh(support.applyAsDouble(head)/4),cs=Math.tanh(support.applyAsDouble(challenger)/4);
        double sd=Math.tanh((support.applyAsDouble(challenger)-support.applyAsDouble(head))/4);
        int[] left=head.codePoints().toArray(),right=challenger.codePoints().toArray();
        int prefix=0,suffix=0,equal=0,length=Math.max(left.length,right.length);
        while(prefix<Math.min(left.length,right.length)&&left[prefix]==right[prefix])prefix++;
        while(suffix<Math.min(left.length,right.length)-prefix&&left[left.length-1-suffix]==right[right.length-1-suffix])suffix++;
        for(int i=0;i<Math.min(left.length,right.length);i++)if(left[i]==right[i])equal++;
        double bestOther=-Double.MAX_VALUE;
        for(int i=0;i<n;i++)if(i!=at)bestOther=Math.max(bestOther,base[i]+neural.get(visible.get(i)));
        return new double[]{1,gap,projected,diff,projected+diff,h,c,hs,cs,sd,
            (double)at/19,Math.min(2,(double)length/24),(double)prefix/length,(double)suffix/length,
            1-(double)equal/length,gap*diff,hs*diff,sd*diff,
            (base[at]+c-bestOther)/2,(base[0]-base[1])/2};
    }

    public static List<String> rerank(List<String> visible,Map<String,Double> raw,
            ToDoubleFunction<String> scorer,ToDoubleFunction<String> support,HeadChangeGate gate) {
        if(gate==null||visible.size()<2)return new ArrayList<>(visible);
        Map<String,Double> neural=new HashMap<>();
        List<String> ranked=VisibleCandidateReranker.rerank(visible,raw,
            text->neural.computeIfAbsent(text,scorer::applyAsDouble));
        if(!ranked.get(0).equals(visible.get(0))
                &&!gate.approve(features(visible,raw,neural,support,ranked.get(0)))) {
            ranked.remove(visible.get(0));ranked.add(0,visible.get(0));
        }
        return ranked;
    }
}
