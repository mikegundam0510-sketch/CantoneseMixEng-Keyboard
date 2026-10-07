package hk.kaiboard.android;

import org.junit.Test;
import static org.junit.Assert.*;

/** Run on the target device to verify its actual Android fallback font coverage. */
public class DeviceCandidateGlyphsTest {
    @Test public void defaultFontKeepsHongKongWordsAndRejectsMissingGlyph() {
        CandidateGlyphFilter filter = DeviceCandidateGlyphs.create();
        assertTrue(filter.canDisplay("香港捏扯抵打丟吞"));
        assertTrue(filter.canDisplay("Hello香港"));
        assertFalse(filter.canDisplay(new String(Character.toChars(0x10ffff))));
        assertFalse(filter.canDisplay("\ufffd"));
    }
}
