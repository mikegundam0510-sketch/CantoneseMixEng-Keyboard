package hk.cantonesemixeng.keyboard;

import java.util.*;
import java.util.function.ToDoubleFunction;

/** Regression guards for displacement, fallback, personal protection and ties. */
public final class PolicyTest {
    private static void check(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        List<String> parent = new ArrayList<>();
        for (int i = 0; i < 20; i++) parent.add("native" + i);
        ToDoubleFunction<String> score = text -> text.startsWith("new") ? 100 : 0;
        List<String> result = TailSupplement.apply(parent, Arrays.asList("newA", "newB", "newC"), t -> true, score, false);
        check(result.subList(0,18).equals(parent.subList(0,18)) && result.size()==20);
        check(result.subList(18,20).equals(Arrays.asList("newA","newB")));
        result = TailSupplement.apply(parent, Arrays.asList("newA", "newB"), t -> true, t -> 0, false);
        check(result.equals(parent));
        result = TailSupplement.apply(parent, Arrays.asList("native0", "newA", "newA", "bad"),
            t -> !t.equals("bad"), t -> t.equals("native19") ? 2 : t.equals("newA") ? 1 : 0, false);
        check(result.subList(18,20).equals(Arrays.asList("native19","newA")));
        check(TailSupplement.apply(parent, List.of("newA"), t -> true, t -> Double.NaN, false).equals(parent));
        check(TailSupplement.apply(parent, List.of("newA"), t -> true, score, true).equals(parent));
        check(TailSupplement.apply(parent, null, t -> true, score, false).equals(parent));
        check(TailSupplement.apply(parent.subList(0,4), List.of("newA"), t -> true, score, false).equals(parent.subList(0,4)));
        result = TailSupplement.apply(parent.subList(0,9), List.of("newA","newB","newC"), t -> true, score, false);
        check(result.size()==11 && result.subList(0,9).equals(parent.subList(0,9)));
        List<String> many = new ArrayList<>();
        for (int i=0;i<20;i++) many.add("bad"+i);
        many.add("newA");
        check(TailSupplement.apply(parent, many, t -> t.startsWith("new"), score, false).equals(parent));
        Thread.currentThread().interrupt();
        check(TailSupplement.apply(parent, List.of("newA"), t -> true, score, false).equals(parent));
        Thread.interrupted();
        check(parent.get(19).equals("native19"));
        System.out.println("policy_checks=11 passed=true");
    }
}
