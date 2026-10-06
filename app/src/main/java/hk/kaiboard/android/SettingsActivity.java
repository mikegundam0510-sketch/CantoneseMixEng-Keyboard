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
        text(page, "粵", 38, accent, true);
        text(page, getString(R.string.app_name), 28, ink, true);
        text(page, "速成・倉頡・English\n一個鍵盤，自然混合輸入。", 16, Color.DKGRAY, false);

        LinearLayout start = card("開始使用");
        status = text(start, "", 14, accent, true);
        button(start, "1   啟用鍵盤", () -> startActivity(new Intent(Settings.ACTION_INPUT_METHOD_SETTINGS)));
        button(start, "2   選擇預設鍵盤", () -> ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());
        text(start, "Samsung：設定 → 一般管理 → 鍵盤清單及預設。", 13, Color.DKGRAY, false);

        LinearLayout methods = card("混合輸入");
        toggle(methods, "速成（首尾碼）", "quick", true);
        toggle(methods, "連續速成組詞", "continuous", true);
        toggle(methods, "倉頡五代（完整字碼）", "cangjie", true);
        toggle(methods, "英文補全", "english", true);
        toggle(methods, "中英混合分段候選", "mixed", true);
        toggle(methods, "參考上文排序候選", "context_candidates", true);
        toggle(methods, "輸入完成後顯示聯想字", "next_suggestions", true);
        toggle(methods, "英文拼字修正候選", "english_repair", true);
        toggle(methods, "英文詞顯示中文候選", "english_chinese", true);
        toggle(methods, "速成相鄰按鍵修正候選", "quick_repair", true);
        toggle(methods, "倉頡相鄰按鍵修正候選", "cangjie_repair", true);
        toggle(methods, "倉頡／速成自動修正", "chinese_autocorrect", true);
        toggle(methods, "儲存選字及英文詞作學習（預設關閉）", "learning", false);
        button(methods, "清除學習記錄", () -> new AlertDialog.Builder(this).setTitle("清除學習記錄？")
            .setMessage("將恢復預設選字次序。鍵盤設定不受影響。")
            .setNegativeButton("取消", null).setPositiveButton("清除", (d, which) -> {
                getSharedPreferences("learned", MODE_PRIVATE).edit().clear().apply();
                getSharedPreferences("english_learned", MODE_PRIVATE).edit().clear().apply();
                Toast.makeText(this, "已清除學習記錄", Toast.LENGTH_SHORT).show();
            }).show());
        button(methods, "管理英文學習記錄", this::manageEnglishLearning);
        button(methods, "新增自訂詞", this::addCustomWord);
        button(methods, "管理自訂詞及置頂候選", this::managePersonal);
        text(methods, "倉頡按空白鍵確認目前突出顯示的候選字。輸入完成後可點選聯想字繼續輸入。英文段按空白鍵確認詞語及加入空格。有歧義時點「英文」指定。長按候選可置頂或分段改選；↶ 重選最近一次已完成的選字。自動修正會於空白鍵或下一段輸入時採用明確較合理的修正字；信心不足時保留候選。修正後按刪除可還原原碼（若已開始下一段，先刪除下一段）。", 13, Color.DKGRAY, false);

        LinearLayout tools = card("功能列");
        choice(tools, "自訂功能鍵", "toolbar_action", new String[]{"剪貼簿", "候選展開", "快捷文字", "Undo"},
            new String[]{"clipboard", "expand", "quick_text", "undo"}, "clipboard");
        choice(tools, "剪貼簿自動清除時間", "clipboard_clear_ms",
            new String[]{"關閉", "1 分鐘", "5 分鐘", "15 分鐘", "1 小時"},
            new String[]{"0", "60000", "300000", "900000", "3600000"}, "300000");
        text(tools, "自動清除鍵盤內的剪貼簿暫存；每項由首次讀取時計時。收起鍵盤或轉到另一輸入框仍會立即清除。", 13, Color.DKGRAY, false);
        button(tools, "新增快捷文字", this::addQuickText);
        button(tools, "管理快捷文字", this::manageQuickTexts);

        LinearLayout voice = card("語音輸入");
        toggle(voice, "只用裝置內語音辨識（預設關閉）", "voice_offline_only", false);
        text(voice, "撳咪直接使用手機預設語音服務，可能經網絡處理語音；本 App 唔會儲存錄音。只用裝置內辨識須手機支援所選語言嘅離線模型。", 13, Color.DKGRAY, false);

        LinearLayout look = card("外觀與手感");
        choice(look, "主題", "theme", new String[]{"跟隨系統", "淺色", "深色"}, new String[]{"system", "light", "dark"}, "system");
        choice(look, "單手模式", "hand", new String[]{"全寬", "左手", "右手"}, new String[]{"full", "left", "right"}, "full");
        choice(look, "按鍵高度", "height", new String[]{"標準", "較高", "特高"}, new String[]{"44", "50", "56"}, "44");
        toggle(look, "顯示數字列", "numbers", true);
        toggle(look, "展開大螢幕時分體排列（Fold）", "split", true);
        toggle(look, "按鍵震動", "haptic", true);
        toggle(look, "在字根按鍵區左右掃動反白選字", "swipe_cursor", true);

        toggle(look, "保留最近使用 Emoji（預設關閉）", "emoji_recent", false);
        button(look, "清除最近使用 Emoji", () -> { prefs.edit().remove("recent_emoji").apply(); Toast.makeText(this, "已清除 Emoji 記錄", Toast.LENGTH_SHORT).show(); });

        LinearLayout practice = card("試打一下");
        text(practice, "你好嗎：OF VD RF（可連續輸入）\n香港：HA EU", 14, Color.DKGRAY, false);
        EditText field = new EditText(this);
        field.setHint("試打中文、English 或 Emoji…"); field.setTextSize(17);
        field.setMinLines(3); field.setGravity(Gravity.TOP);
        field.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        practice.addView(field, new LinearLayout.LayoutParams(-1, -2));
        text(practice, "字根區左右掃動反白選字，反向掃動縮回並取消反白；空白鍵左右掃動游標；長按刪除鍵連續刪字；長按 ⇧ 鎖定大寫。", 13, Color.DKGRAY, false);

        LinearLayout ai = card("Samsung AI 寫作輔助");
        text(ai, "在支援 Galaxy AI 的 One UI 7 或以上裝置，輸入後長按並選取文字，再查看選單有否 Galaxy AI／寫作輔助。功能由 Samsung 提供，視手機、地區及應用程式而定。", 14, Color.DKGRAY, false);
        text(ai, "如未見選項，可切換至 Samsung Keyboard，再使用其 AI 工具。本 App 未內置 Samsung AI 引擎。", 14, Color.DKGRAY, false);
        button(ai, "開啟鍵盤選擇器", () -> ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());

        LinearLayout about = card("離線與私隱");
        text(about, "字碼及候選可離線使用，App 無網絡權限。上文只用於當次候選排序，不保存整段文字。自動學習及最近 Emoji 記錄預設關閉，更新時清除舊自動學習紀錄。如你自行開啟，所選中文字及英文詞或 Emoji 會儲存於手機；手動自訂詞和置頂亦會儲存，可管理及清除，不作備份或轉移。密碼欄停用候選和學習；敏感欄位及要求不學習的輸入框不使用或更新個人詞庫，亦不讀取上文或啟動語音。剪貼簿只在你開啟面板或按更新時讀取，最多暫存 10 項；收起鍵盤或轉到另一輸入框即清除，不寫入檔案。密碼欄不讀取，系統標示為敏感的剪貼簿不加入面板；要求不學習的輸入框只顯示當前剪貼簿。快捷文字只儲存你自行新增的內容，可刪除及清空。語音預設使用手機語音服務，可能經網絡處理；可選擇只用裝置內辨識。本 App 不保存錄音。", 14, Color.DKGRAY, false);
        text(about, "獨立開發的 Android 鍵盤，並非 Kaiboard 或 Samsung 官方產品。採用 Rime 倉頡五代碼表與詞庫，以及 Unicode Emoji 資料；速成由首尾碼生成，選字次序可能與其他速成鍵盤不同。", 13, Color.DKGRAY, false);
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

    private void addQuickText() {
        EditText input = new EditText(this); input.setHint("輸入常用句、地址或電話");
        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("新增快捷文字").setView(input)
            .setNegativeButton("取消",null).setPositiveButton("儲存",null).create();
        dialog.setOnShowListener(d -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String value = input.getText().toString(); java.util.List<String> values = QuickTexts.read(prefs);
            if (value.trim().isEmpty() || value.length() > 2000) { input.setError("請輸入最多 2000 字的文字"); return; }
            if (!values.contains(value)) {
                if (values.size() >= 50) { input.setError("最多 50 項，請先刪除部分文字"); return; }
                values.add(value); QuickTexts.write(prefs, values);
            }
            dialog.dismiss();
        })); dialog.show();
    }

    private void manageQuickTexts() {
        java.util.List<String> values = QuickTexts.read(prefs);
        if (values.isEmpty()) { Toast.makeText(this,"未有快捷文字",Toast.LENGTH_SHORT).show(); return; }
        new AlertDialog.Builder(this).setTitle("點選快捷文字可刪除").setItems(values.toArray(new String[0]),(d,index) -> {
            values.remove(index); QuickTexts.write(prefs,values); manageQuickTexts();
        }).setNegativeButton("關閉",null).setNeutralButton("清空",(d,index) ->
            new AlertDialog.Builder(this).setTitle("清空快捷文字？").setNegativeButton("取消",null)
                .setPositiveButton("清空",(confirm,which) -> prefs.edit().remove("quick_texts").apply()).show()).show();
    }

    private void addCustomWord() {
        LinearLayout inputs = new LinearLayout(this); inputs.setOrientation(LinearLayout.VERTICAL);
        inputs.setPadding(dp(20),dp(10),dp(20),dp(10));
        EditText word = new EditText(this); word.setHint("詞語，例如 AQHI 或常用中文詞");
        word.setSingleLine(true); inputs.addView(word);
        EditText code = new EditText(this); code.setHint("中文輸入字碼；英文詞可留空");
        code.setSingleLine(true); code.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
        inputs.addView(code);
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("新增自訂詞").setView(inputs)
            .setNegativeButton("取消",null).setPositiveButton("儲存",null).create();
        dialog.setOnShowListener(d -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String value = word.getText().toString().trim(), input = code.getText().toString().trim().toLowerCase(java.util.Locale.ROOT);
            if (value.isEmpty() || value.codePointCount(0,value.length()) > 32 || value.contains("\n")) {
                word.setError("請輸入 1–32 個字的詞語"); return;
            }
            if (input.isEmpty() && !EnglishEngine.validWord(value)) { code.setError("中文詞請填字碼"); return; }
            if (!input.isEmpty() && !input.matches("[a-z]{1,48}")) { code.setError("請填 1–48 個英文字母"); return; }
            SharedPreferences data = getSharedPreferences("personal", MODE_PRIVATE);
            String key = input.isEmpty() ? "e:" + value.toLowerCase(java.util.Locale.ROOT) : "c:" + input + ":" + value;
            if (!data.contains(key) && data.getAll().size() >= 500) { word.setError("請先刪除部分自訂詞或置頂記錄"); return; }
            data.edit().putString(key,value).apply(); dialog.dismiss();
            Toast.makeText(this,"已儲存自訂詞",Toast.LENGTH_SHORT).show();
        }));
        dialog.show();
    }

    private void manageEnglishLearning() {
        SharedPreferences data = getSharedPreferences("english_learned",MODE_PRIVATE);
        java.util.List<String> words = new java.util.ArrayList<>(data.getAll().keySet());
        java.util.Collections.sort(words,String.CASE_INSENSITIVE_ORDER);
        if (words.isEmpty()) { Toast.makeText(this,"未有英文學習記錄",Toast.LENGTH_SHORT).show(); return; }
        new AlertDialog.Builder(this).setTitle("點選英文詞可刪除").setItems(words.toArray(new String[0]),(d,index)->{
            data.edit().remove(words.get(index)).apply(); manageEnglishLearning();
        }).setNegativeButton("關閉",null).show();
    }

    private void managePersonal() {
        SharedPreferences data = getSharedPreferences("personal", MODE_PRIVATE);
        java.util.List<String> keys = new java.util.ArrayList<>(data.getAll().keySet());
        java.util.Collections.sort(keys);
        if (keys.isEmpty()) { Toast.makeText(this,"未有自訂詞或置頂候選",Toast.LENGTH_SHORT).show(); return; }
        String[] labels = new String[keys.size()];
        for (int i=0;i<keys.size();i++) {
            String key=keys.get(i), value=data.getString(key,"");
            String[] parts = key.split(":",4);
            labels[i]=(key.startsWith("p:")?"置頂 · "+parts[2]+" · ":key.startsWith("e:")?"英文 · ":"自訂 · "+parts[1]+" · ")+value;
        }
        new AlertDialog.Builder(this).setTitle("點選記錄可刪除").setItems(labels,(d,index)->
            new AlertDialog.Builder(this).setTitle("刪除「"+data.getString(keys.get(index),"")+"」？")
                .setNegativeButton("取消",null).setPositiveButton("刪除",(confirm,which)->{
                    data.edit().remove(keys.get(index)).apply(); managePersonal();
                }).show()).setNegativeButton("關閉",null)
            .setNeutralButton("清除全部",(d,which)->new AlertDialog.Builder(this).setTitle("清除全部自訂詞及置頂候選？")
                .setNegativeButton("取消",null).setPositiveButton("清除",(confirm,index)->data.edit().clear().apply()).show()).show();
    }

    private void showLicenses() {
        StringBuilder content = new StringBuilder("Rime Cangjie dictionary\nhttps://github.com/rime/rime-cangjie\nCommit: 52d90a1b1312e74042b38c1cbc8142defbc53171\n\n");
        content.append("HKCanCor: Luke, Kang Kwong & Wong, May L. Y. (2015), The Hong Kong Cantonese Corpus\nhttps://github.com/fcbond/hkcancor\nRime Cantonese: CanCLID contributors\nhttps://github.com/rime/rime-cantonese\nDerived vocabulary and offline 5-gram model; CC BY 4.0.\n\n");
        for (String name : new String[]{"AUTHORS", "GPL-3.0.txt", "LGPL-3.0.txt", "ESSAY-AUTHORS.txt", "UNICODE-LICENSE.txt", "HKCANCOR-CC-BY-4.0.txt", "RIME-CANTONESE-CC-BY-4.0.txt", "cangjie-completion/LICENSE.txt"}) {
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



