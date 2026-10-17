package hk.cantonesemixeng.keyboard;
import java.io.*;import java.lang.reflect.*;import java.util.*;import java.util.zip.GZIPOutputStream;

/** Controlled live prune: retain the old48, rescue a lawful extra history. */
public final class PrefixReserveCheck {
    static SearchLanguageRanker model(float strength)throws Exception {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(DataOutputStream out=new DataOutputStream(new GZIPOutputStream(bytes))) {
            out.writeInt(0x534c4d31);out.writeInt(1);out.writeInt(1);out.writeInt(6);
            out.writeInt(12);out.writeInt(48);out.writeFloat(2);out.writeFloat(strength);
            for(int cp:new int[]{'丙','乙','甲'})out.writeInt(cp);
            for(int child:new int[]{1,2,-2,-4,-5,-6})out.writeInt(child);
            for(int i=0;i<6;i++)out.writeFloat((float)Math.log(.25));
            for(int i=0;i<18;i++)out.writeFloat(0);
            for(float value:new float[]{(float)Math.log(4),0,(float)Math.log(9)})out.writeFloat(value);
        }
        return SearchLanguageRanker.load(new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray())));
    }
    static List<String> prune(SearchLanguageRanker model,boolean enabled)throws Exception {
        StringBuilder roots=new StringBuilder("...\n丙\taa\n乙\taa\n甲\taa\n");
        for(int cp=0x7000;cp<0x7400;cp++)roots.appendCodePoint(cp).append("\tzz\n");
        DictionaryEngine d=new DictionaryEngine(new StringReader(roots.toString()),new StringReader(""),new StringReader(""));
        QuickDecoder q=new QuickDecoder(d,new StringReader(""),null,null,null,null,null,null,null,1.5,null,null,null,null,model);
        Class<?> path=Class.forName(QuickDecoder.class.getName()+"$Path");
        Constructor<?> make=path.getDeclaredConstructor(String.class,double.class);make.setAccessible(true);
        List<Object> input=new ArrayList<>();
        for(int n=0;n<48;n++) {
            StringBuilder text=new StringBuilder();for(int bit=0;bit<6;bit++)text.append((n&(1<<bit))==0?'丙':'乙');
            input.add(make.newInstance(text.toString(),0.));
        }
        input.add(make.newInstance("甲甲甲甲甲甲",-.01));
        Class<?> cache=Class.forName(QuickDecoder.class.getName()+"$ModelScoreCache");
        Constructor<?> c=cache.getDeclaredConstructor(QuickDecoder.class,String.class,boolean.class);c.setAccessible(true);
        Method prune=QuickDecoder.class.getDeclaredMethod("prune",List.class,String.class,List.class,cache);prune.setAccessible(true);
        List<?> result=(List<?>)prune.invoke(q,input,"",Collections.emptyList(),c.newInstance(q,"",enabled));
        Field text=path.getDeclaredField("text");text.setAccessible(true);List<String> values=new ArrayList<>();
        for(Object p:result)values.add((String)text.get(p));return values;
    }
    public static void main(String[] args)throws Exception {
        List<String> original=prune(null,true),updated=prune(model(.5f),true);
        if(original.size()!=48||updated.size()!=49||!updated.subList(0,48).equals(original)
                ||!updated.get(48).equals("甲甲甲甲甲甲"))throw new AssertionError("reserve hook absent");
        if(!prune(model(0),true).equals(original)||!prune(model(.5f),false).equals(original))throw new AssertionError("fallback/bypass");
        System.out.println("live_prune_rescue=true original48_preserved=true neutral_and_baseline_bypass=true");
    }
}
