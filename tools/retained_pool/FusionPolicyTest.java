package hk.cantonesemixeng.keyboard;

import java.util.*;

/** Protect old generated choices as well as native choices, including short lists. */
public final class FusionPolicyTest {
    private static void check(boolean condition) {
        if (!condition) throw new AssertionError();
    }

    public static void main(String[] args) {
        Set<Integer> additions = new HashSet<>(Arrays.asList((int)'芯', 0x20B79));
        List<String> proposals = Arrays.asList("舊字", "芯片", "又有芯", "𠭹字", null);
        check(NewCharacterSupplement.filter(proposals, additions)
            .equals(Arrays.asList("芯片", "又有芯", "𠭹字")));
        check(NewCharacterSupplement.filter(null, additions).isEmpty());
        check(NewCharacterSupplement.filter(proposals, Collections.emptySet()).isEmpty());
        List<String> tooMany = new ArrayList<>(Collections.nCopies(20, "舊字"));
        tooMany.add("芯片");
        check(NewCharacterSupplement.filter(tooMany, additions).isEmpty());
        List<String> oldDisplay = new ArrayList<>();
        for (int i=0; i<16; i++) oldDisplay.add("native"+i);
        oldDisplay.add("oldGeneratedA"); oldDisplay.add("oldGeneratedB");
        List<String> filtered = NewCharacterSupplement.filter(proposals, additions);
        List<String> result = TailSupplement.apply(oldDisplay, filtered, t -> true, t -> 100, false);
        check(result.subList(0,18).equals(oldDisplay) && result.size()==20);
        List<String> full = new ArrayList<>(oldDisplay);
        full.add("oldGeneratedC"); full.add("oldGeneratedD");
        result = TailSupplement.apply(full, filtered, t -> true,
            t -> t.startsWith("oldGenerated") ? 200 : 100, false);
        check(result.equals(full)); // The previous generator's tail stays eligible.
        result = TailSupplement.apply(full, filtered, t -> true, t -> 100, false);
        check(result.equals(full)); // Ties favour the complete deployed pool.
        check(TailSupplement.apply(full, filtered, t -> true, t -> 1000, true).equals(full));
        System.out.println("fusion-policy checks=8 passed; nonBMP=true deployed-generated-prefix=true old-tail-eligible=true");
    }
}
