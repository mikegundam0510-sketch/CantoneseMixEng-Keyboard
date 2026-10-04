package hk.kaiboard.android;

import org.junit.Test;
import java.util.Arrays;
import java.util.Collections;
import static org.junit.Assert.*;

public class VoicePolicyTest {
    @Test public void legacyProviderRetryStaysInSameLanguage() {
        assertEquals("yue-Hant-HK", VoicePolicy.alternate("yue-HK", false));
        assertEquals("yue-HK", VoicePolicy.alternate("yue-Hant-HK", false));
        assertEquals("en-US", VoicePolicy.alternate("en-HK", true));
        assertNull(VoicePolicy.alternate("zh-CN", false));
        assertNull(VoicePolicy.alternate("en-US", true));
    }
    @Test public void cantoneseUsesProviderScriptTag() {
        assertEquals("yue-Hant-HK", VoicePolicy.language(false, Arrays.asList("en-US", "yue-Hant-HK")));
    }
    @Test public void englishCanUseInstalledModelInsteadOfMissingHongKongModel() {
        assertEquals("en-US", VoicePolicy.language(true, Arrays.asList("yue-HK", "en-US")));
        assertEquals("en-HK", VoicePolicy.language(true, Arrays.asList("en-US", "en-HK")));
    }
    @Test public void neverSilentlySubstitutesMandarinOrEnglishForCantonese() {
        assertNull(VoicePolicy.language(false, Arrays.asList("zh-CN", "zh-TW", "en-US")));
        assertNull(VoicePolicy.language(false, Collections.emptyList()));
        assertNull(VoicePolicy.language(false, null));
    }
    @Test public void preservesActualProviderTag() {
        assertEquals("YUE_hant_HK", VoicePolicy.language(false, Arrays.asList(null, "YUE_hant_HK")));
    }
    @Test public void onlyServiceOrModelFailuresOfferAlternative() {
        assertTrue(VoicePolicy.recovery(5));
        assertTrue(VoicePolicy.recovery(12));
        assertTrue(VoicePolicy.recovery(13));
        assertFalse(VoicePolicy.recovery(9));
        assertFalse(VoicePolicy.recovery(6));
        assertFalse(VoicePolicy.recovery(7));
        assertFalse(VoicePolicy.recovery(10));
    }
    @Test public void diagnosticsDistinguishPermissionsAudioAndMissingModels() {
        assertTrue(VoicePolicy.error(9).contains("權限"));
        assertTrue(VoicePolicy.error(3).contains("咪高峰"));
        assertTrue(VoicePolicy.error(13).contains("模型"));
        assertTrue(VoicePolicy.error(99).contains("99"));
    }
}
