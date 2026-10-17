package hk.cantonesemixeng.keyboard;
import java.io.*;import java.nio.file.*;import java.util.*;
public final class PrefixSessionCheck {
    public static void main(String[] args)throws Exception {
        Path p=Path.of(args[0]);
        SearchLanguageRanker search=SearchLanguageRanker.load(Files.newInputStream(p));
        SentenceLanguageRanker reference=SentenceLanguageRanker.load(Files.newInputStream(p));
        String[] contexts={"","我今日","前文，收工之後","一二三四五六七八九十十一十二十三十四十五","𠮶𠮷"};
        String[] texts={"你","你好","你今日食咗咩","你交咗功課畀老細未","𠮶𠮷","一".repeat(48)};
        int checked=0;
        for(String context:contexts) {
            SearchLanguageRanker.Session session=search.session(context);
            for(String text:texts) {
                double actual=session.score(text),expected=reference.score(context,text);
                if(Math.abs(actual-expected)>1e-6)throw new AssertionError(actual+" "+expected);
                for(int n=1;n<=text.codePointCount(0,text.length());n++) {
                    String prefix=text.substring(0,text.offsetByCodePoints(0,n));
                    // Separate sessions keep this check independent of the query budget.
                    actual=search.session(context).score(prefix);expected=reference.score(context,prefix);
                    if(Math.abs(actual-expected)>1e-6)throw new AssertionError("prefix mismatch");checked++;
                }
            }
            if(session.stateCount()>2048)throw new AssertionError("state bound");
        }
        SearchLanguageRanker.Session bounded=search.session("");
        for(int i=0;i<128;i++)if(!Double.isFinite(bounded.score("你好")))throw new AssertionError("early exhaustion");
        if(bounded.available()||!Double.isNaN(bounded.score("你好"))||bounded.queryCount()!=128)throw new AssertionError("query bound");
        SearchLanguageRanker.Session fresh=search.session("");
        if(fresh.queryCount()!=0||fresh.stateCount()!=1)throw new AssertionError("state leaked across decode");
        System.out.println("prefix_scores="+checked+" exact_reference=true query_budget128=true state_bound2048=true per_decode_isolation=true");
    }
}
