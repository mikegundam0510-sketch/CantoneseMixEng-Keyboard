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
        return prefs;
    }
}

