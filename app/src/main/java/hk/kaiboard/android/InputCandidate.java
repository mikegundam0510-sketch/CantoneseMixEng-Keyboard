package hk.kaiboard.android;

import java.util.*;

/** Immutable source-to-text mapping; Chinese characters and English words remain editable separately. */
public final class InputCandidate {
    public static final class Segment {
        public final String code, text;
        public final boolean english;
        public Segment(String code, String text, boolean english) {
            this.code = code; this.text = text; this.english = english;
        }
    }
    public final String source, text;
    public final List<Segment> segments;
    public final boolean corrected;
    public InputCandidate(String source, List<Segment> segments, boolean corrected) {
        this.source = source;
        this.segments = Collections.unmodifiableList(new ArrayList<>(segments));
        StringBuilder value = new StringBuilder();
        for (Segment segment : segments) value.append(segment.text);
        text = value.toString(); this.corrected = corrected;
    }
    public static InputCandidate english(String source, String text) {
        return new InputCandidate(source, Collections.singletonList(new Segment(source, text, true)), false);
    }
    public static InputCandidate chinese(DictionaryEngine dictionary, String source, String text) {
        List<String> parts = dictionary.matchQuickCodes(source, text);
        if (parts.isEmpty()) return new InputCandidate(source,
            Collections.singletonList(new Segment(source, text, false)), false);
        List<Segment> segments = new ArrayList<>(); int at = 0;
        for (String part : parts) {
            String character = new String(Character.toChars(text.codePointAt(at))); at += character.length();
            segments.add(new Segment(part, character, false));
        }
        return new InputCandidate(source, segments, false);
    }
    public boolean englishOnly() {
        return !segments.isEmpty() && segments.stream().allMatch(s -> s.english);
    }
    public String effectiveCode() {
        StringBuilder result = new StringBuilder();
        for (Segment segment : segments) result.append(segment.code);
        return result.toString();
    }
    public InputCandidate replace(int index, String replacement) {
        List<Segment> result = new ArrayList<>(segments);
        Segment original = result.get(index);
        result.set(index, new Segment(original.code, replacement, original.english));
        return new InputCandidate(source, result, corrected);
    }
}
