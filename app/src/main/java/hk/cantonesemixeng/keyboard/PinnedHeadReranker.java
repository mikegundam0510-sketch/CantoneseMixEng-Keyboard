package hk.cantonesemixeng.keyboard;

import java.util.*;
import java.util.function.ToDoubleFunction;

/** Preserve the established first choice and rerank only its existing tail. */
public final class PinnedHeadReranker {
    private PinnedHeadReranker() {}
    public static List<String> rerank(List<String> visible,Map<String,Double> scores,
            ToDoubleFunction<String> evidence) {
        List<String> ranked=VisibleCandidateReranker.rerank(visible,scores,evidence);
        if(!visible.isEmpty()) {
            String first=visible.get(0);
            ranked.remove(first);ranked.add(0,first);
        }
        return ranked;
    }
}
