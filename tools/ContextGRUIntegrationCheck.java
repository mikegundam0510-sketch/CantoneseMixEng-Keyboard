package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/** A controlled real decode proves the optional recurrent scorer is connected. */
public final class ContextGRUIntegrationCheck {
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
        ContextSentenceRanker nn=ContextSentenceRanker.load(model(out->{
            out.writeInt(0x47525531);out.writeInt(1);out.writeInt(1);out.writeInt(6);out.writeInt(12);out.writeInt(48);out.writeFloat(2);out.writeFloat(1);
            for(int cp:new int[]{'丙','乙','甲'})out.writeInt(cp);
            for(float value:new float[]{0,0,0,-1,0,1, 0,0,1, 0,0,0, 0,0,0, 4,0})out.writeFloat(value);
        }));
        QuickDecoder before=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,sr,null,null,null);
        QuickDecoder after=new QuickDecoder(d,new StringReader(""),null,null,lm,null,null,null,null,sr,null,null,nn);
        List<String> a=before.decode("aabb",(c,w)->0),b=after.decode("aabb",(c,w)->0);
        if(!a.get(0).equals("丙乙")||!b.get(0).equals("甲乙"))throw new AssertionError("Optional recurrent model is not connected: "+a+" / "+b);
        for(String s:b)if(d.matchQuickCodes("aabb",s).isEmpty())throw new AssertionError("Inexact recurrent candidate");
        System.out.println("null_head=丙乙 enabled_head=甲乙 exact_code=true");
    }
}
