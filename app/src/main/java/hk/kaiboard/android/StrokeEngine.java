package hk.kaiboard.android;

import java.io.*;
import java.util.*;

/** Offline prefix lookup. h/s/p/n/z = horizontal/vertical/left-fall/dot/fold. */
final class StrokeEngine {
    private static final class Entry {
        final String word, code; final int weight;
        Entry(String w,String c,int n){word=w;code=c;weight=n;}
    }
    private final List<Entry> entries=new ArrayList<>();
    StrokeEngine(Reader source)throws IOException {
        try(BufferedReader in=new BufferedReader(source)) {
            String line;
            while((line=in.readLine())!=null) {
                if(line.startsWith("#"))continue;
                String[] f=line.split("\t");
                if(f.length!=3 || f[0].codePointCount(0,f[0].length())!=1 || !f[1].matches("[hspnz]{1,64}"))continue;
                try{entries.add(new Entry(f[0],f[1],Integer.parseInt(f[2])));}catch(NumberFormatException e){throw new IOException("Invalid stroke dictionary",e);}
            }
        }
        if(entries.isEmpty())throw new IOException("Empty stroke dictionary");
        entries.sort(Comparator.comparingInt((Entry e)->e.weight).reversed().thenComparingInt(e->e.code.length()).thenComparing(e->e.word));
    }
    List<String> lookup(String code,int limit) {
        if(limit<=0 || code.isEmpty() || !code.matches("[hspnz*]{1,64}"))return Collections.emptyList();
        LinkedHashSet<String> exact=new LinkedHashSet<>(),prefix=new LinkedHashSet<>();
        for(Entry e:entries) {
            if(e.code.length()<code.length())continue;
            boolean match=true;
            for(int i=0;i<code.length();i++)if(code.charAt(i)!='*'&&code.charAt(i)!=e.code.charAt(i)){match=false;break;}
            if(!match)continue;
            if(e.code.length()==code.length()){if(exact.size()<limit)exact.add(e.word);}
            else if(prefix.size()<limit)prefix.add(e.word);
        }
        for(String word:prefix){if(exact.size()>=limit)break;exact.add(word);}
        return new ArrayList<>(exact);
    }
    static String display(String code) {
        StringBuilder text=new StringBuilder();String keys="hspnz*",marks="一丨丿丶乙＊";
        for(int i=0;i<code.length();i++){int at=keys.indexOf(code.charAt(i));if(at>=0)text.append(marks.charAt(at));}
        return text.toString();
    }
}
