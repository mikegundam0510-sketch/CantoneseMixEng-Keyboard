package hk.kaiboard.android;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

/** Exercises actual Android preferences with an isolated package storage directory. */
@RunWith(AndroidJUnit4.class)
public final class PrivacyDefaultsTest {
    private Context context;
    private SharedPreferences data(String name) {
        return context.getSharedPreferences(name, Context.MODE_PRIVATE);
    }
    @Before public void setUp() {
        context = InstrumentationRegistry.getInstrumentation().getContext();
        clear();
    }
    @After public void clear() {
        if (context == null) return;
        for (String name : new String[]{"keyboard", "learned", "english_learned", "recent_learned", "rejected_learned", "personal"})
            data(name).edit().clear().commit();
    }
    @Test public void freshInstallDoesNotRecordHistory() {
        SharedPreferences prefs = Prefs.get(context);
        assertFalse(prefs.getBoolean("learning", true));
        assertFalse(prefs.getBoolean("emoji_recent", true));
        assertFalse(prefs.contains("recent_emoji"));
    }
    @Test public void upgradeErasesAutomaticHistoryButPreservesManualWordsAndLayout() {
        data("keyboard").edit().putBoolean("learning", true).putBoolean("emoji_recent", true)
            .putString("recent_emoji", "😀").putString("theme", "dark").commit();
        data("learned").edit().putInt("test", 8).commit();
        data("english_learned").edit().putInt("Confidential", 3).commit();
        data("recent_learned").edit().putString("E:Confidential", "123:1.0").commit();
        data("rejected_learned").edit().putString("W:wrong", "123:1.0").commit();
        data("personal").edit().putString("manual", "AQHI").commit();
        SharedPreferences prefs = Prefs.get(context);
        assertFalse(prefs.getBoolean("learning", true));
        assertFalse(prefs.getBoolean("emoji_recent", true));
        assertFalse(prefs.contains("recent_emoji"));
        assertTrue(data("learned").getAll().isEmpty());
        assertTrue(data("english_learned").getAll().isEmpty());
        assertTrue(data("recent_learned").getAll().isEmpty());
        assertTrue(data("rejected_learned").getAll().isEmpty());
        assertEquals("AQHI", data("personal").getString("manual", ""));
        assertEquals("dark", prefs.getString("theme", ""));
    }
    @Test public void explicitOptInSurvivesSubsequentStarts() {
        Prefs.get(context).edit().putBoolean("learning", true).commit();
        data("english_learned").edit().putInt("AQHI", 1).commit();
        assertTrue(Prefs.get(context).getBoolean("learning", false));
        assertEquals(1, data("english_learned").getInt("AQHI", 0));
    }
    @Test public void updateFrom0618KeepsChinesePhraseAndEnglishLearning() {
        Prefs.get(context).edit().putBoolean("learning", true).putString("theme", "dark").commit();
        data("learned").edit().putInt("QC:of:你", 12).putInt("W:唔該晒", 7).commit();
        data("english_learned").edit().putInt("AQHI", 3).commit();
        data("personal").edit().putString("manual", "自訂詞").commit();
        data("recent_learned").edit().putString("W:唔該晒", "123:2.0").commit();
        data("rejected_learned").edit().putString("W:wrong", "123:1.0").commit();
        for (int i = 0; i < 3; i++) {
            SharedPreferences prefs = Prefs.get(context);
            assertTrue(prefs.getBoolean("learning", false));
            assertEquals("dark", prefs.getString("theme", ""));
            assertEquals(12, data("learned").getInt("QC:of:你", 0));
            assertEquals(7, data("learned").getInt("W:唔該晒", 0));
            assertEquals("123:2.0", data("recent_learned").getString("W:唔該晒", null));
            assertEquals("123:1.0", data("rejected_learned").getString("W:wrong", null));
            assertEquals(3, data("english_learned").getInt("AQHI", 0));
            assertEquals("自訂詞", data("personal").getString("manual", ""));
        }
    }
}
