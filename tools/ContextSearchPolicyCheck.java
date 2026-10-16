package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/** Controlled counterexamples test search reachability, not corpus accuracy. */
public final class ContextSearchPolicyCheck {
    private static byte[] encoded(ByteArrayOutputStream raw) {
        return Base64.getEncoder().encode(raw.toByteArray());
    }
    private static OfflineLanguageModel model() throws Exception {
        ByteArrayOutputStream raw=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(raw))) {
            out.writeInt(0x4B4C4D32);out.writeInt(5);out.writeInt(1);out.writeFloat(.000001f);
            out.writeLong(OfflineLanguageModel.hash(new int[]{'甲'},0,1));out.writeFloat(.01f);out.writeFloat(1);
        }
        return OfflineLanguageModel.load(new ByteArrayInputStream(encoded(raw)));
    }
    private static SentenceRanker sentences() throws Exception {
        ByteArrayOutputStream raw=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(raw))) {
            out.writeInt(0x53524b32);out.writeInt(2);out.writeInt(2);out.writeFloat(1);out.writeFloat(3);
            for(String feature:new String[]{"W|你交","W|我交"}) {
                byte[] key=feature.getBytes(java.nio.charset.StandardCharsets.UTF_8);
                out.writeShort(key.length);out.write(key);out.writeFloat(1.5f);
            }
        }
        return SentenceRanker.load(new ByteArrayInputStream(encoded(raw)));
    }
    private static QuickDecoder decoder(boolean withModel,boolean withSentences) throws Exception {
        StringBuilder roots=new StringBuilder("...\n甲\taa\n");
        for(int cp=0x7000;cp<0x7400;cp++)roots.appendCodePoint(cp).append("\tzz\n");
        DictionaryEngine d=new DictionaryEngine(new StringReader(roots.toString()),new StringReader(""),new StringReader("甲\t1000\n"));
        return new QuickDecoder(d,new StringReader(""),null,null,withModel?model():null,
            null,null,null,null,0,withSentences?sentences():null);
    }
    private static Class<?> pathClass;
    private static Constructor<?> path;
    private static Field text;
    private static Object path(String value,double score) throws Exception {return path.newInstance(value,score);}
    private static Set<String> texts(List<?> paths) throws Exception {
        Set<String> result=new LinkedHashSet<>();for(Object p:paths)result.add((String)text.get(p));return result;
    }
    private static void check(boolean value,String reason) {if(!value)throw new AssertionError(reason);}
    public static void main(String[] args) throws Exception {
        int heads=Integer.parseInt(args[0]);boolean complete=Boolean.parseBoolean(args[1]);
        pathClass=Class.forName("hk.cantonesemixeng.keyboard.QuickDecoder$Path");
        path=pathClass.getDeclaredConstructor(String.class,double.class);path.setAccessible(true);
        text=pathClass.getDeclaredField("text");text.setAccessible(true);
        Method distinct=QuickDecoder.class.getDeclaredMethod("distinctPaths",List.class);distinct.setAccessible(true);
        List<Object> paths=new ArrayList<>();
        for(int i=0;i<60;i++)paths.add(path(new String(Character.toChars(0x5000+i))+"香港返工",-i*.001));
        String wanted="乙搭車回家";paths.add(path(wanted,-.060));
        Set<String> kept=texts((List<?>)distinct.invoke(decoder(true,false),new ArrayList<>(paths)));
        check(kept.size()==48,"Fixed beam bound");check(kept.contains(wanted)==(heads>0),"Distinct history must be reachable only in diversity arm");
        for(int i=0;i<(heads==0?48:heads);i++)check(kept.contains((String)text.get(paths.get(i))),"Protected ranked prefix lost");
        check(!texts((List<?>)distinct.invoke(decoder(false,false),new ArrayList<>(paths))).contains(wanted),"Model-free fallback changed");
        if(heads>0) {
            Method tail=QuickDecoder.class.getDeclaredMethod("searchHistory",String.class);tail.setAccessible(true);
            check("𠀀𠀁香港".equals(tail.invoke(null,"甲𠀀𠀁香港")),"History split a supplementary character");
        }
        List<Object> completed=new ArrayList<>();
        for(int i=0;i<400;i++) {
            String value=i==168?"你交":i==300?"我交":"一"+new String(Character.toChars(0x6000+i));
            completed.add(path(value,-i*.001));
        }
        Method finish=complete?QuickDecoder.class.getDeclaredMethod("pruneFinal",List.class,String.class)
            :QuickDecoder.class.getDeclaredMethod("pruneFinal",List.class);finish.setAccessible(true);
        List<?> retained=(List<?>)(complete?finish.invoke(decoder(true,true),completed,""):finish.invoke(decoder(true,true),completed));
        Set<String> values=texts(retained);
        check(values.size()==96,"Completed-pool bound");
        check(values.contains("你交")==complete,"Existing sentence evidence must reach the pre-rerank cutoff");
        check(!values.contains("我交"),"Out-of-window strong path was scanned beyond the2*pool bound");
        System.out.printf("controlled_checks=7 prefix_heads=%d completed_policy=%s%n",heads,complete);
    }
}
