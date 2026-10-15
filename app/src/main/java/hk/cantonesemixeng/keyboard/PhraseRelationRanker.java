package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Bounded word-role evidence; unknown relations never prohibit a candidate. */
public final class PhraseRelationRanker {
    private static final String ROLES="PNVQMADRFCTOBXZU";
    private static final Map<String,String> OVERRIDES=new HashMap<>();
    private static final Map<String,String> QUESTIONS=new HashMap<>();
    private static final Map<String,String> NOUN_CATEGORIES=new HashMap<>();
    static {
        override("P","我 你 佢 我哋 你哋 佢哋 您 大家 自己");
        override("X","唔 冇 未 唔好 唔使 唔洗 唔駛 毋須 咪 毋");
        override("Z","咗 緊 過");
        override("Q","個 件 張 本 碟 杯 支 間 條 架 份 次 位 隻 部 對 塊 張 座 袋 碗 盒 瓶 啲");
        override("D","咁 噉 就 先 再 都 又 啱啱 而家 今日 聽日");
        override("M","一 二 三 四 五 六 七 八 九 十 百 千 萬 兩 幾");
        override("R","畀 俾 比 給 同 對 向 喺 在 到 從");
        override("C","但 但係 所以 因為 如果 或者 同埋 而且 不過");
        override("T","呀 啊 喇 啦 㗎 囉 喎 呢 啫 咩 嗎");
        override("V","係 有 要 會 想 可以 能夠 應該 需要 繼續 完善 改善 研究 修改 調整 檢查 打字 返工 收工");
        override("U","乜 乜嘢 點 點解 點樣 幾時 邊 邊度 邊個 幾多 係咪 有冇 會唔會 要唔要 可唔可以");
        QUESTIONS.put("未","Y");QUESTIONS.put("咩","W");QUESTIONS.put("嗎","Y");QUESTIONS.put("呢","U");
        nouns("F","飯 粉 麵 粥 餅 包 菜 湯 茶 水 汁 酒 肉 魚 蛋 糖 果 餸 豬腸粉 腸粉 米粉 河粉 意粉 炒飯 湯麵 牛腩麵 奶茶 咖啡 可樂 汽水 啤酒 豆漿 涼茶 麵包 菠蘿包 蛋糕 雞蛋 雞翼 牛肉 豬肉 雞肉 水果 蘋果 香蕉 花生 木瓜 三文治 沙律 甜品 雪糕 麥皮 麥片");
        nouns("D","功課 文件 報告 資料 表格 電郵 訊息 紙 紙張 書 書本 報紙 信 信件 筆記 清單 名單 帳單 賬單 收據 合約 合同 表 申請表");
        nouns("H","人 老細 同事 朋友 同學 老師 學生 家人 哥哥 姐姐 妹妹 弟弟 爸爸 媽媽 阿哥 阿爸 阿媽 司機 主席 議員 客人 員工 職員 醫生 病人 市民 小朋友");
        nouns("L","屋企 公司 學校 餐廳 車站 屋 房 屋苑 街 市場 超市 商場 地鐵站 巴士站 港鐵站 公園 工廠 醫院 住宅 地址");
        nouns("E","車 汽車 巴士 的士 電腦 手機 相機 電視 冷氣 雪櫃 洗衣機 機器 單車 船 飛機 收音機");
    }
    private static void override(String role,String words) {for(String word:words.split(" "))OVERRIDES.put(word,role);}
    private static void nouns(String category,String words) {
        for(String word:words.split(" ")) {NOUN_CATEGORIES.put(word,category);OVERRIDES.putIfAbsent(word,"N");}
    }
    private final Map<String,String> lexicon;
    private final Map<String,Float> weights;
    private final float strength,limit;
    private final boolean aligned;
    private final boolean expandedPool;
    private final float headMargin,headLift;
    private final Map<String,Float> headWeights;
    private final float headStrength,headLimit;

    private PhraseRelationRanker(Map<String,String> lexicon,Map<String,Float> weights,float strength,float limit,int format,float headMargin,float headLift,
            Map<String,Float> headWeights,float headStrength,float headLimit) {
        this.lexicon=Collections.unmodifiableMap(lexicon);this.weights=Collections.unmodifiableMap(weights);
        this.strength=strength;this.limit=limit;
        this.aligned=format!=0x50525231;this.expandedPool=format==0x50525233;
        this.headMargin=headMargin;this.headLift=headLift;
        this.headWeights=Collections.unmodifiableMap(headWeights);this.headStrength=headStrength;this.headLimit=headLimit;
    }
    private static String readString(DataInputStream input,int maximum) throws IOException {
        int size=input.readUnsignedShort();if(size<1||size>maximum)throw new IOException("Invalid relation text size");
        byte[] bytes=new byte[size];input.readFully(bytes);
        return StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString();
    }
    private static boolean word(String text,int maximum) {
        int size=text.codePointCount(0,text.length());return size>=1&&size<=maximum&&SentenceRanker.hanText(text);
    }
    private static boolean role(String text) {return text.length()==1&&ROLES.contains(text);}
    private static boolean sequence(String text,int minimum,int maximum) {
        return text.length()>=minimum&&text.length()<=maximum&&text.chars().allMatch(c->ROLES.indexOf(c)>=0);
    }
    private static boolean category(String text) {return text.length()==1&&"FDHLEG".contains(text);}
    private static boolean validFeature(String key) {
        String[] p=key.split("\\|",-1);
        if(p.length==2)return p[0].equals("G")&&sequence(p[1],2,4);
        if(p.length==3) {
            switch(p[0]) {
                case "B":return role(p[1])&&role(p[2]);
                case "SV":case "NV":return word(p[1],4)&&word(p[2],4);
                case "SR":return p[1].equals("P")&&word(p[2],4);
                case "CN":case "VO":return word(p[1],4)&&category(p[2]);
                case "CH":case "VH":return word(p[1],4)&&word(p[2],1);
                case "VQ":return word(p[1],4)&&p[2].length()==1&&"YWU".contains(p[2]);
                case "AV":return p[1].length()==1&&"YW".contains(p[1])&&word(p[2],4);
                case "Q":return p[1].length()==1&&"YWU".contains(p[1])&&sequence(p[2],0,3);
                default:return false;
            }
        }
        return p.length==4&&(p[0].equals("SVO")?p[1].equals("P"):p[0].equals("NVO")&&word(p[1],4))
            &&word(p[2],4)&&category(p[3]);
    }
    public static PhraseRelationRanker load(InputStream encoded) throws IOException {
        try(DataInputStream in=new DataInputStream(new BufferedInputStream(new GZIPInputStream(
                Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            int magic=in.readInt();
            if(magic!=0x50525231&&magic!=0x50525232&&magic!=0x50525233)throw new IOException("Unsupported phrase relations");
            int words=in.readInt(),features=in.readInt();float strength=in.readFloat(),limit=in.readFloat();
            float headMargin=magic==0x50525233?in.readFloat():0,headLift=magic==0x50525233?in.readFloat():0;
            boolean headDisabled=headMargin==0&&headLift==0;
            if(magic==0x50525233&&!headDisabled&&(!Float.isFinite(headMargin)||headMargin<.5||headMargin>1
                    ||!Float.isFinite(headLift)||headLift<.5||headLift>1))throw new IOException("Invalid head promotion bounds");
            if(words<0||words>20000||features<0||features>6000||!Float.isFinite(strength)||strength<0||strength>1.5
                    ||!Float.isFinite(limit)||limit<=0||limit>2)throw new IOException("Invalid relation bounds");
            Map<String,String> lexicon=new HashMap<>();Map<String,Float> weights=new HashMap<>();
            for(int i=0;i<words;i++) {
                String text=readString(in,16),r=String.valueOf((char)in.readUnsignedByte());int count=in.readUnsignedShort();
                if(!word(text,4)||!role(r)||count==0||lexicon.put(text,r)!=null)throw new IOException("Invalid relation lexicon");
            }
            for(int i=0;i<features;i++) {
                String key=readString(in,96);float value=in.readFloat();
                if(!validFeature(key)||!Float.isFinite(value)||Math.abs(value)>1.5||weights.put(key,value)!=null)
                    throw new IOException("Invalid relation feature");
            }
            Map<String,Float> headWeights=new HashMap<>();float headStrength=0,headLimit=2;
            if(magic==0x50525233) {
                int size=in.readInt();headStrength=in.readFloat();headLimit=in.readFloat();
                if(size<0||size>6000||!Float.isFinite(headStrength)||headStrength<0||headStrength>1.5
                        ||!Float.isFinite(headLimit)||headLimit<=0||headLimit>2)throw new IOException("Invalid head model bounds");
                if(headDisabled&&(size!=0||headStrength!=0))throw new IOException("Disabled head model has weights");
                for(int i=0;i<size;i++) {
                    String key=readString(in,96);float value=in.readFloat();
                    if(!validFeature(key)||!Float.isFinite(value)||Math.abs(value)>1.5||headWeights.put(key,value)!=null)
                        throw new IOException("Invalid head feature");
                }
            }
            if(in.read()!=-1)throw new IOException("Trailing relation data");
            return new PhraseRelationRanker(lexicon,weights,strength,limit,magic,headMargin,headLift,headWeights,headStrength,headLimit);
        }catch(IllegalArgumentException e){throw new IOException("Invalid relation encoding",e);}
    }
    private static String nounCategory(String word) {
        return NOUN_CATEGORIES.getOrDefault(word,"G");
    }
    private static final class Token {
        final String text,role;final boolean active;
        Token(String text,String role,boolean active){this.text=text;this.role=role;this.active=active;}
    }
    private List<Token> tokens(String preceding,String text) {
        int start=preceding.length(),count=0;
        while(start>0&&count<12&&SentenceRanker.han(preceding.codePointBefore(start))) {
            start-=Character.charCount(preceding.codePointBefore(start));count++;
        }
        String prefix=preceding.substring(start);int[] whole=(prefix+text).codePoints().toArray();int boundary=count;
        List<Token> result=new ArrayList<>();
        for(int at=0;at<whole.length;) {
            if(!SentenceRanker.han(whole[at])) {result.add(new Token(new String(whole,at,1),"B",at+1>boundary));at++;continue;}
            String value=new String(whole,at,1),r=OVERRIDES.getOrDefault(value,lexicon.getOrDefault(value,"O"));int size=1;
            for(int n=Math.min(4,whole.length-at);n>1;n--) {
                String candidate=new String(whole,at,n);
                if(!SentenceRanker.hanText(candidate))continue;
                if(OVERRIDES.containsKey(candidate)||lexicon.containsKey(candidate)) {
                    value=candidate;r=OVERRIDES.getOrDefault(candidate,lexicon.get(candidate));size=n;break;
                }
            }
            int end=at+size;if(end==whole.length&&QUESTIONS.containsKey(value))r="T";
            result.add(new Token(value,r,end>boundary));at=end;
        }
        return result;
    }
    private static void add(Map<String,Integer> result,String key) {result.merge(key,1,(a,b)->Math.min(2,a+b));}
    private static boolean stop(String role,String choices) {return choices.contains(role);}
    private static String tailRole(List<Token> history,int size) {
        StringBuilder s=new StringBuilder();for(int i=Math.max(0,history.size()-size);i<history.size();i++)s.append(history.get(i).role);return s.toString();
    }
    Map<String,Integer> features(String preceding,String text) {
        Map<String,Integer> result=new LinkedHashMap<>();List<Token> history=new ArrayList<>();
        for(Token token:tokens(preceding,text)) {
            String value=token.text,r=token.role;int end=history.size();
            if(r.equals("B")){history.clear();continue;}
            if(token.active) {
                String seq=tailRole(history,3)+r;
                for(int n=2;n<=Math.min(4,seq.length());n++)add(result,"G|"+seq.substring(seq.length()-n));
                if(end>0)add(result,"B|"+history.get(end-1).role+"|"+r);
                if(r.equals("V")) {
                    for(int i=end-1;i>=Math.max(0,end-4);i--) {
                        Token left=history.get(i);
                        if(left.role.equals("P")){add(result,"SV|"+left.text+"|"+value);add(result,"SR|P|"+value);break;}
                        if(stop(left.role,"CT"))break;
                    }
                    for(int i=end-1;i>=Math.max(0,end-3);i--) {
                        Token left=history.get(i);if(left.role.equals("X")){add(result,"NV|"+left.text+"|"+value);break;}
                        if(stop(left.role,"PCTV"))break;
                    }
                    for(int i=end-1;i>=Math.max(0,end-4);i--) {
                        Token left=history.get(i);
                        if(left.role.equals("U")) {
                            String ask=Arrays.asList("係咪","有冇","會唔會","要唔要","可唔可以").contains(left.text)?"Y":"W";
                            add(result,"AV|"+ask+"|"+value);break;
                        }
                        if(stop(left.role,"CT"))break;
                    }
                }
                if(r.equals("N")) {
                    String cat=nounCategory(value),head=new String(Character.toChars(value.codePointBefore(value.length())));
                    for(int i=end-1;i>=Math.max(0,end-3);i--) {
                        Token left=history.get(i);
                        if(left.role.equals("Q")){add(result,"CN|"+left.text+"|"+cat);add(result,"CH|"+left.text+"|"+head);break;}
                        if(!stop(left.role,"ADM"))break;
                    }
                    for(int i=end-1;i>Math.max(-1,end-5);i--) {
                        Token left=history.get(i);
                        if(left.role.equals("V")) {
                            add(result,"VO|"+left.text+"|"+cat);add(result,"VH|"+left.text+"|"+head);
                            boolean subject=false;for(int j=Math.max(0,i-3);j<i;j++)if(history.get(j).role.equals("P"))subject=true;
                            if(subject)add(result,"SVO|P|"+left.text+"|"+cat);
                            for(int j=i-1;j>=Math.max(0,i-3);j--) {
                                Token neg=history.get(j);
                                if(neg.role.equals("X")){add(result,"NVO|"+neg.text+"|"+left.text+"|"+cat);break;}
                                if(stop(neg.role,"VCT"))break;
                            }
                            break;
                        }
                        if(stop(left.role,"PCT"))break;
                    }
                }
                if(r.equals("T")&&QUESTIONS.containsKey(value)) {
                    for(int i=end-1;i>=Math.max(0,end-6);i--) {
                        Token left=history.get(i);if(left.role.equals("V")){add(result,"VQ|"+left.text+"|"+QUESTIONS.get(value));break;}
                        if(stop(left.role,"CT"))break;
                    }
                    add(result,"Q|"+QUESTIONS.get(value)+"|"+tailRole(history,3));
                }
                if(r.equals("U"))for(int i=end-1;i>=Math.max(0,end-4);i--) {
                    Token left=history.get(i);if(left.role.equals("V")){add(result,"VQ|"+left.text+"|W");break;}
                    if(stop(left.role,"CT"))break;
                }
            }
            history.add(token);if(history.size()>6)history.remove(0);
        }
        return result;
    }
    static final class Evidence {
        final double raw;
        private final Set<String> positive,negative,kinds;
        Evidence(double raw,Set<String> positive,Set<String> negative,Set<String> kinds) {
            this.raw=raw;this.positive=positive;this.negative=negative;this.kinds=kinds;
        }
        boolean supportedOver(Evidence reference) {
            if(kinds.size()<2)return false;
            for(String key:positive)if(!reference.positive.contains(key))return true;return false;
        }
        boolean repairs(Evidence reference) {
            for(String key:reference.negative)if(!negative.contains(key))return true;return false;
        }
        boolean moreStructure(Evidence reference) {
            // Negation alone does not make one of two valid opposite meanings
            // more coherent. Compare the other distinct supported relations.
            return kinds.stream().filter(k->!k.equals("negation")).count()
                >reference.kinds.stream().filter(k->!k.equals("negation")).count();
        }
    }
    private static String kind(String name) {
        switch(name) {
            case "SV":case "SR":case "SVO":return "subject";
            case "NV":case "NVO":return "negation";
            case "VO":case "VH":return "object";
            case "CN":case "CH":return "classifier";
            case "AV":case "VQ":return "question";
            default:return "";
        }
    }
    Evidence evidence(String preceding,String text) {
        return evidence(preceding,text,weights);
    }
    private Evidence evidence(String preceding,String text,Map<String,Float> weights) {
        return evidence(features(preceding,text),weights);
    }
    private Evidence evidence(Map<String,Integer> features,Map<String,Float> weights) {
        double raw=0;Set<String> positive=new HashSet<>(),negative=new HashSet<>(),kinds=new HashSet<>();
        for(Map.Entry<String,Integer> e:features.entrySet()) {
            float weight=weights.getOrDefault(e.getKey(),0f);raw+=(double)weight*e.getValue();
            String key=e.getKey();
            if(weight>0&&key.charAt(0)!='G'&&key.charAt(0)!='B'&&key.charAt(0)!='Q') {
                String k=kind(key.substring(0,key.indexOf('|')));
                if(!k.isEmpty()){positive.add(key);kinds.add(k);}
            }
            // An unknown-word role is uncertainty, not adverse grammatical evidence.
            if(weight<-.1) {
                boolean unknown=key.startsWith("G|")&&key.indexOf('O',2)>=0
                    ||key.startsWith("B|")&&(key.charAt(2)=='O'||key.charAt(4)=='O')
                    ||key.startsWith("Q|")&&key.indexOf('O',4)>=0;
                if(!unknown)negative.add(key);
            }
        }
        return new Evidence(raw,positive,negative,kinds);
    }
    public double rawScore(String preceding,String text) {
        return dot(features(preceding,text),weights);
    }
    /** Cache only within one decode/context; head evidence reuses the exact same vectors. */
    double rawScore(String preceding,String text,Map<String,Map<String,Integer>> cache) {
        if(cache==null)return rawScore(preceding,text);
        return dot(cache.computeIfAbsent(text,k->features(preceding,k)),weights);
    }
    private static double dot(Map<String,Integer> vector,Map<String,Float> weights) {
        double score=0;
        for(Map.Entry<String,Integer> e:vector.entrySet())
            score+=(double)weights.getOrDefault(e.getKey(),0f)*e.getValue();
        return score;
    }
    public double correction(double raw,double reference) {return Math.max(0,strength*Math.max(-limit,Math.min(limit,raw-reference))-.1);}
    boolean aligned(){return aligned;}
    boolean expandedPool(){return expandedPool;}
    boolean headPromotion(){return strength>0&&headMargin>0;}
    private static String numerals(String text) {
        StringBuilder value=new StringBuilder();
        text.codePoints().filter(cp->"〇零一二三四五六七八九十百千萬億兩幾第壹貳參肆伍陸柒捌玖拾佰仟廿卅卌".indexOf(cp)>=0).forEach(value::appendCodePoint);
        return value.toString();
    }
    /** Promote within the established display; keep the former head as runner-up. */
    void promoteHead(String context,List<String> values,Map<String,Double> scores) {
        promoteHead(context,values,scores,null);
    }
    void promoteHead(String context,List<String> values,Map<String,Double> scores,Map<String,Map<String,Integer>> cache) {
        if(!headPromotion()||values.size()<2)return;
        Map<String,Float> selectedWeights=headWeights.isEmpty()?weights:headWeights;
        String first=values.get(0);Map<String,Integer> firstVector=vector(context,first,cache);
        double referenceRaw=dot(firstVector,selectedWeights);Evidence reference=null;
        String numbers=numerals(first);
        int chosen=-1;double best=Double.NEGATIVE_INFINITY;
        for(int i=1;i<Math.min(20,values.size());i++) {
            String value=values.get(i);
            // The bounded correction cannot close a larger base-score gap.
            if(scores.get(value)+(double)headStrength*headLimit<scores.get(first)+headMargin
                    ||!numbers.equals(numerals(value)))continue;
            Map<String,Integer> vector=vector(context,value,cache);
            double lift=dot(vector,selectedWeights)-referenceRaw;
            if(lift<headLift)continue;
            double score=scores.get(value)+headStrength*Math.max(-headLimit,Math.min(headLimit,lift));
            if(score<scores.get(first)+headMargin||score<=best)continue;
            if(reference==null)reference=evidence(firstVector,selectedWeights);
            Evidence candidate=evidence(vector,selectedWeights);
            if(lift>=headLift&&trustedPromotion(candidate,reference,lift)){chosen=i;best=score;}
        }
        if(chosen>0){String selected=values.remove(chosen);values.add(0,selected);}
    }
    private Map<String,Integer> vector(String context,String text,Map<String,Map<String,Integer>> cache) {
        return cache==null?features(context,text):cache.computeIfAbsent(text,k->features(context,k));
    }
    double alignedCorrection(double raw,double reference){return strength*Math.max(-limit,Math.min(limit,raw-reference));}
    boolean trustedPromotion(Evidence candidate,Evidence reference,double lift) {
        return lift>=.5&&candidate.supportedOver(reference)&&(candidate.repairs(reference)||candidate.moreStructure(reference));
    }
    public int entryCount(){return weights.size();}
}
