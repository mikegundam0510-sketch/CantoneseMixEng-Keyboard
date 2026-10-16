package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;

/** Tests observer checkpoint selection; never benchmark predictions. */
public final class CurrentSearchObserverCheck {
    private static QuickDecoder.SearchCheckpoint point(int at,boolean lost,String text,double margin) {
        QuickDecoder.SearchCheckpoint p=new QuickDecoder.SearchCheckpoint();
        p.position=at;p.lost=lost;p.positive=text;p.rank=49;
        p.rivals.add("錯誤");p.margins.add(margin);return p;
    }
    private static List<String> write()throws Exception {
        StringWriter s=new StringWriter();BufferedWriter w=new BufferedWriter(s);
        QuickDecoder.writePrefixPairs(w);w.flush();
        return s.toString().isEmpty()?Collections.emptyList():Arrays.asList(s.toString().split("\n"));
    }
    public static void main(String[] args)throws Exception {
        QuickDecoder.observedSource="train:fixture";QuickDecoder.observedContext="";
        QuickDecoder.observedCode="abcdefghi";QuickDecoder.observedGold="正確句子";
        QuickDecoder.checkpoints.clear();
        if(!write().isEmpty())throw new AssertionError("Empty observation emitted pairs");
        QuickDecoder.checkpoints.add(point(2,false,"正確",-100));
        QuickDecoder.checkpoints.add(point(6,true,"正確句",-20));
        QuickDecoder.checkpoints.add(point(4,true,"正確",-2));
        QuickDecoder.checkpoints.add(point(4,true,"正確",-3));
        List<String> rows=write();
        if(rows.size()!=2||!rows.get(0).split("\t",-1)[4].equals("4")||!rows.get(1).split("\t",-1)[4].equals("2"))
            throw new AssertionError("Earliest loss then maximum violation not selected");
        if(!rows.get(0).split("\t",-1)[8].equals("lost"))throw new AssertionError("Loss origin missing");
        if(QuickDecoder.checkpoints.size()!=4)throw new AssertionError("Writer mutated observations");
        QuickDecoder.checkpoints.clear();QuickDecoder.checkpoints.add(point(3,false,"正確",1));
        if(write().size()!=1)throw new AssertionError("Correct-prefix protection missing");
        System.out.println("empty/first-loss/max-violation/dedup/protection checks passed");
    }
}
