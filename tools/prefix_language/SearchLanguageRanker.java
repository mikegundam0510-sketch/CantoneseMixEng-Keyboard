package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Immutable causal character model; no editor text or personal records retained. */
public final class SearchLanguageRanker {
    private final int dimension, hidden;
    private final int[] characters, parents, leafParents;
    private final byte[] parentBits, leafBits;
    private final float strength;
    private final float[] prior, embedding, input, recurrent, bias, output, outputBias;

    private SearchLanguageRanker(int dimension, int hidden, int[] characters,
            int[] parents, int[] leafParents, byte[] parentBits, byte[] leafBits, float strength,
            float[] prior, float[] embedding, float[] input, float[] recurrent,
            float[] bias, float[] output, float[] outputBias) {
        this.dimension=dimension; this.hidden=hidden; this.characters=characters;
        this.parents=parents; this.leafParents=leafParents; this.parentBits=parentBits;
        this.leafBits=leafBits; this.strength=strength; this.prior=prior; this.embedding=embedding;
        this.input=input; this.recurrent=recurrent; this.bias=bias; this.output=output; this.outputBias=outputBias;
    }

    private static float[] values(DataInputStream data, int count) throws IOException {
        float[] result=new float[count];
        for(int i=0;i<count;i++) {
            result[i]=data.readFloat();
            if(!Float.isFinite(result[i]) || Math.abs(result[i])>64)
                throw new IOException("Invalid sentence language weight");
        }
        return result;
    }

    public static SearchLanguageRanker load(InputStream encoded) throws IOException {
        try(DataInputStream data=new DataInputStream(new BufferedInputStream(
                new GZIPInputStream(Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if(data.readInt()!=0x534c4d31) throw new IOException("Unsupported sentence language model");
            int dimension=data.readInt(), hidden=data.readInt(), size=data.readInt();
            int context=data.readInt(), maximum=data.readInt();
            float cap=data.readFloat(), strength=data.readFloat();
            if(dimension<1 || dimension>32 || hidden<1 || hidden>32 || size<5 || size>4096
                    || context!=12 || maximum!=48 || cap!=2 || !Float.isFinite(strength)
                    || strength<0 || strength>1) throw new IOException("Invalid sentence language header");
            int[] characters=new int[size-3];
            for(int i=0;i<characters.length;i++) {
                characters[i]=data.readInt();
                if(!OfflineLanguageModel.han(characters[i]) || i>0 && characters[i]<=characters[i-1])
                    throw new IOException("Invalid sentence language vocabulary");
            }
            int nodes=size-3;
            int[] parents=new int[nodes], leafParents=new int[size];
            byte[] parentBits=new byte[nodes], leafBits=new byte[size];
            Arrays.fill(parents,-2); Arrays.fill(leafParents,-2); parents[0]=-1;
            for(int node=0;node<nodes;node++) for(int bit=0;bit<2;bit++) {
                int child=data.readInt();
                if(child>=0) {
                    if(child<=node || child>=nodes || parents[child]!=-2)
                        throw new IOException("Invalid sentence language tree");
                    parents[child]=node; parentBits[child]=(byte)bit;
                } else {
                    long token=-(long)child-1;
                    if(token<1 || token==2 || token>=size || leafParents[(int)token]!=-2)
                        throw new IOException("Invalid sentence language leaf");
                    leafParents[(int)token]=node; leafBits[(int)token]=(byte)bit;
                }
            }
            for(int node=0;node<nodes;node++) {
                int depth=0;
                for(int at=node;at>=0;at=parents[at]) {
                    if(parents[at]==-2 || ++depth>32) throw new IOException("Disconnected or deep sentence tree");
                }
            }
            for(int token=1;token<size;token++)
                if(token!=2 && leafParents[token]<0) throw new IOException("Missing sentence tree leaf");
            float[] prior=values(data,size);
            for(float value:prior) if(value>=0 || value< -40) throw new IOException("Invalid sentence prior");
            float[] embedding=values(data,size*dimension), input=values(data,dimension*3*hidden),
                recurrent=values(data,hidden*3*hidden), bias=values(data,3*hidden),
                output=values(data,nodes*hidden), outputBias=values(data,nodes);
            if(data.read()!=-1) throw new IOException("Trailing sentence model bytes");
            return new SearchLanguageRanker(dimension,hidden,characters,parents,leafParents,parentBits,
                leafBits,strength,prior,embedding,input,recurrent,bias,output,outputBias);
        } catch(IllegalArgumentException e) {
            throw new IOException("Invalid sentence language encoding",e);
        }
    }

    private int id(int cp) {
        int at=Arrays.binarySearch(characters,cp); return at<0?1:at+3;
    }
    private static float sigmoid(float value) {
        return (float)(1/(1+Math.exp(-Math.max(-40,Math.min(40,value)))));
    }
    private void step(int token, float[] state, float[] a, float[] b) {
        System.arraycopy(bias,0,a,0,a.length); Arrays.fill(b,0);
        int width=3*hidden;
        for(int i=0;i<dimension;i++) {
            float x=embedding[token*dimension+i]; int offset=i*width;
            for(int j=0;j<width;j++) a[j]+=x*input[offset+j];
        }
        for(int i=0;i<hidden;i++) {
            float h=state[i]; int offset=i*width;
            for(int j=0;j<width;j++) b[j]+=h*recurrent[offset+j];
        }
        for(int i=0;i<hidden;i++) {
            float z=sigmoid(a[i]+b[i]), r=sigmoid(a[hidden+i]+b[hidden+i]);
            float g=(float)Math.tanh(a[2*hidden+i]+r*b[2*hidden+i]);
            state[i]=(1-z)*state[i]+z*g;
        }
    }
    private double logProbability(int token, float[] state) {
        double result=0;
        int node=leafParents[token], bit=leafBits[token];
        while(node>=0) {
            float value=outputBias[node]; int offset=node*hidden;
            for(int i=0;i<hidden;i++) value+=state[i]*output[offset+i];
            double signed=bit==1?-value:value;
            result-=Math.max(0,signed)+Math.log1p(Math.exp(-Math.abs(signed)));
            bit=parentBits[node]; node=parents[node];
        }
        return result;
    }

    /** Mean conditional-vs-unigram evidence; bounded to [-1,1] at fixed strength0.5. */
    public double score(String preceding, String text) {
        if(strength==0 || text.isEmpty()) return 0;
        int count=text.codePointCount(0,text.length());
        if(count>48 || !QuickDecoder.hanText(text)) return 0;
        int start=preceding.length(), used=0;
        while(start>0 && used<12) {
            int cp=preceding.codePointBefore(start);
            if(!OfflineLanguageModel.han(cp)) break;
            start-=Character.charCount(cp); used++;
        }
        float[] state=new float[hidden], a=new float[3*hidden], b=new float[3*hidden];
        step(2,state,a,b);
        for(int at=start;at<preceding.length();) {
            int cp=preceding.codePointAt(at); at+=Character.charCount(cp); step(id(cp),state,a,b);
        }
        double sum=0;
        for(int at=0;at<text.length();) {
            int cp=text.codePointAt(at); at+=Character.charCount(cp); int token=id(cp);
            sum+=logProbability(token,state)-prior[token];
            if(at<text.length()) step(token,state,a,b);
        }
        return strength*2*Math.tanh(sum/count);
    }
    /** State belongs to one decode; the immutable model retains no editor text. */
    public Session session(String preceding) { return new Session(preceding); }
    public final class Session {
        private final Map<String,State> cache=new HashMap<>();
        private int queries;
        private final float[] a=new float[3*hidden], b=new float[3*hidden];
        private final class State {
            final float[] hiddenState; final double sum; final int count;
            State(float[] h,double s,int c){hiddenState=h;sum=s;count=c;}
        }
        private Session(String preceding) {
            float[] h=new float[hidden];step(2,h,a,b);
            int start=preceding.length(),count=0;
            while(start>0&&count<12) {
                int cp=preceding.codePointBefore(start);if(!OfflineLanguageModel.han(cp))break;
                start-=Character.charCount(cp);count++;
            }
            for(int at=start;at<preceding.length();) {
                int cp=preceding.codePointAt(at);at+=Character.charCount(cp);step(id(cp),h,a,b);
            }
            cache.put("",new State(h,0,0));
        }
        private State state(String text) {
            State found=cache.get(text);if(found!=null)return found;
            if(cache.size()>=2048)return null;
            int end=text.offsetByCodePoints(text.length(),-1);
            State previous=state(text.substring(0,end));if(previous==null||cache.size()>=2048)return null;
            int token=id(text.codePointAt(end));
            double sum=previous.sum+logProbability(token,previous.hiddenState)-prior[token];
            float[] h=previous.hiddenState.clone();step(token,h,a,b);
            State result=new State(h,sum,previous.count+1);cache.put(text,result);return result;
        }
        public boolean available(){return queries<128&&cache.size()<2048;}
        public double score(String text) {
            if(!available()||text.isEmpty()||text.codePointCount(0,text.length())>48||!QuickDecoder.hanText(text))return Double.NaN;
            queries++;State value=state(text);
            return value==null?Double.NaN:strength*2*Math.tanh(value.sum/value.count);
        }
        public int stateCount(){return cache.size();}
        public int queryCount(){return queries;}
    }
    public long arrayBytes() {
        return 4L*(characters.length+parents.length+leafParents.length+prior.length+embedding.length
            +input.length+recurrent.length+bias.length+output.length+outputBias.length)+parentBits.length+leafBits.length;
    }
}
