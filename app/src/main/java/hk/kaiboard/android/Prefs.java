package hk.kaiboard.android;

import android.content.Context;
import android.content.SharedPreferences;

final class Prefs {
    static synchronized SharedPreferences get(Context context) {
        SharedPreferences prefs = context.getSharedPreferences("keyboard", Context.MODE_PRIVATE);
        if (!prefs.getBoolean("compact_key_geometry", false)) {
            String oldHeight = prefs.getString("height", "50");
            String height = "56".equals(oldHeight) ? "46" : "62".equals(oldHeight) ? "52" : "40";
            prefs.edit().putString("height", height).putBoolean("compact_key_geometry", true).apply();
        }
        if (!prefs.getBoolean("roomier_key_geometry_v1", false)) {
            String oldHeight = prefs.getString("height", "40");
            String height = "46".equals(oldHeight) ? "50" : "52".equals(oldHeight) ? "56" : "44";
            prefs.edit().putString("height", height).putBoolean("roomier_key_geometry_v1", true).apply();
        }
        if (!prefs.getBoolean("privacy_defaults_v1", false)) {
            // Clear automatically collected history before marking migration complete.
            context.getSharedPreferences("learned", Context.MODE_PRIVATE).edit().clear().commit();
            context.getSharedPreferences("english_learned", Context.MODE_PRIVATE).edit().clear().commit();
            context.getSharedPreferences("recent_learned", Context.MODE_PRIVATE).edit().clear().commit();
            prefs.edit().putBoolean("learning", false).putBoolean("emoji_recent", false)
                .remove("recent_emoji").putBoolean("privacy_defaults_v1", true).commit();
        }
        return prefs;
    }
}

