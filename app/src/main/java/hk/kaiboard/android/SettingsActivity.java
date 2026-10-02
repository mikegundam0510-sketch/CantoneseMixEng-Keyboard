package hk.kaiboard.android;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.provider.Settings;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public final class SettingsActivity extends Activity {
    private LinearLayout page;
    private SharedPreferences prefs;
    private TextView status;
    private final int ink = Color.rgb(30, 35, 58), accent = Color.rgb(89, 100, 232);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = Prefs.get(this);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(243, 244, 248));
        page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(22), dp(24), dp(22), dp(32)); scroll.addView(page);
        scroll.setOnApplyWindowInsetsListener((v, insets) -> {
            v.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(scroll);
        text(page, "K.", 38, accent, true);
        text(page, "Kaiboard Android", 28, ink, true);
        text(page, "速成・倉頡・English\n一個鍵盤，自然混合輸入。", 16, Color.DKGRAY, false);

        LinearLayout start = card("開始使用");
        status = text(start, "", 14, accent, true);
        button(start, "1   啟用 Kaiboard", () -> startActivity(new Intent(Settings.ACTION_INPUT_METHOD_SETTINGS)));
        button(start, "2   選擇預設鍵盤", () -> ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());
        text(start, "Samsung：設定 → 一般管理 → 鍵盤清單及預設。", 13, Color.DKGRAY, false);

        LinearLayout methods = card("混合輸入");
        toggle(methods, "速成（首尾碼）", "quick", true);
        toggle(methods, "倉頡五代（完整字碼）", "cangjie", true);
        toggle(methods, "基本英文補全", "english", true);
        toggle(methods, "學習選字排序（只儲存於手機）", "learning", true);
        button(methods, "清除學習記錄", () -> new AlertDialog.Builder(this).setTitle("清除學習記錄？")
            .setMessage("將恢復預設選字次序。鍵盤設定不受影響。")
            .setNegativeButton("取消", null).setPositiveButton("清除", (d, which) -> {
                getSharedPreferences("learned", MODE_PRIVATE).edit().clear().apply();
                Toast.makeText(this, "已清除學習記錄", Toast.LENGTH_SHORT).show();
            }).show());
        text(methods, "速成優先；候選列可左右滑動。點選「英文」保留原字，空白鍵選第一個候選字。", 13, Color.DKGRAY, false);

        LinearLayout look = card("外觀與手感");
        choice(look, "主題", "theme", new String[]{"跟隨系統", "淺色", "深色"}, new String[]{"system", "light", "dark"}, "system");
        choice(look, "單手模式", "hand", new String[]{"全寬", "左手", "右手"}, new String[]{"full", "left", "right"}, "full");
        choice(look, "按鍵高度", "height", new String[]{"標準", "較高", "特高"}, new String[]{"48", "54", "60"}, "48");
        toggle(look, "顯示數字列", "numbers", false);
        toggle(look, "展開大螢幕時分體排列（Fold）", "split", true);
        toggle(look, "按鍵震動", "haptic", true);

        LinearLayout practice = card("試打一下");
        text(practice, "你：人火 OF　好：女木 VD\n香港：竹日 HA ／ 水山 EU", 14, Color.DKGRAY, false);
        EditText field = new EditText(this);
        field.setHint("試打中文、English 或 Emoji…"); field.setTextSize(17);
        field.setMinLines(3); field.setGravity(Gravity.TOP);
        field.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        practice.addView(field, new LinearLayout.LayoutParams(-1, -2));
        text(practice, "左右滑動空白鍵移動游標；長按刪除鍵連續刪字；長按 ⇧ 鎖定大寫。", 13, Color.DKGRAY, false);

        LinearLayout ai = card("Samsung AI 寫作輔助");
        text(ai, "在支援 Galaxy AI 的 One UI 7 或以上裝置，輸入後長按並選取文字，再查看選單有否 Galaxy AI／寫作輔助。功能由 Samsung 提供，視手機、地區及應用程式而定。", 14, Color.DKGRAY, false);
        text(ai, "如未見選項，可切換至 Samsung Keyboard，再使用其 AI 工具。本 App 未內置 Samsung AI 引擎。", 14, Color.DKGRAY, false);
        button(ai, "開啟鍵盤選擇器", () -> ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());

        LinearLayout about = card("離線與私隱");
        text(about, "鍵盤無網絡權限，不記錄整段文字，亦不讀取剪貼簿。開啟學習後，只在手機儲存你選取的單一中文字、字碼及次數。密碼欄停用建議與學習；App 要求不學習時亦不使用或更新學習記錄。記錄不會備份到雲端。Samsung AI 的資料處理由 Samsung 功能本身管理。", 14, Color.DKGRAY, false);
        text(about, "獨立開發的 Android 鍵盤，並非 Kaiboard 或 Samsung 官方產品。採用 Rime 倉頡五代基礎碼表；速成由首尾碼生成，選字次序可能與其他速成鍵盤不同。", 13, Color.DKGRAY, false);
        button(about, "開源資料與授權", this::showLicenses);
    }

    @Override protected void onResume() {
        super.onResume();
        InputMethodManager imm = (InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
        boolean enabled = imm.getEnabledInputMethodList().stream().anyMatch(i -> i.getPackageName().equals(getPackageName()));
        String current = Settings.Secure.getString(getContentResolver(), Settings.Secure.DEFAULT_INPUT_METHOD);
        status.setText(current != null && current.startsWith(getPackageName() + "/") ? "已啟用 · 正在使用" : enabled ? "已啟用 · 請選擇預設鍵盤" : "尚未啟用");
    }

    private void toggle(LinearLayout parent, String title, String key, boolean fallback) {
        Switch control = new Switch(this); control.setText(title); control.setTextColor(ink); control.setTextSize(16);
        control.setPadding(0, dp(12), 0, dp(12)); control.setMinHeight(dp(48));
        control.setChecked(prefs.getBoolean(key, fallback));
        control.setOnCheckedChangeListener((b, checked) -> prefs.edit().putBoolean(key, checked).apply());
        parent.addView(control, new LinearLayout.LayoutParams(-1, -2));
    }

    private void choice(LinearLayout parent, String label, String key, String[] titles, String[] values, String fallback) {
        Button control = new Button(this); control.setAllCaps(false);
        Runnable update = () -> {
            String value = prefs.getString(key, fallback); int selected = 0;
            for (int i = 0; i < values.length; i++) if (values[i].equals(value)) selected = i;
            control.setText(label + "   ·   " + titles[selected]);
        };
        update.run();
        control.setOnClickListener(v -> new AlertDialog.Builder(this).setTitle(label).setItems(titles, (d, which) -> {
            prefs.edit().putString(key, values[which]).apply(); update.run();
        }).show());
        parent.addView(control, new LinearLayout.LayoutParams(-1, -2));
    }

    private LinearLayout card(String title) {
        LinearLayout box = new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL); box.setPadding(dp(18), dp(18), dp(18), dp(18));
        GradientDrawable shape = new GradientDrawable(); shape.setColor(Color.WHITE); shape.setCornerRadius(dp(20)); box.setBackground(shape);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2); params.topMargin = dp(18); page.addView(box, params);
        text(box, title, 19, ink, true); return box;
    }

    private TextView text(LinearLayout parent, String value, int size, int color, boolean bold) {
        TextView v = new TextView(this); v.setText(value); v.setTextSize(size); v.setTextColor(color); v.setLineSpacing(dp(3), 1);
        if (bold) v.setTypeface(null, Typeface.BOLD); v.setPadding(0, 0, 0, dp(10)); parent.addView(v); return v;
    }

    private void button(LinearLayout parent, String title, Runnable action) {
        Button b = new Button(this); b.setText(title); b.setAllCaps(false); b.setTextColor(accent); b.setOnClickListener(v -> action.run());
        parent.addView(b, new LinearLayout.LayoutParams(-1, -2));
    }

    private void showLicenses() {
        StringBuilder content = new StringBuilder("Rime Cangjie dictionary\nhttps://github.com/rime/rime-cangjie\nCommit: 52d90a1b1312e74042b38c1cbc8142defbc53171\n\n");
        for (String name : new String[]{"AUTHORS", "GPL-3.0.txt", "LGPL-3.0.txt"}) {
            try (InputStream stream = getAssets().open("licenses/" + name)) {
                ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] buf = new byte[4096]; int n;
                while ((n = stream.read(buf)) != -1) bytes.write(buf, 0, n);
                content.append(new String(bytes.toByteArray(), StandardCharsets.UTF_8)).append("\n\n");
            } catch (IOException e) { content.append("License file unavailable: ").append(name); }
        }
        ScrollView scroll = new ScrollView(this); TextView body = new TextView(this); body.setText(content); body.setTextIsSelectable(true);
        body.setPadding(dp(20), dp(16), dp(20), dp(16)); scroll.addView(body);
        new AlertDialog.Builder(this).setTitle("開源授權").setView(scroll).setPositiveButton("關閉", null).show();
    }

    private int dp(float v) { return Math.round(v * getResources().getDisplayMetrics().density); }
}
