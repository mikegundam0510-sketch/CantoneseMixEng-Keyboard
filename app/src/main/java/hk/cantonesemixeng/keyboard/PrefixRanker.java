package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Immutable evidence for a prefix and vocabulary hints matching the remaining codes. */
public final class PrefixRanker {
    private final Map<String, Float> weights;
    private final float strength, limit;
    private PrefixRanker(Map<String,Float> weights,float strength,float limit) {
        this.weights=Collections.unmodifiableMap(weights);this.strength=strength;this.limit=limit;
    }
    public static PrefixRanker load(InputStream encoded)throws IOException {
        try(DataInputStream in=new DataInputStream(new BufferedInputStream(new GZIPInputStream(
                Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if(in.readInt()!=0x50524b31)throw new IOException("Unsupported prefix ranker");
            int count=in.readInt();float strength=in.readFloat(),limit=in.readFloat();
            if(count<0||count>16000||!Float.isFinite(strength)||strength<0||strength>2
                ||!Float.isFinite(limit)||limit<=0||limit>2)throw new IOException("Invalid prefix bounds");
            Map<String,Float> weights=new HashMap<>();
            for(int i=0;i<count;i++) {
                int size=in.readUnsignedShort();if(size<3||size>64)throw new IOException("Invalid prefix key size");
                byte[] bytes=new byte[size];in.readFully(bytes);
                String key=StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString();float value=in.readFloat();
                if(!validKey(key)||!Float.isFinite(value)||Math.abs(value)>1.5||weights.put(key,value)!=null)
                    throw new IOException("Invalid prefix feature");
            }
            if(in.read()!=-1)throw new IOException("Unexpected prefix data");
            return new PrefixRanker(weights,strength,limit);
        } catch(IllegalArgumentException e){throw new IOException("Invalid prefix encoding",e);}
    }
    private static boolean validKey(String key) {
        String[] p=key.split("\\|",-1);
        if(p.length==2&&(p[0].equals("W")||p[0].equals("E"))) {
            int n=p[1].codePointCount(0,p[1].length());
            return SentenceRanker.hanText(p[1])&&(p[0].equals("W")?n>=2&&n<=4:n>=1&&n<=3);
        }
        if(p.length!=4)return false;
        if(p[0].equals("K")||p[0].equals("R"))return Arrays.asList("2","3","4","5").contains(p[2])
            &&(p[0].equals("K")?oneHan(p[1])&&oneHan(p[3]):roleKey(p[1])&&roleKey(p[3]));
        if(!p[1].equals("0")&&!p[1].equals("1"))return false;
        if(p[0].equals("C"))return roleKey(p[2])&&roleKey(p[3]);
        return p[0].equals("B")&&shortHan(p[2])&&shortHan(p[3]);
    }
    private static boolean roleKey(String s){return s.length()==1&&"PNATVOMB".contains(s);}
    private static boolean oneHan(String s){return SentenceRanker.hanText(s)&&s.codePointCount(0,s.length())==1;}
    private static boolean shortHan(String s){return SentenceRanker.hanText(s)&&s.codePointCount(0,s.length())<=2;}
    static String tail(String value) {
        int start=value.length(),count=0;
        while(start>0&&count<12&&SentenceRanker.han(value.codePointBefore(start))) {
            start-=Character.charCount(value.codePointBefore(start));count++;
        }
        return value.substring(start);
    }
    static Map<String,Integer> features(String context,String text,List<String> hints) {
        String history=tail(context+text);
        Map<String,Integer> result=new LinkedHashMap<>();
        for(Map.Entry<String,Integer> e:SentenceRanker.features("",history).entrySet())
            if("W|K|R|E|".contains(e.getKey().substring(0,2)))result.put(e.getKey(),e.getValue());
        int count=history.codePointCount(0,history.length());
        for(int i=0;i<Math.min(6,hints.size());i++) {
            String hint=hints.get(i);int end=0,n=0;
            while(end<hint.length()&&n<2&&SentenceRanker.han(hint.codePointAt(end))){end+=Character.charCount(hint.codePointAt(end));n++;}
            String head=hint.substring(0,end),tier=i<2?"0":"1";
            for(int a=1;a<=Math.min(2,count);a++)for(int b=1;b<=n;b++)
                add(result,"B|"+tier+"|"+history.substring(history.offsetByCodePoints(history.length(),-a))+"|"+head.substring(0,head.offsetByCodePoints(0,b)));
            if(count>0&&n>0)add(result,"C|"+tier+"|"+SentenceRanker.role(history.codePointBefore(history.length()),2)+"|"+SentenceRanker.role(head.codePointAt(0),2));
        }
        return result;
    }
    private static void add(Map<String,Integer> result,String key){result.merge(key,1,(a,b)->Math.min(2,a+b));}
    public double correction(String context,String text,List<String> hints) {
        if(strength==0)return 0;
        double total=0;
        for(Map.Entry<String,Integer> e:features(context,text,hints).entrySet())total+=weights.getOrDefault(e.getKey(),0f)*e.getValue();
        return strength*Math.max(-limit,Math.min(limit,total));
    }
    /** Cheap positive endpoint evidence retrieves candidates for full pairwise scoring. */
    double proposal(String text,List<String> hints) {
        if(strength==0||text.isEmpty())return 0;
        int count=text.codePointCount(0,text.length());double total=0;
        for(int n=2;n<=Math.min(3,count);n++)total+=positive("W|"+text.substring(text.offsetByCodePoints(text.length(),-n)));
        String last=text.substring(text.offsetByCodePoints(text.length(),-1));total+=positive("E|"+last);
        for(int i=0;i<Math.min(2,hints.size());i++) {
            String hint=hints.get(i);if(!hint.isEmpty())total+=positive("B|0|"+last+"|"+hint.substring(0,Character.charCount(hint.codePointAt(0))));
        }
        return strength*Math.min(limit,total);
    }
    private double positive(String key){return Math.max(0,weights.getOrDefault(key,0f));}
}
