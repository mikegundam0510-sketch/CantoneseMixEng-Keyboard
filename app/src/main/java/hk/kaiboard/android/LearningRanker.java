package hk.kaiboard.android;

import java.util.*;
import java.util.function.ToIntFunction;

public final class LearningRanker {
    private LearningRanker() {}
    public static boolean isLearnable(String value) {
        return value.codePointCount(0, value.length()) == 1 &&
            Character.UnicodeScript.of(value.codePointAt(0)) == Character.UnicodeScript.HAN;
    }
    public static List<String> rank(List<String> original, ToIntFunction<String> frequency) {
        List<String> ranked = new ArrayList<>(original);
        // Stable sorting keeps the original dictionary order when usage counts tie.
        ranked.sort(Comparator.comparingInt((String word) -> isLearnable(word) ? frequency.applyAsInt(word) : 0).reversed());
        return ranked;
    }
    public static String key(String code, boolean quick, boolean cangjie, String word) {
        return (quick ? "Q" : "-") + (cangjie ? "C" : "-") + ":" + code.toLowerCase(Locale.ROOT) + ":" + word;
    }
}
