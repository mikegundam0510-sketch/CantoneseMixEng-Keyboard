package hk.kaiboard.android;

import android.content.*;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.inputmethodservice.InputMethodService;
import android.os.*;
import android.text.*;
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
    private QuickDecoder decoder;
    private EmojiCatalog emojiCatalog;
    private boolean loadFailed, destroyed;
    private SharedPreferences prefs;
    private SharedPreferences learned;
    private boolean noLearning;
    private LinearLayout root, panel, candidateRow;
    private HorizontalScrollView candidateScroll;
    private TextView raw, nextPage, firstToggle, codePreview;
    private boolean chooseFirst;
    private int emojiGroup;
    private final Map<String, Integer> consumedCodes = new HashMap<>();
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
                QuickDecoder phrases = new QuickDecoder(loaded, new InputStreamReader(getAssets().open("quick_phrases.tsv"), StandardCharsets.UTF_8));
                EmojiCatalog emojis = new EmojiCatalog(new InputStreamReader(getAssets().open("emoji.tsv"), StandardCharsets.UTF_8));
                handler.post(() -> { if (!destroyed) { dictionary = loaded; decoder = phrases; emojiCatalog = emojis; if (emoji) render(); else updateCandidates(); } });
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
        ascii = directField; shift = false; caps = false; symbols = false; extraSymbols = false; emoji = false; aiHelp = false; chooseFirst = false;
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
        bg = Color.parseColor(dark ? "#181A1F" : "#DDE0E5");
        keyColor = Color.parseColor(dark ? "#34373D" : "#FFFFFF");
        functionColor = Color.parseColor(dark ? "#494D55" : "#BFC5CE");
        fg = Color.parseColor(dark ? "#F5F6F8" : "#272D36");
        muted = Color.parseColor(dark ? "#C5CAD3" : "#535D6D");
        accent = Color.parseColor(dark ? "#AFC8FC" : "#315991");
    }

    private void render() {
        if (root == null) return;
        stopRepeat(); colors(); candidateRow = null; raw = null; nextPage = null; firstToggle = null; codePreview = null;
        quick = prefs.getBoolean("quick", true); cangjie = prefs.getBoolean("cangjie", true); english = prefs.getBoolean("english", true);
        root.removeAllViews(); root.setBackgroundColor(bg); root.setPadding(dp(splitLayout() ? 14 : 4), dp(5), dp(splitLayout() ? 14 : 4), dp(6));
        LinearLayout dock = row(root);
        String hand = prefs.getString("hand", "full");
        if (hand.equals("right")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));
        panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL);
        dock.addView(panel, new LinearLayout.LayoutParams(0, -2, hand.equals("full") ? 1 : .82f));
        if (hand.equals("left")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));

        LinearLayout tools = row(panel);
        key(tools, secure ? "密碼" : ascii ? "EN" : "中 · EN", 1.6f, true, () -> {
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

        codePreview = new TextView(this); codePreview.setTextColor(muted); codePreview.setTextSize(12);
        codePreview.setPadding(dp(8),0,dp(8),0); codePreview.setSingleLine(true); codePreview.setEllipsize(TextUtils.TruncateAt.START);
        panel.addView(codePreview, new LinearLayout.LayoutParams(-1,dp(22)));
        LinearLayout bar = row(panel);
        raw = key(bar, "英文", 1.35f, true, this::finishLiteral, 42);
        raw.setTextSize(13);
        candidateScroll = new HorizontalScrollView(this); candidateScroll.setHorizontalScrollBarEnabled(false);
        candidateRow = new LinearLayout(this); candidateRow.setOrientation(LinearLayout.HORIZONTAL);
        candidateScroll.addView(candidateRow); bar.addView(candidateScroll, new LinearLayout.LayoutParams(0, dp(48), 6));
        firstToggle = key(bar, "逐字", 1.15f, true, () -> { chooseFirst = !chooseFirst; updateCandidates(); }, 42);
        nextPage = key(bar, "›", .65f, true, () -> { candidatePage++; displayCandidates(); }, 43);
        nextPage.setContentDescription("下一頁候選字"); updateCandidates();

        if (emoji) {
            renderEmoji();
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
            if (prefs.getBoolean("numbers", true)) {
                LinearLayout line = row(panel); int i = 0;
                for (char n : "1234567890".toCharArray()) {
                    if (splitLayout() && i++ == 5) splitGap(line);
                    key(line, "" + n, 1, false, () -> insert("" + n), 37);
                }
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
            TextView space = key(bottom, "␣", splitLayout() ? 6.4f : 3.6f, false, this::space, keyHeight());
            space.setContentDescription("空白鍵，左右滑動移動游標"); attachSpaceGesture(space);
            key(bottom, ascii ? "." : "。", .9f, false, () -> insert(ascii ? "." : "。"), keyHeight());
        }
        if (symbols || emoji || numeric) deleteKey(bottom, 1.2f);
        TextView enterKey = key(bottom, enterLabel(), 1.45f, true, this::enter, keyHeight());
        enterKey.setBackground(background(dark ? Color.parseColor("#486795") : Color.parseColor("#45658D")));
        enterKey.setTextColor(Color.WHITE);
        if (getWindow() != null) {
            getWindow().getWindow().setNavigationBarColor(bg);
            getWindow().getWindow().getDecorView().setSystemUiVisibility(dark ? 0 : View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }
    }

    private void letters(String letters, boolean withShift) {
        LinearLayout line = row(panel);
        if (splitLayout()) {
            LinearLayout left = new LinearLayout(this), right = new LinearLayout(this);
            line.addView(left, new LinearLayout.LayoutParams(0,-2,1)); splitGap(line);
            line.addView(right, new LinearLayout.LayoutParams(0,-2,1));
            if (withShift) shiftKey(left,1);
            int split = withShift ? 4 : 5;
            for (int i=0;i<letters.length();i++) addLetterKey(i<split?left:right,letters.charAt(i));
            if (withShift) {
                right.addView(new View(this),new LinearLayout.LayoutParams(0,1,1)); deleteKey(right,1);
            } else if (letters.length()==9) right.addView(new View(this),new LinearLayout.LayoutParams(0,1,1));
        } else {
            if (withShift) shiftKey(line,1.4f);
            else if (letters.length()==9) line.setPadding(dp(14),0,dp(14),0);
            for(char letter:letters.toCharArray()) addLetterKey(line,letter);
            if(withShift) deleteKey(line,1.4f);
        }
    }

    private void shiftKey(LinearLayout parent,float weight) {
        TextView toggle=key(parent,caps?"⇪":"⇧",weight,true,()->{shift=!shift;caps=false;render();},keyHeight());
        toggle.setContentDescription("大寫，長按鎖定大寫");
        toggle.setOnLongClickListener(v->{caps=!caps;shift=caps;render();return true;});
    }

    private void addLetterKey(LinearLayout parent,char letter) {
        String latin=String.valueOf(Character.toUpperCase(letter));
        TextView button=key(parent,latin,1,false,()->typeLetter(letter),keyHeight());
        if(!ascii && (quick||cangjie)) ((KeyboardKey)button).legend(latin,String.valueOf(RADICALS.charAt(letter-'a')),muted);
    }

    private void typeLetter(char lower) {
        String value = String.valueOf(shift || caps ? Character.toUpperCase(lower) : lower);
        if (secure || ascii) insert(value);
        else {
            if (composing.length() >= 48) space();
            composing.append(value); InputConnection ic = getCurrentInputConnection();
            if (ic != null) ic.setComposingText(composing, 1);
            updateCandidates();
        }
        if (shift && !caps) { shift = false; render(); }
    }

    private void updateCandidates() {
        candidatePage = 0;
        consumedCodes.clear(); String input = composing.toString();
        boolean continuous = quick && prefs.getBoolean("continuous", true) && input.length() > 2 && !secure;
        LinkedHashSet<String> results = new LinkedHashSet<>();
        if (!secure && !input.isEmpty()) {
            if (continuous && chooseFirst && dictionary != null) {
                for (int size = 2; size >= 1; size--) {
                    String part = input.substring(0, size);
                    for (String word : LearningRanker.rank(dictionary.quickCandidates(part), w -> learnedCount(part, w))) {
                        results.add(word); consumedCodes.putIfAbsent(word, size);
                    }
                }
            } else {
                if (continuous && decoder != null) results.addAll(decoder.decode(input, this::learnedCount));
                List<String> single = dictionary == null ? Collections.singletonList(input) : dictionary.lookup(input, quick, cangjie, english);
                results.addAll(LearningRanker.rank(single, word -> learnedCount(input, word)));
            }
        }
        candidates = new ArrayList<>(results);
        for (String word : candidates) consumedCodes.putIfAbsent(word, input.length());
        displayCandidates();
    }

    private int learnedCount(String code, String word) {
        return noLearning || !prefs.getBoolean("learning", true) ? 0 : learned.getInt(LearningRanker.key(code, quick, cangjie, word), 0);
    }

    private void displayCandidates() {
        if (candidateRow == null || raw == null) return;
        candidateRow.removeAllViews();
        raw.setText("英文");
        raw.setEnabled(composing.length() > 0);
        raw.setAlpha(composing.length() > 0 ? 1f : .45f);
        if (codePreview != null) codePreview.setText(composing.length() == 0 ? secure ? "密碼輸入" : loadFailed ? "字庫載入失敗" : dictionary == null ? "載入字庫…" : ascii ? "English" : "速成  ·  倉頡  ·  English" :
            (chooseFirst ? "逐字選取   " : "") + composing.toString().toUpperCase(Locale.ROOT));
        if (firstToggle != null) { firstToggle.setText(chooseFirst ? "整句" : "逐字"); firstToggle.setVisibility(quick && prefs.getBoolean("continuous",true) && composing.length() > 2 ? View.VISIBLE : View.GONE); }
        if (candidates.isEmpty()) { nextPage.setVisibility(View.GONE); return; }
        int pages = (candidates.size() + PAGE_SIZE - 1) / PAGE_SIZE;
        candidatePage %= pages;
        for (int i = candidatePage * PAGE_SIZE; i < Math.min(candidates.size(), (candidatePage + 1) * PAGE_SIZE); i++) {
            String value = candidates.get(i);
            TextView item = new TextView(this); item.setText(value); item.setTextSize(23); item.setTextColor(fg);
            item.setGravity(Gravity.CENTER); item.setPadding(dp(14), 0, dp(14), 0); item.setMinWidth(dp(48)); item.setSingleLine(true);
            item.setContentDescription(value + (chooseFirst ? "，先輸入此字並保留後續字碼" : ""));
            if (i == 0) { item.setTextColor(accent); item.setTypeface(null, Typeface.BOLD); }
            item.setBackground(background(keyColor)); item.setOnClickListener(v -> commit(value));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, dp(42)); params.setMargins(dp(3), dp(3), dp(3), dp(3));
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
        int consumed = consumedCodes.getOrDefault(value, composing.length());
        String code = composing.substring(0, consumed);
        String remaining = composing.substring(consumed);
        if (ic != null) {
            ic.beginBatchEdit();
            boolean accepted = ic.commitText(value, 1);
            if (accepted && !noLearning && prefs.getBoolean("learning", true) && !code.isEmpty()) {
                List<String> parts = quick && dictionary != null ? dictionary.matchQuickCodes(code, value) : Collections.emptyList();
                if (!parts.isEmpty()) {
                    int at = 0;
                    for (String part : parts) {
                        String character = new String(Character.toChars(value.codePointAt(at))); at += character.length();
                        learnCharacter(part, character);
                    }
                } else if (LearningRanker.isLearnable(value)) {
                    learnCharacter(code, value);
                }
            }
            if (accepted) {
                composing.setLength(0); composing.append(remaining); chooseFirst = false;
                if (remaining.isEmpty()) ic.finishComposingText(); else ic.setComposingText(remaining, 1);
            }
            ic.endBatchEdit();
        }
        updateCandidates();
    }

    private void learnCharacter(String code, String character) {
        if (!LearningRanker.isLearnable(character)) return;
        String key = LearningRanker.key(code, quick, cangjie, character);
        SharedPreferences.Editor edit = learned.edit();
        Map<String, ?> all = learned.getAll();
        if (!all.containsKey(key) && all.size() >= 2000) {
            String leastUsed = Collections.min(all.keySet(), Comparator.comparingInt(k -> learned.getInt(k, 0)));
            edit.remove(leastUsed);
        }
        edit.putInt(key, Math.min(100000, learned.getInt(key, 0) + 1)).apply();
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
            else {
                CharSequence before = ic.getTextBeforeCursor(128, 0);
                int units = emojiCatalog == null ? 0 : emojiCatalog.deletionUnits(before);
                if (units > 0) ic.deleteSurroundingText(units, 0);
                else if (!ic.deleteSurroundingTextInCodePoints(1, 0)) sendKey(KeyEvent.KEYCODE_DEL);
            }
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
    private void resetComposition() { composing.setLength(0); candidates = Collections.emptyList(); consumedCodes.clear(); candidatePage = 0; chooseFirst = false; }
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

    private void renderEmoji() {
        if (emojiCatalog == null) {
            TextView loading = new TextView(this); loading.setText("載入 Emoji…"); loading.setTextColor(fg); panel.addView(loading); return;
        }
        HorizontalScrollView tabs = new HorizontalScrollView(this); tabs.setHorizontalScrollBarEnabled(false);
        LinearLayout tabRow = new LinearLayout(this); tabs.addView(tabRow);
        panel.addView(tabs, new LinearLayout.LayoutParams(-1, dp(42)));
        for (int index = -1; index < emojiCatalog.groupCount(); index++) {
            final int group = index;
            TextView tab = new TextView(this); tab.setText(index == -1 ? "最近" : EmojiCatalog.LABELS[index]);
            tab.setTextSize(14); tab.setTextColor(index == emojiGroup ? accent : muted); tab.setGravity(Gravity.CENTER);
            if (index == emojiGroup) { tab.setTypeface(null, Typeface.BOLD); tab.setBackground(background(keyColor)); }
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(dp(62), dp(36)); params.setMargins(dp(2),dp(3),dp(2),dp(3));
            tabRow.addView(tab,params); tab.setOnClickListener(v -> { emojiGroup = group; render(); });
        }
        tabs.post(() -> tabs.scrollTo(Math.max(0, dp((emojiGroup + 1) * 66 - 120)), 0));
        List<EmojiCatalog.Entry> items = emojiGroup < 0 ? emojiCatalog.recent(noLearning || !prefs.getBoolean("emoji_recent",true) ? "" : prefs.getString("recent_emoji","")) : emojiCatalog.group(emojiGroup);
        GridView grid = new GridView(this); grid.setNumColumns(GridView.AUTO_FIT); grid.setColumnWidth(dp(43)); grid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);
        grid.setHorizontalSpacing(dp(3)); grid.setVerticalSpacing(dp(4)); grid.setPadding(dp(4),dp(5),dp(4),dp(5));
        grid.setClipToPadding(false); grid.setVerticalScrollBarEnabled(true);
        grid.setAdapter(new BaseAdapter() {
            @Override public int getCount() { return items.size(); }
            @Override public Object getItem(int position) { return items.get(position); }
            @Override public long getItemId(int position) { return position; }
            @Override public View getView(int position, View convertView, android.view.ViewGroup parent) {
                TextView cell = convertView instanceof TextView ? (TextView)convertView : new TextView(KaiboardService.this);
                EmojiCatalog.Entry entry = items.get(position); cell.setText(entry.symbol); cell.setTextSize(27); cell.setTextColor(fg);
                cell.setGravity(Gravity.CENTER); cell.setContentDescription(entry.name); cell.setBackground(background(keyColor));
                cell.setLayoutParams(new android.widget.AbsListView.LayoutParams(-1,dp(44))); return cell;
            }
        });
        grid.setOnItemClickListener((parent, view, position, id) -> {
            String symbol = items.get(position).symbol; insert(symbol);
            if (!noLearning && prefs.getBoolean("emoji_recent",true)) prefs.edit().putString("recent_emoji",emojiCatalog.remember(prefs.getString("recent_emoji",""),symbol)).apply();
            if (prefs.getBoolean("haptic",true)) view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);
        });
        if (items.isEmpty()) {
            TextView empty = new TextView(this); empty.setText("未有最近使用的 Emoji"); empty.setTextColor(muted); empty.setGravity(Gravity.CENTER);
            panel.addView(empty, new LinearLayout.LayoutParams(-1,dp(200)));
        } else panel.addView(grid, new LinearLayout.LayoutParams(-1,dp(200)));
    }

    private LinearLayout row(LinearLayout parent) {
        LinearLayout line = new LinearLayout(this); line.setOrientation(LinearLayout.HORIZONTAL); line.setGravity(Gravity.CENTER_VERTICAL);
        parent.addView(line, new LinearLayout.LayoutParams(-1, -2)); return line;
    }

    private TextView key(LinearLayout parent, String label, float weight, boolean special, Runnable action, int height) {
        KeyboardKey button = new KeyboardKey(this); button.setText(label); button.setTextColor(fg); button.setTextSize(label.length() > 2 && !label.contains("\n") ? 13 : 22);
        button.setGravity(Gravity.CENTER); button.setIncludeFontPadding(false); button.setMaxLines(2); button.setSingleLine(false);
        button.setBackground(background(special ? functionColor : keyColor)); button.setFocusable(true);
        switch (label) {
            case "☺": button.icon("emoji"); break;
            case "⌫": button.icon("delete"); break;
            case "⇧": case "⇪": button.icon("shift"); if (shift || caps) button.setTextColor(accent); break;
            case "🌐": button.icon("globe"); break;
            case "⌄": button.icon("hide"); break;
            case "⚙": button.icon("settings"); break;
            case "↵": button.icon("enter"); break;
            case "␣": button.icon("space"); break;
        }
        button.setElevation(dp(1));
        button.setOnClickListener(v -> { if (prefs.getBoolean("haptic", true)) v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP); action.run(); });
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(height), weight); params.setMargins(dp(2), dp(3), dp(2), dp(3));
        parent.addView(button, params); return button;
    }

    private android.graphics.drawable.Drawable background(int color) {
        GradientDrawable shape = new GradientDrawable(); shape.setColor(color); shape.setCornerRadius(dp(7));
        return new android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(dark ? 0x40FFFFFF : 0x22000000), shape, null);
    }

    private int keyHeight() {
        return getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE && !splitLayout() ? 40 : Integer.parseInt(prefs.getString("height", "50"));
    }
    private void splitGap(LinearLayout line) {
        line.addView(new View(this), new LinearLayout.LayoutParams(dp(Math.min(80,getResources().getConfiguration().screenWidthDp * .085f)), 1));
    }
    private boolean splitLayout() {
        return prefs.getBoolean("split", true) && prefs.getString("hand", "full").equals("full")
            && getResources().getConfiguration().screenWidthDp >= 600;
    }
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
