package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;

public class ClauseRelationsTest {
    @Test public void literalObjectRelationsDistinguishNaturalAndClashingChoices() {
        assertTrue(ClauseRelations.score("你", "搭巴士")>ClauseRelations.score("你", "飲巴士"));
        assertTrue(ClauseRelations.score("你", "飲奶茶")>ClauseRelations.score("你", "搭奶茶"));
        assertEquals(4,ClauseRelations.score("你", "覆返個訊息"),0);
        assertEquals(4,ClauseRelations.score("我", "確認份文件"),0);
    }
    @Test public void aBareOverlappingFragmentDoesNotGetAClauseBonus() {
        assertEquals(0,ClauseRelations.score("", "日借款錯啊"),0);
        assertEquals(2.5,ClauseRelations.score("我", "借咗款"),0);
    }
    @Test public void classifiersSupportReusableNounsWithoutInventingHardGrammarRules() {
        assertTrue(ClauseRelations.score("", "份文件") > ClauseRelations.score("", "修文件"));
        assertEquals(1.5,ClauseRelations.score("", "張訂單"),0);
        assertEquals(1.5,ClauseRelations.score("", "封信"),0);
        assertEquals(0,ClauseRelations.score("", "個信心"),0);
        assertEquals(4,ClauseRelations.score("你收到", "件貨"),0);
        assertEquals(0,ClauseRelations.score("", "份陌生人名"),0);
        assertEquals(0,ClauseRelations.score("檢查文件，份", "陳氏"),0);
    }
    @Test public void alternativesSupportCompatibleObjectsAndResetAtBoundaries() {
        assertEquals(2,ClauseRelations.score("地鐵定", "巴士"),0);
        assertEquals(2,ClauseRelations.score("送貨定", "自取"),0);
        assertEquals(0,ClauseRelations.score("地鐵，定", "巴士"),0);
        assertEquals(0,ClauseRelations.score("地鐵定", "奶茶"),0);
        assertEquals(2.5,ClauseRelations.score("你訂咗", "餐廳"),0);
        assertEquals(2.5,ClauseRelations.score("你去", "房間"),0);
        assertEquals(2.5,ClauseRelations.score("你返", "酒店"),0);
        assertEquals(0,ClauseRelations.score("你訂咗", "錢"),0);
    }
    @Test public void classifierAndAlternativeEvidenceIsIndependentOfLatticeTokenBoundaries() {
        for(String text:new String[]{"你收到件貨未", "幫我查下張訂單", "你搭地鐵定巴士", "你想送貨定自取", "你訂咗餐廳未"}) {
            double score=ClauseRelations.score("",text);
            for(int cut=0;cut<=text.length();cut++)
                assertEquals(text,score,ClauseRelations.score("",text.substring(0,cut))
                    +ClauseRelations.score(text.substring(0,cut),text.substring(cut)),0);
        }
    }
    @Test public void scoringIsIndependentOfTokenBoundaries() {
        String text="你覆返個訊息畀同事未";
        double score=ClauseRelations.score("",text);
        for(int cut=0;cut<=text.length();cut++)
            assertEquals(score,ClauseRelations.score("",text.substring(0,cut))
                +ClauseRelations.score(text.substring(0,cut),text.substring(cut)),0);
        assertEquals(2.5,ClauseRelations.score("", "你飲奶茶"),0);
        assertEquals(2.5,ClauseRelations.score("", "你返屋企"),0);
        assertEquals(2.5,ClauseRelations.score("", "你去車站"),0);
        assertEquals(0,ClauseRelations.score("", "你等車站"),0);
    }
    @Test public void punctuationAndUnknownObjectsStayNeutral() {
        assertEquals(0,ClauseRelations.score("你飲", "，巴士"),0);
        assertEquals(0,ClauseRelations.score("你飲", "ABC巴士"),0);
        assertEquals(0,ClauseRelations.score("你飲", "陳氏"),0);
        assertEquals(0,ClauseRelations.score("", "某個罕見人名"),0);
    }
}
