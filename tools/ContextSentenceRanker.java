package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Immutable offline GRU residual; keeps no editor text or personal history. */
public final class ContextSentenceRanker {
    private final int dimension,hidden;
    private final int[] characters;
    private final float cap,strength;
    private final float[] embedding,input,recurrent,bias,output;
    private final float outputBias;
    private ContextSentenceRanker(int dimension,int hidden,int[] characters,float cap,float strength,
            float[] embedding,float[] input,float[] recurrent,float[] bias,float[] output,float outputBias) {
        this.dimension=dimension;this.hidden=hidden;this.characters=characters;this.cap=cap;this.strength=strength;
        this.embedding=embedding;this.input=input;this.recurrent=recurrent;this.bias=bias;this.output=output;this.outputBias=outputBias;
    }
    private static float[] values(DataInputStream data,int count)throws IOException {
        float[] result=new float[count];
        for(int i=0;i<count;i++) {
            result[i]=data.readFloat();
            if(!Float.isFinite(result[i])||Math.abs(result[i])>16)throw new IOException("Invalid recurrent weight");
        }
        return result;
    }
    public static ContextSentenceRanker load(InputStream encoded)throws IOException {
        try(DataInputStream data=new DataInputStream(new BufferedInputStream(
                new GZIPInputStream(Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if(data.readInt()!=0x47525531)throw new IOException("Unsupported context model");
            int dimension=data.readInt(),hidden=data.readInt(),size=data.readInt(),context=data.readInt(),maximum=data.readInt();
            float cap=data.readFloat(),strength=data.readFloat();
            if(dimension<1||dimension>32||hidden<1||hidden>32||size<3||size>8192||context!=12||maximum!=48
                    ||!Float.isFinite(cap)||cap<=0||cap>3||!Float.isFinite(strength)||strength<0||strength>2)
                throw new IOException("Invalid context model header");
            int[] characters=new int[size-3];
            for(int i=0;i<characters.length;i++) {
                characters[i]=data.readInt();
                if(!OfflineLanguageModel.han(characters[i])||i>0&&characters[i]<=characters[i-1])
                    throw new IOException("Invalid context vocabulary");
            }
            float[] embedding=values(data,size*dimension),input=values(data,dimension*3*hidden),
                recurrent=values(data,hidden*3*hidden),bias=values(data,3*hidden),output=values(data,hidden);
            float outputBias=values(data,1)[0];
            if(data.read()!=-1)throw new IOException("Trailing context model bytes");
            return new ContextSentenceRanker(dimension,hidden,characters,cap,strength,embedding,input,recurrent,bias,output,outputBias);
        }catch(IllegalArgumentException e){throw new IOException("Invalid context model encoding",e);}
    }
    private int id(int cp) {
        int at=Arrays.binarySearch(characters,cp);return at<0?1:at+3;
    }
    private static float sigmoid(float value) {
        return (float)(1/(1+Math.exp(-Math.max(-40,Math.min(40,value)))));
    }
    private void step(int id,float[] state,float[] a,float[] b) {
        System.arraycopy(bias,0,a,0,a.length);Arrays.fill(b,0);
        int width=3*hidden;
        for(int i=0;i<dimension;i++) {
            float x=embedding[id*dimension+i];int offset=i*width;
            for(int j=0;j<width;j++)a[j]+=x*input[offset+j];
        }
        for(int i=0;i<hidden;i++) {
            float h=state[i];int offset=i*width;
            for(int j=0;j<width;j++)b[j]+=h*recurrent[offset+j];
        }
        for(int i=0;i<hidden;i++) {
            float z=sigmoid(a[i]+b[i]),r=sigmoid(a[hidden+i]+b[hidden+i]);
            float g=(float)Math.tanh(a[2*hidden+i]+r*b[2*hidden+i]);
            state[i]=(1-z)*state[i]+z*g;
        }
    }
    /** Whole-candidate evidence, at most12 editor-context and48 composing characters. */
    public double score(String preceding,String text) {
        if(strength==0||text.isEmpty())return 0;
        int count=text.codePointCount(0,text.length());if(count>48||!QuickDecoder.hanText(text))return 0;
        int start=preceding.length(),used=0;
        while(start>0&&used<12) {
            int cp=preceding.codePointBefore(start);if(!OfflineLanguageModel.han(cp))break;
            start-=Character.charCount(cp);used++;
        }
        float[] state=new float[hidden],a=new float[3*hidden],b=new float[3*hidden];
        for(int at=start;at<preceding.length();) {
            int cp=preceding.codePointAt(at);at+=Character.charCount(cp);step(id(cp),state,a,b);
        }
        step(2,state,a,b);
        for(int at=0;at<text.length();) {
            int cp=text.codePointAt(at);at+=Character.charCount(cp);step(id(cp),state,a,b);
        }
        float value=outputBias;for(int i=0;i<hidden;i++)value+=state[i]*output[i];
        return strength*cap*Math.tanh(value);
    }
    public long arrayBytes() {
        return 4L*(characters.length+embedding.length+input.length+recurrent.length+bias.length+output.length+1);
    }
}
