package hk.kaiboard.android;

import java.util.*;
import java.util.function.Predicate;

/** Explicit replacement feedback; only existing character/known-word keys persist. */
final class CorrectionLearning {
    private CorrectionLearning() {}

    static int adjust(int learned, Object stored, long now) {
        double rejected = RecentLearning.recent(stored instanceof String ? (String) stored : null, now);
        int penalty = (int) Math.round(8 * Math.min(8, rejected));
        // A correction temporarily lowers confidence in a large legacy count.
        return penalty == 0 ? learned : Math.min(20, learned) - penalty;
    }

    static String update(String stored, long now, double delta) {
        double count = Math.max(0, Math.min(8, RecentLearning.recent(stored, now) + delta));
        return count == 0 ? null : Math.max(0, now) + ":" + count;
    }

    static Set<String> rejectedKeys(InputCandidate old, InputCandidate replacement,
            Predicate<String> known, boolean quick, boolean cangjie, boolean enabled, boolean protectedField) {
        Set<String> result = new LinkedHashSet<>();
        if (!enabled || protectedField || old == null || replacement == null || old.source.isEmpty()
                || !old.source.equals(replacement.source) || old.text.equals(replacement.text)
                || old.englishOnly() || replacement.englishOnly()
                || replacement.segments.stream().allMatch(s -> s.translated)) return result;
        Map<Integer, InputCandidate.Segment> replacements = new HashMap<>();
        int offset = 0;
        for (InputCandidate.Segment segment : replacement.segments) {
            replacements.put(offset, segment); offset += segment.code.length();
        }
        offset = 0;
        for (InputCandidate.Segment segment : old.segments) {
            InputCandidate.Segment selected = replacements.get(offset);
            if (selected != null && !segment.english && !segment.translated && !selected.english && !selected.translated
                    && !segment.code.isEmpty() && segment.code.equals(selected.code)
                    && !segment.text.equals(selected.text) && LearningRanker.isLearnable(segment.text))
                result.add(LearningRanker.key(segment.code, quick, cangjie, segment.text));
            offset += segment.code.length();
        }
        Set<String> kept = new HashSet<>(PhraseLearning.selectedWords("", replacement, known, true, false));
        for (String word : PhraseLearning.selectedWords("", old, known, true, false))
            if (!kept.contains(word)) result.add(PhraseLearning.key(word));
        return result;
    }
}
