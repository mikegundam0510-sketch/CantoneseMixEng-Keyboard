package hk.cantonesemixeng.keyboard;

import java.util.*;
import java.util.function.Predicate;
import java.util.function.ToDoubleFunction;

/** Research policy: keep the first 18; compete for at most two final slots. */
public final class TailSupplement {
    private TailSupplement() {}

    public static List<String> apply(List<String> parent, List<String> generated,
            Predicate<String> legal, ToDoubleFunction<String> score, boolean personal) {
        if (parent.size() > 20 || new HashSet<>(parent).size() != parent.size())
            throw new IllegalArgumentException("Invalid parent display");
        List<String> original = new ArrayList<>(parent);
        if (personal || parent.size() < 5 || generated == null || Thread.currentThread().isInterrupted())
            return original;
        int pinned = Math.min(18, parent.size()), capacity = Math.min(2, 20 - pinned);
        List<String> pool = new ArrayList<>(parent.subList(pinned, parent.size()));
        Set<String> seen = new HashSet<>(parent);
        // Existing candidates precede proposals, so ties always preserve them.
        for (String text : generated.subList(0, Math.min(20, generated.size())))
            if (text != null && seen.add(text) && legal.test(text)) pool.add(text);
        Map<String, Double> scores = new HashMap<>();
        for (String text : pool) {
            if (Thread.currentThread().isInterrupted()) return original;
            double value = score.applyAsDouble(text);
            if (!Double.isFinite(value)) return original;
            scores.put(text, value);
        }
        pool.sort(Comparator.comparingDouble((String text) -> scores.get(text)).reversed());
        Set<String> chosen = new HashSet<>(pool.subList(0, Math.min(capacity, pool.size())));
        List<String> result = new ArrayList<>(parent.subList(0, pinned));
        // Preserve the relative order of every surviving native choice.
        for (String text : parent.subList(pinned, parent.size()))
            if (chosen.contains(text)) result.add(text);
        for (String text : pool)
            if (chosen.contains(text) && !parent.contains(text)) result.add(text);
        return result;
    }
}
