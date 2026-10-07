package hk.kaiboard.android;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.IntPredicate;

/** Device font coverage, independent of dictionary membership and candidate ranking. */
final class CandidateGlyphFilter {
    private final IntPredicate hasGlyph;
    private final Map<Integer, Boolean> coverage = new LinkedHashMap<Integer, Boolean>(256, .75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<Integer, Boolean> entry) {
            return size() > 4096;
        }
    };

    CandidateGlyphFilter(IntPredicate hasGlyph) { this.hasGlyph = hasGlyph; }

    // Search workers and the UI share the cache and font probe; Paint is not thread safe.
    synchronized boolean canDisplay(String text) {
        if (text == null || text.isEmpty()) return false;
        for (int offset = 0; offset < text.length();) {
            int cp = text.codePointAt(offset);
            offset += Character.charCount(cp);
            if (cp == 0xfffd || cp >= 0xd800 && cp <= 0xdfff) return false;
            if (cp >= 0x20 && cp <= 0x7e) continue;
            // Marks/selectors belong to their base, rather than being standalone glyphs.
            int type = Character.getType(cp);
            if (type == Character.NON_SPACING_MARK || type == Character.COMBINING_SPACING_MARK
                    || type == Character.ENCLOSING_MARK || type == Character.FORMAT) continue;
            Boolean supported = coverage.get(cp);
            if (supported == null) {
                supported = hasGlyph.test(cp);
                coverage.put(cp, supported);
            }
            if (!supported) return false;
        }
        return true;
    }
}
