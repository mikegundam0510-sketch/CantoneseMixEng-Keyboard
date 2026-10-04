package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Immutable, primitive-array 5-gram model trained offline from attributed corpora. */
public final class OfflineLanguageModel {
    private static final long SEED = 1469598103934665603L, PRIME = 1099511628211L;
    private final long[] keys;
    private final float[] probabilities, backoffs;
    private final float unknown;
    private OfflineLanguageModel(long[] keys, float[] probabilities, float[] backoffs, float unknown) {
        this.keys=keys; this.probabilities=probabilities; this.backoffs=backoffs; this.unknown=unknown;
    }
    public static OfflineLanguageModel load(InputStream encoded) throws IOException {
        try (DataInputStream data = new DataInputStream(new BufferedInputStream(
                new GZIPInputStream(Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded, 32768)), 32768)))) {
            if (data.readInt()!=0x4B4C4D32 || data.readInt()!=5) throw new IOException("Unsupported language model");
            int count=data.readInt(); float unknown=data.readFloat();
            if (count<1 || count>2000000 || !Float.isFinite(unknown) || unknown<=0 || unknown>=1)
                throw new IOException("Invalid language model header");
            long[] keys=new long[count]; float[] probs=new float[count], backs=new float[count];
            for(int i=0;i<count;i++) {
                keys[i]=data.readLong(); probs[i]=data.readFloat(); backs[i]=data.readFloat();
                if(i>0 && keys[i]<=keys[i-1] || !Float.isFinite(probs[i]) || probs[i]<0 || probs[i]>1
                        || !Float.isFinite(backs[i]) || backs[i]<0 || backs[i]>1)
                    throw new IOException("Invalid language model row");
            }
            if(data.read()!=-1)throw new IOException("Unexpected language model data");
            return new OfflineLanguageModel(keys,probs,backs,unknown);
        } catch(IllegalArgumentException e) { throw new IOException("Invalid model encoding",e); }
    }
    static long hash(int[] text,int start,int length) {
        long result=SEED^length;
        for(int i=start;i<start+length;i++)result=(result^text[i])*PRIME;
        return result;
    }
    private int index(int[] text,int start,int length) { return Arrays.binarySearch(keys,hash(text,start,length)); }
    private static boolean han(int cp) { return Character.UnicodeScript.of(cp)==Character.UnicodeScript.HAN; }
    public static String contextTail(String text) {
        int start=text.length(), count=0;
        while(start>0 && count<4) {
            int cp=text.codePointBefore(start); if(!han(cp))break;
            start-=Character.charCount(cp);count++;
        }
        return text.substring(start);
    }
    public double score(String preceding,String text) {
        int[] history=new int[5];int used=0;
        for(int cp:contextTail(preceding).codePoints().toArray())history[used++]=cp;
        double score=0;
        for(int at=0;at<text.length();) {
            int cp=text.codePointAt(at);at+=Character.charCount(cp);
            if(!han(cp)){used=0;continue;}
            history[used]=cp;
            int one=index(history,used,1);
            double p=one<0?unknown:probabilities[one];
            for(int n=2;n<=Math.min(5,used+1);n++) {
                int start=used+1-n;
                int context=index(history,start,n-1);
                if(context>=0) {
                    int gram=index(history,start,n);
                    p=(gram<0?0:probabilities[gram])+backoffs[context]*p;
                }
            }
            score+=Math.log(Math.max(unknown,p));
            if(used==4)System.arraycopy(history,1,history,0,4);else used++;
        }
        return score;
    }
    public int entryCount() { return keys.length; }
    public long arrayBytes() { return 16L*keys.length; }
}

