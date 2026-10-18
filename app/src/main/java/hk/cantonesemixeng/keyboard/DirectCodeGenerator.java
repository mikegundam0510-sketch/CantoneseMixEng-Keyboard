package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Immutable code-conditioned generator. All history and search state is per call. */
public final class DirectCodeGenerator {
    private static final int H = 32, C = 16, V = 2251, BEAM = 24;
    private final int[] characters;
    private final Map<String,int[]> byCode;
    private final float[] embedding, input, recurrent, bias, wordH, wordC, wordBias,
        codeEmbedding, codeRecurrent, lengthH, lengthC, lengthBias;

    private DirectCodeGenerator(int[] characters, Map<String,int[]> byCode, float[][] weights) {
        this.characters=characters;this.byCode=byCode;
        embedding=weights[0];input=weights[1];recurrent=weights[2];bias=weights[3];
        wordH=weights[4];wordC=weights[5];wordBias=weights[6];codeEmbedding=weights[7];
        codeRecurrent=weights[8];lengthH=weights[9];lengthC=weights[10];lengthBias=weights[11];
    }
    public static DirectCodeGenerator load(InputStream encoded) throws IOException {
        try (DataInputStream in=new DataInputStream(new BufferedInputStream(
                new GZIPInputStream(Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if(in.readInt()!=0x44434731 || in.readInt()!=32 || in.readInt()!=32 || in.readInt()!=16
                    || in.readInt()!=V || in.readInt()!=12 || in.readInt()!=48 || in.readInt()!=BEAM)
                throw new IOException("Invalid direct-code model header");
            int[] characters=new int[V-3];Map<String,List<Integer>> items=new HashMap<>();
            for(int i=0;i<characters.length;i++) {
                int cp=in.readInt();characters[i]=cp;
                if(!OfflineLanguageModel.han(cp) || i>0 && cp<=characters[i-1])
                    throw new IOException("Invalid direct-code vocabulary");
                int count=in.readUnsignedByte();
                if(count<1 || count>16)throw new IOException("Invalid direct-code aliases");
                Set<String> seen=new HashSet<>();
                for(int j=0;j<count;j++) {
                    String code=in.readUTF();
                    if(!code.matches("[a-z]{1,2}") || !seen.add(code))throw new IOException("Invalid direct code");
                    items.computeIfAbsent(code,k->new ArrayList<>()).add(i+3);
                }
            }
            int[] sizes={V*H,H*3*H,H*3*H,3*H,V*H,V*C,V,27*C,C*C,H*2,C*2,2};
            float[][] weights=new float[sizes.length][];
            for(int k=0;k<sizes.length;k++) {
                weights[k]=new float[sizes[k]];
                for(int j=0;j<sizes[k];j++) {
                    float value=in.readFloat();
                    if(!Float.isFinite(value) || Math.abs(value)>64)throw new IOException("Invalid direct-code weight");
                    weights[k][j]=value;
                }
            }
            if(in.read()!=-1)throw new IOException("Trailing direct-code bytes");
            Map<String,int[]> byCode=new HashMap<>();
            for(Map.Entry<String,List<Integer>> entry:items.entrySet())
                byCode.put(entry.getKey(),entry.getValue().stream().mapToInt(i->i).toArray());
            return new DirectCodeGenerator(characters,byCode,weights);
        } catch(IllegalArgumentException failure) {throw new IOException("Invalid direct-code encoding",failure);}
    }
    private int id(int cp) {int at=Arrays.binarySearch(characters,cp);return at<0?1:at+3;}
    private static float sigmoid(float x) {return (float)(1/(1+Math.exp(-Math.max(-40,Math.min(40,x)))));}
    private float[] step(int token,float[] previous) {
        float[] a=new float[3*H],b=new float[3*H],next=new float[H];
        for(int i=0;i<H;i++)for(int j=0;j<3*H;j++) {
            a[j]+=embedding[token*H+i]*input[i*3*H+j];
            b[j]+=previous[i]*recurrent[i*3*H+j];
        }
        for(int j=0;j<a.length;j++)a[j]+=bias[j];
        for(int i=0;i<H;i++) {
            float z=sigmoid(a[i]+b[i]),r=sigmoid(a[H+i]+b[H+i]);
            float g=(float)Math.tanh(a[2*H+i]+r*b[2*H+i]);
            next[i]=(1-z)*previous[i]+z*g;
        }
        return next;
    }
    private float[][] codeStates(String code) {
        float[][] result=new float[code.length()+1][C];
        for(int p=code.length()-1;p>=0;p--)for(int j=0;j<C;j++) {
            float value=0;for(int i=0;i<C;i++)value+=result[p+1][i]*codeRecurrent[i*C+j];
            result[p][j]=(float)Math.tanh(codeEmbedding[(code.charAt(p)-'a'+1)*C+j]+value);
        }
        return result;
    }
    private static int textOrder(String left,String right) {
        int i=0,j=0;
        while(i<left.length() && j<right.length()) {
            int a=left.codePointAt(i),b=right.codePointAt(j);if(a!=b)return Integer.compare(a,b);
            i+=Character.charCount(a);j+=Character.charCount(b);
        }
        return Integer.compare(left.length()-i,right.length()-j);
    }
    static final class Result {
        final String text;final double score;
        Result(String text,double score){this.text=text;this.score=score;}
    }
    private static final class Path {
        final String text;final double score;final float[] parent;
        Path(String text,double score,float[] parent){this.text=text;this.score=score;this.parent=parent;}
    }
    private static final class Extension {
        final int path,token,order;final double score;
        Extension(int path,int token,int order,double score){this.path=path;this.token=token;this.order=order;this.score=score;}
    }
    public List<String> generate(String code,String context) {
        List<String> result=new ArrayList<>();for(Result item:generateScored(code,context))result.add(item.text);return result;
    }
    List<Result> generateScored(String raw,String context) {
        if(raw==null || raw.length()<1 || raw.length()>48 || !raw.matches("[a-zA-Z]+"))return Collections.emptyList();
        String code=raw.toLowerCase(Locale.ROOT);float[][] cs=codeStates(code);
        float[] initial=step(2,new float[H]);
        int start=context.length(),used=0;
        while(start>0 && used<12) {
            int cp=context.codePointBefore(start);if(!OfflineLanguageModel.han(cp))break;
            start-=Character.charCount(cp);used++;
        }
        for(int at=start;at<context.length();) {
            int cp=context.codePointAt(at);at+=Character.charCount(cp);initial=step(id(cp),initial);
        }
        List<List<Path>> lattice=new ArrayList<>();
        for(int i=0;i<=code.length();i++)lattice.add(new ArrayList<>());
        lattice.get(0).add(new Path("",0,initial));Map<String,float[]> states=new HashMap<>();states.put("",initial);
        for(int pos=0;pos<code.length();pos++) {
            if(Thread.currentThread().isInterrupted())return Collections.emptyList();
            Map<String,Path> unique=new LinkedHashMap<>();
            for(Path path:lattice.get(pos)) {
                Path old=unique.get(path.text);if(old==null || path.score>old.score)unique.put(path.text,path);
            }
            List<Path> paths=new ArrayList<>(unique.values());
            paths.sort((a,b)->{int score=Double.compare(b.score,a.score);return score!=0?score:textOrder(a.text,b.text);});
            if(paths.size()>BEAM)paths=new ArrayList<>(paths.subList(0,BEAM));
            if(paths.isEmpty())continue;
            List<Integer> ids=new ArrayList<>(),lengths=new ArrayList<>();
            for(int length=1;length<=2 && pos+length<=code.length();length++) {
                int[] choices=byCode.get(code.substring(pos,pos+length));if(choices==null)continue;
                for(int token:choices){ids.add(token);lengths.add(length);}
            }
            if(ids.isEmpty())continue;
            float[][] hidden=new float[paths.size()][];
            for(int i=0;i<paths.size();i++) {
                Path path=paths.get(i);float[] state=states.get(path.text);
                if(state==null){state=step(id(path.text.codePointBefore(path.text.length())),path.parent);states.put(path.text,state);}
                hidden[i]=state;
            }
            float[] constant=new float[ids.size()];float[][] wh=new float[ids.size()][H];
            for(int j=0;j<ids.size();j++) {
                int token=ids.get(j),n=lengths.get(j)-1;float value=0;
                for(int i=0;i<C;i++)value+=(wordC[token*C+i]+lengthC[i*2+n])*cs[pos][i];
                constant[j]=value;
                for(int i=0;i<H;i++)wh[j][i]=wordH[token*H+i]+lengthH[i*2+n];
            }
            float[][] logp=new float[paths.size()][ids.size()];
            for(int p=0;p<paths.size();p++) {
                float maximum=-Float.MAX_VALUE;
                for(int j=0;j<ids.size();j++) {
                    float value=0;for(int i=0;i<H;i++)value+=hidden[p][i]*wh[j][i];
                    value+=constant[j];value+=wordBias[ids.get(j)];value+=lengthBias[lengths.get(j)-1];
                    logp[p][j]=value;maximum=Math.max(maximum,value);
                }
                float sum=0;for(int j=0;j<ids.size();j++){logp[p][j]-=maximum;sum+=(float)Math.exp(logp[p][j]);}
                float logZ=(float)Math.log(sum);for(int j=0;j<ids.size();j++)logp[p][j]-=logZ;
            }
            for(int length=1;length<=2;length++) {
                List<Extension> extensions=new ArrayList<>();int order=0;
                for(int p=0;p<paths.size();p++)for(int j=0;j<ids.size();j++)if(lengths.get(j)==length)
                    extensions.add(new Extension(p,ids.get(j),order++,paths.get(p).score+logp[p][j]));
                extensions.sort(Comparator.comparingDouble((Extension e)->e.score).reversed().thenComparingInt(e->e.order));
                for(Extension e:extensions.subList(0,Math.min(BEAM,extensions.size()))) {
                    String text=paths.get(e.path).text+new String(Character.toChars(characters[e.token-3]));
                    lattice.get(pos+length).add(new Path(text,e.score,hidden[e.path]));
                }
            }
        }
        Map<String,Double> best=new HashMap<>();
        for(Path path:lattice.get(code.length()))best.merge(path.text,path.score,Math::max);
        List<Result> result=new ArrayList<>();for(Map.Entry<String,Double> entry:best.entrySet())result.add(new Result(entry.getKey(),entry.getValue()));
        result.sort((a,b)->{int score=Double.compare(b.score,a.score);return score!=0?score:textOrder(a.text,b.text);});
        return new ArrayList<>(result.subList(0,Math.min(20,result.size())));
    }
}
