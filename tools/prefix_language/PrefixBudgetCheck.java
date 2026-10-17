package hk.cantonesemixeng.keyboard;

/** Force state exhaustion, rather than merely checking a small live cache. */
public final class PrefixBudgetCheck {
    public static void main(String[] args)throws Exception {
        SearchLanguageRanker model=PrefixReserveCheck.model(.5f);
        SearchLanguageRanker.Session session=model.session("");boolean exhausted=false;
        for(int i=0;i<128&&session.available();i++) {
            String text=new String(Character.toChars(0x4e00+i))+"甲".repeat(47);
            double score=session.score(text);
            if(Double.isNaN(score))exhausted=true;
            if(session.stateCount()>2048)throw new AssertionError("state overflow");
        }
        if(!exhausted||session.available()||session.stateCount()!=2048)throw new AssertionError("state ceiling not exercised");
        int count=session.queryCount();
        if(!Double.isNaN(session.score("你好"))||session.queryCount()!=count||session.stateCount()!=2048)
            throw new AssertionError("exhausted cache mutated");
        if(model.session("").stateCount()!=1)throw new AssertionError("decode state retained");
        System.out.println("state_exhaustion2048=true finite_fallback=true no_post_limit_growth=true fresh_session=true");
    }
}
