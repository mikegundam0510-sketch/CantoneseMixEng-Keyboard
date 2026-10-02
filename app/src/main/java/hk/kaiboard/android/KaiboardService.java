package hk.kaiboard.android;

import android.content.*;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.inputmethodservice.InputMethodService;
import android.os.*;
import android.text.*;
import android.text.style.RelativeSizeSpan;
import android.view.*;
import android.view.inputmethod.*;
import android.widget.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

public final class KaiboardService extends InputMethodService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService loader = Executors.newSingleThreadExecutor();
    private DictionaryEngine dictionary;
    private boolean loadFailed, destroyed;
    private SharedPreferences prefs;
    private SharedPreferences learned;
    private boolean noLearning;
    private LinearLayout root, panel, candidateRow;
    private HorizontalScrollView candidateScroll;
    private TextView raw, nextPage;
    private final StringBuilder composing = new StringBuilder();
    private List<String> candidates = Collections.emptyList();
    private int candidatePage, bg, keyColor, functionColor, fg, muted, accent;
    private boolean secure, numeric, directField, ascii, shift, caps, symbols, emoji, aiHelp;
    private boolean extraSymbols;
    private boolean quick, cangjie, english, dark;
    private static final int PAGE_SIZE = 30;
    private static final String RADICALS = "日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重";

    @Override public void onCreate() {
        super.onCreate(); prefs = Prefs.get(this); learned = getSharedPreferences("learned", MODE_PRIVATE);
        loader.execute(() -> {
            try {
                DictionaryEngine loaded = new DictionaryEngine(
                    new InputStreamReader(getAssets().open("cangjie5.base.dict.yaml"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("english.txt"), StandardCharsets.UTF_8));
                handler.post(() -> { if (!destroyed) { dictionary = loaded; updateCandidates(); } });
            } catch (IOException e) {
                handler.post(() -> { if (!destroyed) { loadFailed = true; updateCandidates(); } });
            }
        });
    }

    @Override public View onCreateInputView() {
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        render(); return root;
    }

    @Override public void onStartInput(EditorInfo info, boolean restarting) {
        super.onStartInput(info, restarting);
        resetComposition(); stopRepeat();
        int type = info.inputType & InputType.TYPE_MASK_CLASS;
        int variation = info.inputType & InputType.TYPE_MASK_VARIATION;
        secure = InputPolicy.isSecure(info.inputType);
        noLearning = InputPolicy.noLearning(info.inputType, info.imeOptions);
        numeric = type == InputType.TYPE_CLASS_NUMBER || type == InputType.TYPE_CLASS_PHONE || type == InputType.TYPE_CLASS_DATETIME;
        directField = secure || numeric || type == InputType.TYPE_NULL || type == InputType.TYPE_CLASS_TEXT &&
            (variation == InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS || variation == InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS
            || variation == InputType.TYPE_TEXT_VARIATION_URI);
        ascii = directField; shift = false; caps = false; symbols = false; extraSymbols = false; emoji = false; aiHelp = false;
    }

    @Override public void onStartInputView(EditorInfo info, boolean restarting) {
        super.onStartInputView(info, restarting); render();
    }

    @Override public boolean onEvaluateFullscreenMode() { return false; }

    @Override public void onUpdateSelection(int oldStart, int oldEnd, int start, int end, int composingStart, int composingEnd) {
        super.onUpdateSelection(oldStart, oldEnd, start, end, composingStart, composingEnd);
        if (composing.length() > 0 && (start != composingEnd || end != composingEnd)) {
            InputConnection ic = getCurrentInputConnection();
            if (ic != null) ic.finishComposingText();
            resetComposition(); updateCandidates();
        }
    }

    @Override public void onFinishInputView(boolean finishingInput) {
        stopRepeat(); finishLiteral(); super.onFinishInputView(finishingInput);
    }

    @Override public void onFinishInput() {
        stopRepeat(); resetComposition(); updateCandidates(); super.onFinishInput();
    }

    @Override public void onDestroy() {
        destroyed = true; stopRepeat(); handler.removeCallbacksAndMessages(null); loader.shutdownNow(); super.onDestroy();
    }

    private void colors() {
        String theme = prefs.getString("theme", "system");
        dark = theme.equals("dark") || theme.equals("system") &&
            (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        bg = Color.parseColor(dark ? "#171923" : "#EDEFF5");
        keyColor = Color.parseColor(dark ? "#303342" : "#FFFFFF");
        functionColor = Color.parseColor(dark ? "#414559" : "#D7DBEB");
        fg = Color.parseColor(dark ? "#F5F5FA" : "#23283E");
        muted = Color.parseColor(dark ? "#B0B7CD" : "#656D87");
        accent = Color.parseColor(dark ? "#A6AEFF" : "#5964E8");
    }

    private void render() {
        if (root == null) return;
        stopRepeat(); colors(); candidateRow = null; raw = null; nextPage = null;
        quick = prefs.getBoolean("quick", true); cangjie = prefs.getBoolean("cangjie", true); english = prefs.getBoolean("english", true);
        root.removeAllViews(); root.setBackgroundColor(bg); root.setPadding(dp(3), dp(4), dp(3), dp(5));
        LinearLayout dock = row(root);
        String hand = prefs.getString("hand", "full");
        if (hand.equals("right")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));
        panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL);
        dock.addView(panel, new LinearLayout.LayoutParams(0, -2, hand.equals("full") ? 1 : .82f));
        if (hand.equals("left")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));

        LinearLayout tools = row(panel);
        key(tools, secure ? "密碼" : ascii ? "EN" : "混合", 1.2f, true, () -> {
            if (!secure && !numeric) { finishLiteral(); ascii = !ascii; render(); }
        }, 36);
        key(tools, "☺", 1, true, () -> { if (!secure && !numeric) { finishLiteral(); emoji = !emoji; aiHelp = false; render(); } }, 36).setContentDescription("Emoji 鍵盤");
        key(tools, "AI 說明", 1.7f, true, () -> { finishLiteral(); aiHelp = !aiHelp; emoji = false; render(); }, 36);
        key(tools, "單手", 1.2f, true, () -> {
            String value = prefs.getString("hand", "full");
            prefs.edit().putString("hand", value.equals("full") ? "right" : value.equals("right") ? "left" : "full").apply(); render();
        }, 36);
        key(tools, "⚙", 1, true, () -> {
            finishLiteral(); startActivity(new Intent(this, SettingsActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        }, 36).setContentDescription("鍵盤設定");
        key(tools, "⌄", 1, true, () -> requestHideSelf(0), 36).setContentDescription("收起鍵盤");

        if (aiHelp) {
            TextView help = new TextView(this); help.setTextColor(fg); help.setTextSize(15); help.setPadding(dp(14), dp(12), dp(14), dp(12));
            help.setText("Samsung AI 寫作輔助\n\n輸入後，長按並選取文字，再點 Galaxy AI／寫作輔助（限支援裝置）。\n\n未見選項？切換 Samsung Keyboard 使用其 AI 工具。本鍵盤未內置 Samsung AI。");
            panel.addView(help);
            LinearLayout actions = row(panel);
            key(actions, "選擇鍵盤", 1, true, this::picker, 48);
            key(actions, "返回打字", 1, true, () -> { aiHelp = false; render(); }, 48);
            return;
        }

        LinearLayout bar = row(panel);
        raw = key(bar, "", 2, true, () -> commit(composing.toString()), 43);
        raw.setTextSize(13);
        candidateScroll = new HorizontalScrollView(this); candidateScroll.setHorizontalScrollBarEnabled(false);
        candidateRow = new LinearLayout(this); candidateRow.setOrientation(LinearLayout.HORIZONTAL);
        candidateScroll.addView(candidateRow); bar.addView(candidateScroll, new LinearLayout.LayoutParams(0, dp(47), 5));
        nextPage = key(bar, "›", .65f, true, () -> { candidatePage++; displayCandidates(); }, 43);
        nextPage.setContentDescription("下一頁候選字"); updateCandidates();

        if (emoji) {
            String[][] groups = {{"😀","😄","😂","😊","😍","🥰","😎","😭"}, {"👍","👏","🙏","💪","❤","🎉","🔥","✨"},
                {"😅","🤔","😴","🙄","😢","😡","🤝","👌"}, {"☀","🌙","☕","🍺","🎵","🏠","✅","❌"}};
            for (String[] group : groups) { LinearLayout line = row(panel); for (String value : group) key(line, value, 1, false, () -> insert(value), keyHeight()); }
        } else if (numeric) {
            for (String group : new String[]{"123", "456", "789", ".0-"}) {
                LinearLayout line = row(panel);
                for (char value : group.toCharArray()) key(line, String.valueOf(value), 1, false, () -> insert(String.valueOf(value)), keyHeight());
            }
        } else if (symbols) {
            String[][] symbolRows = extraSymbols ? new String[][]{
                {"_","[","]","{","}","<",">","\\","^","~"},
                {"`","|","€","£","¥","•","÷","×","「","」"},
                {"，","。","？","！","：","；","（","）","《","》"}}
                : new String[][]{{"1","2","3","4","5","6","7","8","9","0"},
                {"@","#","$","%","&","*","-","+","(",")"},
                {"?","!",":",";","'","\"","/","=",",","."}};
            for (String[] group : symbolRows) {
                LinearLayout line = row(panel); for (String value : group) key(line, value, 1, false, () -> insert(value), keyHeight());
            }
        } else {
            if (prefs.getBoolean("numbers", false)) {
                LinearLayout line = row(panel); for (char n : "1234567890".toCharArray()) key(line, "" + n, 1, false, () -> insert("" + n), 36);
            }
            letters("qwertyuiop", false); letters("asdfghjkl", false); letters("zxcvbnm", true);
        }

        LinearLayout bottom = row(panel);
        if (!numeric) key(bottom, symbols || emoji ? "ABC" : "123", 1.25f, true, () -> {
            finishLiteral(); if (emoji) emoji = false; else symbols = !symbols; render();
        }, keyHeight());
        if (symbols && !emoji && !numeric) key(bottom, extraSymbols ? "123" : "#+=", 1, true, () -> { extraSymbols = !extraSymbols; render(); }, keyHeight());
        key(bottom, "🌐", 1, true, this::picker, keyHeight()).setContentDescription("切換鍵盤");
        if (!numeric) {
            key(bottom, ascii ? "," : "，", .9f, false, () -> insert(ascii ? "," : "，"), keyHeight());
            TextView space = key(bottom, "空白", 3.6f, false, this::space, keyHeight());
            space.setContentDescription("空白鍵，左右滑動移動游標"); attachSpaceGesture(space);
            key(bottom, ascii ? "." : "。", .9f, false, () -> insert(ascii ? "." : "。"), keyHeight());
        }
        if (symbols || emoji || numeric) deleteKey(bottom, 1.2f);
        key(bottom, enterLabel(), 1.45f, true, this::enter, keyHeight());
        if (getWindow() != null) {
            getWindow().getWindow().setNavigationBarColor(bg);
            getWindow().getWindow().getDecorView().setSystemUiVisibility(dark ? 0 : View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }
    }

    private void letters(String letters, boolean withShift) {
        LinearLayout line = row(panel);
        if (withShift) {
            TextView toggle = key(line, caps ? "⇪" : "⇧", 1.4f, true, () -> { shift = !shift; caps = false; render(); }, keyHeight());
            toggle.setContentDescription("大寫，長按鎖定大寫");
            toggle.setOnLongClickListener(v -> { caps = !caps; shift = caps; render(); return true; });
        } else if (letters.length() == 9) line.setPadding(dp(14), 0, dp(14), 0);
        int position = 0;
        for (char letter : letters.toCharArray()) {
            if (splitLayout() && position == (withShift ? 4 : 5)) {
                line.addView(new View(this), new LinearLayout.LayoutParams(dp(56), dp(1)));
            }
            position++;
            String latin = String.valueOf(shift || caps ? Character.toUpperCase(letter) : letter);
            String label = latin + (!ascii && (quick || cangjie) ? "\n" + RADICALS.charAt(letter - 'a') : "");
            TextView button = key(line, label, 1, false, () -> typeLetter(letter), keyHeight());
            if (label.contains("\n")) {
                SpannableString styled = new SpannableString(label); styled.setSpan(new RelativeSizeSpan(.55f), 2, label.length(), 0); button.setText(styled);
            }
        }
        if (withShift) deleteKey(line, 1.4f);
    }

    private void typeLetter(char lower) {
        String value = String.valueOf(shift || caps ? Character.toUpperCase(lower) : lower);
        if (secure || ascii) insert(value);
        else {
            if (composing.length() >= 48) finishLiteral();
            composing.append(value); InputConnection ic = getCurrentInputConnection();
            if (ic != null) ic.setComposingText(composing, 1);
            updateCandidates();
        }
        if (shift && !caps) { shift = false; render(); }
    }

    private void updateCandidates() {
        candidatePage = 0;
        candidates = secure || composing.length() == 0 ? Collections.emptyList() : dictionary == null ?
            Collections.singletonList(composing.toString()) : dictionary.lookup(composing.toString(), quick, cangjie, english);
        if (!noLearning && prefs.getBoolean("learning", true)) {
            candidates = LearningRanker.rank(candidates, word -> learned.getInt(LearningRanker.key(composing.toString(), quick, cangjie, word), 0));
        }
        displayCandidates();
    }

    private void displayCandidates() {
        if (candidateRow == null || raw == null) return;
        candidateRow.removeAllViews();
        raw.setText(composing.length() == 0 ? secure ? "安全輸入" : loadFailed ? "字庫載入失敗" : dictionary == null ? "載入字庫…" : ascii ? "English" : "速成 · 倉頡" : "英文\n" + composing);
        raw.setEnabled(composing.length() > 0);
        if (candidates.isEmpty()) { nextPage.setVisibility(View.GONE); return; }
        int pages = (candidates.size() + PAGE_SIZE - 1) / PAGE_SIZE;
        candidatePage %= pages;
        for (int i = candidatePage * PAGE_SIZE; i < Math.min(candidates.size(), (candidatePage + 1) * PAGE_SIZE); i++) {
            String value = candidates.get(i);
            TextView item = new TextView(this); item.setText(value); item.setTextSize(23); item.setTextColor(fg);
            item.setGravity(Gravity.CENTER); item.setPadding(dp(16), 0, dp(16), 0); item.setMinWidth(dp(48));
            if (i == 0) { item.setTextColor(accent); item.setTypeface(null, Typeface.BOLD); }
            item.setBackground(background(keyColor)); item.setOnClickListener(v -> commit(value));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, dp(43)); params.setMargins(dp(2), dp(2), dp(2), dp(2));
            candidateRow.addView(item, params);
        }
        nextPage.setVisibility(pages > 1 ? View.VISIBLE : View.GONE);
        nextPage.setText((candidatePage + 1) + "›"); nextPage.setTextSize(13);
        candidateScroll.scrollTo(0, 0);
    }

    private void space() {
        if (composing.length() > 0) commit(candidates.isEmpty() ? composing.toString() : candidates.get(0));
        else insert(" ");
    }

    private void commit(String value) {
        if (value.isEmpty()) return;
        InputConnection ic = getCurrentInputConnection();
        if (ic != null) {
            if (ic.commitText(value, 1) && !noLearning && prefs.getBoolean("learning", true)
                && composing.length() > 0 && LearningRanker.isLearnable(value)) {
                String key = LearningRanker.key(composing.toString(), quick, cangjie, value);
                SharedPreferences.Editor edit = learned.edit();
                Map<String, ?> all = learned.getAll();
                if (!all.containsKey(key) && all.size() >= 2000) {
                    String leastUsed = Collections.min(all.keySet(), Comparator.comparingInt(k -> learned.getInt(k, 0)));
                    edit.remove(leastUsed);
                }
                edit.putInt(key, Math.min(100000, learned.getInt(key, 0) + 1)).apply();
            }
            ic.finishComposingText();
        }
        resetComposition(); updateCandidates();
    }

    private void finishLiteral() {
        if (composing.length() > 0) commit(composing.toString());
    }

    private void insert(String text) {
        finishLiteral(); InputConnection ic = getCurrentInputConnection(); if (ic != null) ic.commitText(text, 1);
    }

    private void delete() {
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        if (composing.length() > 0) {
            composing.deleteCharAt(composing.length() - 1);
            if (composing.length() == 0) { ic.commitText("", 1); ic.finishComposingText(); }
            else ic.setComposingText(composing, 1);
            updateCandidates();
        } else {
            CharSequence selected = ic.getSelectedText(0);
            if (selected != null && selected.length() > 0) ic.commitText("", 1);
            else if (!ic.deleteSurroundingTextInCodePoints(1, 0)) sendKey(KeyEvent.KEYCODE_DEL);
        }
    }

    private String enterLabel() {
        EditorInfo info = getCurrentInputEditorInfo();
        if (info == null || (info.imeOptions & EditorInfo.IME_FLAG_NO_ENTER_ACTION) != 0) return "↵";
        switch (info.imeOptions & EditorInfo.IME_MASK_ACTION) {
            case EditorInfo.IME_ACTION_GO: return "前往";
            case EditorInfo.IME_ACTION_SEARCH: return "搜尋";
            case EditorInfo.IME_ACTION_SEND: return "傳送";
            case EditorInfo.IME_ACTION_NEXT: return "下一個";
            case EditorInfo.IME_ACTION_DONE: return "完成";
            default: return "↵";
        }
    }

    private void enter() {
        if (composing.length() > 0) { finishLiteral(); return; }
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        if (!sendDefaultEditorAction(true)) ic.commitText("\n", 1);
    }

    private void picker() { finishLiteral(); ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker(); }
    private void resetComposition() { composing.setLength(0); candidates = Collections.emptyList(); candidatePage = 0; }
    private void sendKey(int keyCode) { InputConnection ic = getCurrentInputConnection(); if (ic != null) {
        ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, keyCode)); ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, keyCode));
    } }

    private final Runnable repeatDelete = new Runnable() {
        @Override public void run() { delete(); handler.postDelayed(this, 65); }
    };
    private void stopRepeat() { handler.removeCallbacks(repeatDelete); }

    private void deleteKey(LinearLayout line, float weight) {
        TextView button = key(line, "⌫", weight, true, this::delete, keyHeight()); button.setContentDescription("刪除，長按連續刪除");
        button.setOnTouchListener((v, event) -> {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN: v.performClick(); v.setPressed(true); handler.postDelayed(repeatDelete, 400); break;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL: stopRepeat(); v.setPressed(false); break;
            }
            return true;
        });
    }

    private void attachSpaceGesture(TextView key) {
        key.setOnTouchListener(new View.OnTouchListener() {
            float lastX, startX; boolean moved;
            @Override public boolean onTouch(View v, android.view.MotionEvent event) {
                switch (event.getActionMasked()) {
                    case MotionEvent.ACTION_DOWN: startX = lastX = event.getX(); moved = false; v.setPressed(true); return true;
                    case MotionEvent.ACTION_MOVE:
                        if (!moved && Math.abs(event.getX() - startX) > dp(18)) { moved = true; finishLiteral(); }
                        if (moved) {
                            float delta = event.getX() - lastX;
                            if (Math.abs(delta) >= dp(16)) { sendKey(delta > 0 ? KeyEvent.KEYCODE_DPAD_RIGHT : KeyEvent.KEYCODE_DPAD_LEFT); lastX = event.getX(); }
                        }
                        return true;
                    case MotionEvent.ACTION_UP: v.setPressed(false); if (!moved) v.performClick(); return true;
                    case MotionEvent.ACTION_CANCEL: v.setPressed(false); return true;
                    default: return true;
                }
            }
        });
    }

    private LinearLayout row(LinearLayout parent) {
        LinearLayout line = new LinearLayout(this); line.setOrientation(LinearLayout.HORIZONTAL); line.setGravity(Gravity.CENTER_VERTICAL);
        parent.addView(line, new LinearLayout.LayoutParams(-1, -2)); return line;
    }

    private TextView key(LinearLayout parent, String label, float weight, boolean special, Runnable action, int height) {
        TextView button = new TextView(this); button.setText(label); button.setTextColor(fg); button.setTextSize(label.length() > 2 && !label.contains("\n") ? 13 : 20);
        button.setGravity(Gravity.CENTER); button.setIncludeFontPadding(false); button.setMaxLines(2); button.setSingleLine(false);
        button.setBackground(background(special ? functionColor : keyColor)); button.setFocusable(true);
        button.setOnClickListener(v -> { if (prefs.getBoolean("haptic", true)) v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP); action.run(); });
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(height), weight); params.setMargins(dp(2), dp(3), dp(2), dp(3));
        parent.addView(button, params); return button;
    }

    private android.graphics.drawable.Drawable background(int color) {
        GradientDrawable shape = new GradientDrawable(); shape.setColor(color); shape.setCornerRadius(dp(7));
        return new android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(dark ? 0x40FFFFFF : 0x22000000), shape, null);
    }

    private int keyHeight() {
        return getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE ? 38 : Integer.parseInt(prefs.getString("height", "48"));
    }
    private boolean splitLayout() {
        return prefs.getBoolean("split", true) && prefs.getString("hand", "full").equals("full")
            && getResources().getConfiguration().screenWidthDp >= 600;
    }
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
