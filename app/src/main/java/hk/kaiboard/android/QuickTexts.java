package hk.kaiboard.android;

import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONException;
import java.util.ArrayList;
import java.util.List;

/** Only manually supplied text is persisted, in backup-excluded preferences. */
final class QuickTexts {
    static List<String> read(SharedPreferences prefs) {
        List<String> values = new ArrayList<>();
        try {
            JSONArray array = new JSONArray(prefs.getString("quick_texts", "[]"));
            for (int i = 0; i < array.length() && values.size() < 50; i++) {
                String value = array.optString(i, "");
                if (!value.trim().isEmpty() && value.length() <= 2000 && !values.contains(value)) values.add(value);
            }
        } catch (JSONException ignored) { }
        return values;
    }
    static void write(SharedPreferences prefs, List<String> values) {
        prefs.edit().putString("quick_texts", new JSONArray(values).toString()).apply();
    }
}
