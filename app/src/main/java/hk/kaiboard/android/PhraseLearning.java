package hk.kaiboard.android;

import java.util.*;
import java.util.function.Predicate;

/** Only bounded, bundled words are persisted; editor sentences never become keys. */
public final class PhraseLearning {
    private PhraseLearning() {}
    public static String key(String word) { return "W:" + word; }

    public static List<String> selectedWords(String context, InputCandidate candidate,
            Predicate<String> known, boolean enabled, boolean protectedField) {
        if (!enabled || protectedField) return Collections.emptyList();
        LinkedHashSet<String> result = new LinkedHashSet<>();
        // A cursor context is transient; only known words overlapping this explicit
        // Chinese selection can be saved. English, translations and punctuation
        // break the span. A prediction tail is an explicit Chinese selection too.
        String history = tail(context);
        for (InputCandidate.Segment segment : candidate.segments) {
            if (segment.english || segment.translated || !QuickDecoder.hanText(segment.text)) {
                history = ""; continue;
            }
            for (int cp : segment.text.codePoints().toArray()) {
                history = tail(history + new String(Character.toChars(cp)));
                int length = history.codePointCount(0, history.length());
                for (int size = 2; size <= length; size++) {
                    String word = history.substring(history.offsetByCodePoints(0, length - size));
                    if (known.test(word)) result.add(word);
                }
            }
        }
        return new ArrayList<>(result);
    }

    private static String tail(String text) {
        int at = text.length(), count = 0;
        while (at > 0 && count < 8) {
            int cp = text.codePointBefore(at);
            if (!OfflineLanguageModel.han(cp)) break;
            at -= Character.charCount(cp); count++;
        }
        return text.substring(at);
    }
}
