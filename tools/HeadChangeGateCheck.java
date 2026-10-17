package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

public final class HeadChangeGateCheck {
    static byte[] encoded(double threshold,double intercept)throws Exception {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(bytes))) {
            out.writeInt(0x48434731);out.writeInt(20);out.writeDouble(threshold);
            for(int a=0;a<3;a++)for(int i=0;i<20;i++)out.writeDouble(a==1?1:a==2&&i==0?intercept:0);
        }
        return Base64.getEncoder().encode(bytes.toByteArray());
    }
    public static void main(String[] args)throws Exception {
        HeadChangeGate yes=HeadChangeGate.load(new ByteArrayInputStream(encoded(.75,20)));
        HeadChangeGate no=HeadChangeGate.load(new ByteArrayInputStream(encoded(.75,-20)));
        List<String> old=Arrays.asList("甲乙","丙乙","丁乙");
        Map<String,Double> raw=new HashMap<>(),neural=new HashMap<>();
        for(int i=0;i<3;i++){raw.put(old.get(i),-.1*i);neural.put(old.get(i),.5*i);}
        List<String> accepted=HeadChangeGate.rerank(old,raw,neural::get,t->0,yes);
        List<String> rejected=HeadChangeGate.rerank(old,raw,neural::get,t->0,no);
        if(!accepted.equals(Arrays.asList("丁乙","丙乙","甲乙")))throw new AssertionError("Approve path disconnected");
        if(!rejected.equals(Arrays.asList("甲乙","丁乙","丙乙")))throw new AssertionError("Protection must retain reranked tail");
        if(!HeadChangeGate.rerank(old,raw,neural::get,t->0,null).equals(old))throw new AssertionError("Missing gate fallback changed");
        double[] f=HeadChangeGate.features(old,raw,neural,t->0,"丁乙");f[4]=Double.NaN;
        if(no.approve(f)||yes.approve(f))throw new AssertionError("Nonfinite input approved");
        int malformed=0;
        for(double threshold:new double[]{-.1,.49,1,Double.NaN,Double.POSITIVE_INFINITY}) {
            try{HeadChangeGate.load(new ByteArrayInputStream(encoded(threshold,0)));throw new AssertionError("Bad threshold accepted");}
            catch(IOException expected){malformed++;}
        }
        for(double intercept:new double[]{1001,Double.NaN,Double.NEGATIVE_INFINITY}) {
            try{HeadChangeGate.load(new ByteArrayInputStream(encoded(.75,intercept)));throw new AssertionError("Bad parameter accepted");}
            catch(IOException expected){malformed++;}
        }
        if(args.length==2) {
            HeadChangeGate fitted=HeadChangeGate.load(Files.newInputStream(Path.of(args[0])));int checked=0;
            for(String line:Files.readAllLines(Path.of(args[1]))) {
                String[] row=line.split("\t");String[] fields=row[0].split("\\|");double[] vector=new double[20];
                for(int i=0;i<20;i++)vector[i]=Double.valueOf(fields[i]);
                double expected=Double.valueOf(row[1]);
                if(Math.abs(fitted.probability(vector)-expected)>1e-11)throw new AssertionError("Python/Java probability mismatch");
                checked++;
            }
            System.out.println("fitted_probability_parity="+checked);
        }
        System.out.println("repair=true protection=true stable_tail=true null_fallback=true nonfinite_rejection=true malformed_rejected="+malformed);
    }
}
