package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Scores cached, unchanged TRAIN displays; labels never enter language inference. */
public final class HeadGateTrainingEvaluation {
    public static void main(String[] args)throws Exception {
        SentenceLanguageRanker nn=SentenceLanguageRanker.load(Files.newInputStream(Path.of(args[0])));
        try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]))) {
            int count=0;
            for(String line:Files.readAllLines(Path.of(args[1]))) {
                String[] f=line.split("\t",-1);
                if(f.length!=7)throw new IllegalArgumentException("Seven-column TRAIN cache required");
                List<String> values=Arrays.asList(f[4].split("\\|"));
                String[] scores=f[5].split("\\|"),supports=f[6].split("\\|");
                Map<String,Double> raw=new HashMap<>(),neural=new HashMap<>(),support=new HashMap<>();
                for(int i=0;i<values.size();i++) {
                    raw.put(values.get(i),Double.valueOf(scores[i]));
                    support.put(values.get(i),Double.valueOf(supports[i]));
                    neural.put(values.get(i),nn.score(f[1],values.get(i)));
                }
                List<String> proposed=VisibleCandidateReranker.rerank(values,raw,neural::get);
                for(String choice:values.subList(1,values.size())) {
                    double[] vector=HeadChangeGate.features(values,raw,neural,support::get,choice);
                    List<String> numbers=new ArrayList<>();for(double v:vector)numbers.add(Double.toHexString(v));
                    out.write(f[0]+"\t"+(values.get(0).equals(f[3])?"1":"0")+"\t"+
                        (choice.equals(f[3])?"1":"0")+"\t"+(choice.equals(proposed.get(0))?"1":"0")+"\t"+
                        String.join("|",numbers)+"\n");
                }
                if(++count%500==0)System.out.println("scored_train_displays="+count);
            }
        }
    }
}
