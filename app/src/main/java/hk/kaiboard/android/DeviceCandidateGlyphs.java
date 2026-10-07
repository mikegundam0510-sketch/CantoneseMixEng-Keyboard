package hk.kaiboard.android;

import android.graphics.Paint;
import android.graphics.Typeface;

final class DeviceCandidateGlyphs {
    private DeviceCandidateGlyphs() {}

    static CandidateGlyphFilter create() {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setTypeface(Typeface.DEFAULT);
        paint.setTextSize(23);
        // Probe each scalar: hasGlyph on an ordinary multi-character word tests a ligature.
        return new CandidateGlyphFilter(cp -> paint.hasGlyph(new String(Character.toChars(cp))));
    }
}
