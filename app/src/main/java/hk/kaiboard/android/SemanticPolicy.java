package hk.kaiboard.android;

import java.util.*;

/** Pure memory/latency policy. Basic exact input never depends on the neural model. */
public final class SemanticPolicy {
    public static final long MIB = 1024L * 1024;
    public static final class Budget {
        public final int candidates, context, threads, milliseconds;
        Budget(int candidates, int context, int threads, int milliseconds) {
            this.candidates=candidates; this.context=context; this.threads=threads; this.milliseconds=milliseconds;
        }
    }
    public static Budget budget(long total, long available, boolean lowMemory) {
        if (lowMemory || total < 2500 * MIB || available < 1000 * MIB) return null;
        if (total >= 7500 * MIB && available >= 2000 * MIB) return new Budget(8,128,4,1800);
        return new Budget(4,96,2,1400);
    }
    /** Promote one existing exact candidate only; stable ordering of all others is preserved. */
    public static List<String> promote(List<String> original, List<String> eligible, float[] logits) {
        if (logits == null || logits.length != eligible.size() || eligible.size() < 2) return original;
        int best = 0;
        for (int i=0;i<logits.length;i++) {
            if (!Float.isFinite(logits[i])) return original;
            if (logits[i]>logits[best]) best=i;
        }
        if (best == 0 || logits[best]-logits[0] < 1.0 || !original.contains(eligible.get(best))) return original;
        List<String> result = new ArrayList<>(original);
        String chosen=eligible.get(best); result.remove(chosen); result.add(0,chosen);
        return result;
    }
}
