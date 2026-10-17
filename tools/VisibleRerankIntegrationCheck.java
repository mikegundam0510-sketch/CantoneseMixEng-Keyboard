package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;
import java.util.zip.GZIPOutputStream;

/** A controlled real decode proves the optional pretrained language scorer is connected. */
public final class VisibleRerankIntegrationCheck {
    private interface Writer {void write(DataOutputStream out)throws Exception;}
    private static InputStream model(Writer writer)throws Exception {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(bytes))){writer.write(out);}
        return new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray()));
    }
    public static void main(String[] args)throws Exception {
        StringBuilder roots=new StringBuilder("...\n丙\taa\n甲\taa\n乙\tbb\n");
        for(int cp=0x7000;cp<0x7400;cp++)roots.appendCodePoint(cp).append("\tzz\n");
        DictionaryEngine d=new DictionaryEngine(new StringReader(roots.toString()),new StringReader(""),new StringReader("丙\t1000\n甲\t1000\n乙\t1000\n"));
        TreeMap<Long,Float> probs=new TreeMap<>();
        for(int cp:new int[]{'丙','甲','乙'})probs.put(OfflineLanguageModel.hash(new int[]{cp},0,1),cp=='甲'?.009f:.01f);
        OfflineLanguageModel lm=OfflineLanguageModel.load(model(out->{
            out.writeInt(0x4b4c4d32);out.writeInt(5);out.writeInt(probs.size());out.writeFloat(.000001f);
            for(Map.Entry<Long,Float> e:probs.entrySet()){out.writeLong(e.getKey());out.writeFloat(e.getValue());out.writeFloat(1);}
        }));
        SentenceRanker sr=SentenceRanker.load(model(out->{
            out.writeInt(0x53524b32);out.writeInt(1);out.writeInt(2);out.writeFloat(1);out.writeFloat(3);
            byte[] key="W|中文".getBytes(java.nio.charset.StandardCharsets.UTF_8);out.writeShort(key.length);out.write(key);out.writeFloat(.1f);
        }));
        SentenceLanguageRanker nn=SentenceLanguageRanker.load(model(out->{
            out.writeInt(0x534c4d31);out.writeInt(1);out.writeInt(1);out.writeInt(6);
            out.writeInt(12);out.writeInt(48);out.writeFloat(2);out.writeFloat(.5f);
            for(int cp:new int[]{'丙','乙','甲'})out.writeInt(cp);
            for(int child:new int[]{1,2,-2,-4,-5,-6})out.writeInt(child);
            for(int i=0;i<6;i++)out.writeFloat((float)Math.log(.25));
            for(int i=0;i<18;i++)out.writeFloat(0);
            for(float value:new float[]{(float)Math.log(4),0,(float)Math.log(9)})out.writeFloat(value);
        }));
        QuickDecoder before=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,sr,null,null,null);
        QuickDecoder after=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,sr,null,null,nn);
        List<String> a=before.decode("aabb",(c,w)->0),b=after.decode("aabb",(c,w)->0);
        if(!a.get(0).equals("丙乙")||!b.get(0).equals("甲乙"))throw new AssertionError("Pretrained language model is not connected: "+a+" / "+b);
        for(String s:b)if(d.matchQuickCodes("aabb",s).isEmpty())throw new AssertionError("Inexact pretrained candidate");
        if(!new HashSet<>(a).equals(new HashSet<>(b))||a.size()!=b.size())throw new AssertionError("Display changed");
        if(!after.decodeBaseline("aabb",(c,w)->0,"",null).equals(a))throw new AssertionError("Baseline bypass changed");
        ToIntBiFunction<String,String> familiar=(c,w)->5;
        if(!after.decode("aabb",familiar).get(0).equals("甲乙"))
            throw new AssertionError("Familiar characters incorrectly disable new phrase ranking");
        InputCandidate preferred=InputCandidate.chinese(d,"aabb","丙乙");
        Set<String> keys=ContextLearning.selectedKeys("",preferred,true,false);
        if(keys.isEmpty())throw new AssertionError("Missing contextual fixture keys");
        ContextLearning.Preferences positive=new ContextLearning.Preferences(keys,k->5);
        if(!before.decode("aabb",(c,w)->0,"",positive).equals(after.decode("aabb",(c,w)->0,"",positive)))
            throw new AssertionError("Confirmed contextual choices changed");
        Set<String> rejected=ContextLearning.selectedKeys("",InputCandidate.chinese(d,"aabb","甲乙"),true,false);
        ContextLearning.Preferences negative=new ContextLearning.Preferences(rejected,k->-5);
        if(!before.decode("aabb",(c,w)->0,"",negative).equals(after.decode("aabb",(c,w)->0,"",negative)))
            throw new AssertionError("Contextual rejections changed");
        EnglishEngine english=new EnglishEngine(new StringReader("hello\nCAN\n"));
        CandidateEngine oldEngine=new CandidateEngine(d,before,english),newEngine=new CandidateEngine(d,after,english);
        List<InputCandidate> oldMixed=oldEngine.mixed("aabbhello","",Collections.emptyList(),(c,w)->0);
        List<InputCandidate> newMixed=newEngine.mixed("aabbhello","",Collections.emptyList(),(c,w)->0);
        if(oldMixed.isEmpty()||oldMixed.size()!=newMixed.size())throw new AssertionError("Mixed fixture absent or lost");
        for(int i=0;i<oldMixed.size();i++)if(!oldMixed.get(i).text.equals(newMixed.get(i).text))
            throw new AssertionError("Mixed source choices changed");
        EnglishChineseEngine meanings=new EnglishChineseEngine(new StringReader("can\t可以\t1\n"));
        List<InputCandidate> oldSuffix=meanings.mixedSuffix("aabbCAN","",oldEngine,(c,w)->0);
        List<InputCandidate> newSuffix=meanings.mixedSuffix("aabbCAN","",newEngine,(c,w)->0);
        if(oldSuffix.isEmpty()||oldSuffix.size()!=newSuffix.size())throw new AssertionError("Translated fixture absent or lost");
        for(int i=0;i<oldSuffix.size();i++)if(!oldSuffix.get(i).text.equals(newSuffix.get(i).text))
            throw new AssertionError("Translation source choices changed");
        System.out.println("cold_head=甲乙 original_set_preserved=true positive_and_negative_context=true familiar_characters_active=true mixed_and_translation_unchanged=true");
    }
}
