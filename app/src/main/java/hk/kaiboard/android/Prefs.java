package hk.kaiboard.android;

import android.content.Context;
import android.content.SharedPreferences;

final class Prefs {
    static SharedPreferences get(Context context) { return context.getSharedPreferences("keyboard", Context.MODE_PRIVATE); }
}
