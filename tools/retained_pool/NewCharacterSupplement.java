package hk.cantonesemixeng.keyboard;

import java.util.*;

/** Expanded proposals may supplement the deployed pool only through new letters. */
public final class NewCharacterSupplement {
    private NewCharacterSupplement() {}

    public static List<String> filter(List<String> proposals, Set<Integer> additions) {
        List<String> result = new ArrayList<>();
        if (proposals == null || additions == null || additions.isEmpty()) return result;
        // The ordinary provider offers at most twenty. Do not search farther
        // after filtering, which would silently change the frozen generator.
        for (String text : proposals.subList(0, Math.min(20, proposals.size()))) {
            if (text == null) continue;
            if (text.codePoints().anyMatch(additions::contains)) result.add(text);
        }
        return result;
    }
}
