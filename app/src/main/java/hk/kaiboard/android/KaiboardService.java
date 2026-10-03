package hk.kaiboard.android;

import android.content.*;
import android.Manifest;
import android.content.pm.PackageManager;
import android.speech.*;
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
    private SpeechRecognizer voiceRecognizer;
    private boolean voiceListening;
    private int voiceSession;
    private SharedPreferences prefs;
    private SharedPreferences learned;
    private boolean noLearning;
    private LinearLayout root, panel, candidateRow;
    private HorizontalScrollView candidateScroll;
    private TextView raw, nextPage, firstToggle, codePreview, selectKey;
    private boolean chooseFirst, expanded, emojiSearch;
    private String emojiQuery = "";
    private LinearLayout toolbar, candidateBar;
    private TextView emojiSearchLabel;
    private BaseAdapter emojiAdapter;
    private EmojiBrowserModel emojiModel;
    private ListView emojiList;
    private final android.util.SparseArray<TextView> emojiTabs = new android.util.SparseArray<>();
    private HorizontalScrollView emojiCategories;
    private PopupWindow tonePopup;
    private int emojiColumns;
    private int emojiGroup;
    private final Map<String, Integer> consumedCodes = new HashMap<>();
    private final StringBuilder composing = new StringBuilder();
    private List<String> candidates = Collections.emptyList();
    private int candidatePage, bg, keyColor, functionColor, fg, muted, accent;
    private boolean secure, numeric, directField, ascii, shift, caps, symbols, emoji, aiHelp;
    private boolean extraSymbols;
    private boolean quick, cangjie, english, dark;
    private static final int PAGE_SIZE = 7;
    private static final String RADICALS = "日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重";

    @Override public void onCreate() {
        super.onCreate(); prefs = Prefs.get(this); learned = getSharedPreferences("learned", MODE_PRIVATE);
        loader.execute(() -> {
            try {
                DictionaryEngine loaded = new DictionaryEngine(
                    new InputStreamReader(getAssets().open("cangjie5.base.dict.yaml"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("english.txt"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("character_frequencies.tsv"), StandardCharsets.UTF_8));
                QuickDecoder phrases = new QuickDecoder(loaded, new InputStreamReader(getAssets().open("quick_phrases.tsv"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("hk_phrases.tsv"), StandardCharsets.UTF_8));
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
        cancelVoice(); resetComposition(); stopRepeat();
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
        cancelVoice();
        if (tonePopup != null) tonePopup.dismiss();
        stopRepeat(); finishLiteral(); super.onFinishInputView(finishingInput);
    }

    @Override public void onFinishInput() {
        cancelVoice(); stopRepeat(); resetComposition(); updateCandidates(); super.onFinishInput();
    }

    @Override public void onDestroy() {
        destroyed = true; cancelVoice(); stopRepeat(); handler.removeCallbacksAndMessages(null); loader.shutdownNow(); super.onDestroy();
    }

    private void colors() {
        String theme = prefs.getString("theme", "system");
        dark = theme.equals("dark") || theme.equals("system") &&
            (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        bg = Color.parseColor(dark ? "#181A1F" : "#D1D2D7");
        keyColor = Color.parseColor(dark ? "#34373D" : "#FFFFFF");
        functionColor = Color.parseColor(dark ? "#494D55" : "#BFC5CE");
        fg = Color.parseColor(dark ? "#F5F6F8" : "#272D36");
        muted = Color.parseColor(dark ? "#C5CAD3" : "#535D6D");
        accent = Color.parseColor(dark ? "#AFC8FC" : "#087CF0");
    }

    private void render() {
        if (root == null) return;
        if (tonePopup != null) { tonePopup.dismiss(); tonePopup = null; }
        stopRepeat(); colors(); candidateRow = null; raw = null; nextPage = null; firstToggle = null; codePreview = null;
        quick = prefs.getBoolean("quick", true); cangjie = prefs.getBoolean("cangjie", true); english = prefs.getBoolean("english", true);
        root.removeAllViews(); root.setBackgroundColor(bg); root.setPadding(dp(splitLayout() ? 14 : 4), dp(5), dp(splitLayout() ? 14 : 4), dp(6));
        LinearLayout dock = row(root);
        String hand = prefs.getString("hand", "full");
        if (hand.equals("right")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));
        panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL);
        dock.addView(panel, new LinearLayout.LayoutParams(0, -2, hand.equals("full") ? 1 : .82f));
        if (hand.equals("left")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));

        toolbar = row(panel);
        tool(toolbar, "emoji", "Emoji", () -> { if (!secure && !numeric) { finishLiteral(); emoji = !emoji; emojiSearch = false; emojiQuery = ""; render(); } }, emoji);
        tool(toolbar, "language", "中英輸入模式", () -> { if (!secure && !numeric) { finishLiteral(); ascii = !ascii; render(); } }, ascii);
        tool(toolbar, "clipboard", "貼上剪貼簿", () -> {
            if (secure) return;
            android.content.ClipboardManager cb = (android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
            if (cb.hasPrimaryClip() && cb.getPrimaryClip() != null && cb.getPrimaryClip().getItemCount() > 0) {
                CharSequence text = cb.getPrimaryClip().getItemAt(0).coerceToText(this);
                if (text != null) insert(text.toString());
            }
        }, false);
        tool(toolbar, "keyboard", "選擇鍵盤", this::picker, false);
        tool(toolbar, "pen", "切換系統鍵盤使用手寫", () -> systemTool("手寫"), false);
        tool(toolbar, "mic", voiceListening ? "停止語音輸入" : "語音輸入", this::voice, voiceListening);
        tool(toolbar, "more", "鍵盤設定", () -> {
            finishLiteral(); startActivity(new Intent(this, SettingsActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        }, false);
        if (emoji) { renderEmoji(); return; }

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
        LinearLayout bar = row(panel); candidateBar = bar;
        raw = key(bar, "英文", 1.35f, true, this::finishLiteral, 42);
        raw.setTextSize(13);
        candidateScroll = new HorizontalScrollView(this); candidateScroll.setHorizontalScrollBarEnabled(false); candidateScroll.setFillViewport(false);
        candidateScroll.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        candidateRow = new LinearLayout(this); candidateRow.setOrientation(LinearLayout.HORIZONTAL);
        candidateScroll.addView(candidateRow, new HorizontalScrollView.LayoutParams(-2, -1)); bar.addView(candidateScroll, new LinearLayout.LayoutParams(0, dp(48), 6));
        firstToggle = key(bar, "逐字", 1.15f, true, () -> { chooseFirst = !chooseFirst; updateCandidates(); }, 42);
        nextPage = key(bar, "⌄", .65f, true, () -> { expanded = !expanded; render(); }, 43);
        nextPage.setContentDescription("展開或收起候選字"); updateCandidates();

        if (expanded && !candidates.isEmpty()) {
            renderExpandedCandidates();
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
        TextView select = key(bottom, composing.length() > 0 ? "選字" : "速成", 1, true, () -> {
            if (composing.length() > 0) selectCandidate(); else picker();
        }, keyHeight());
        selectKey = select; select.setTextSize(14); select.setSingleLine(true);
        select.setContentDescription("選取本頁第一個候選字；沒有字碼時切換鍵盤");
        if (!numeric) {
            TextView space = key(bottom, "", splitLayout() ? 6.4f : 3.6f, false, this::space, keyHeight());
            ((KeyboardKey) space).icon("space");
            space.setContentDescription("空白鍵，左右滑動移動游標"); attachSpaceGesture(space);
            key(bottom, ascii ? "," : "，", .9f, false, () -> insert(ascii ? "," : "，"), keyHeight());
            key(bottom, ascii ? "." : "。", .9f, false, () -> insert(ascii ? "." : "。"), keyHeight());
        }
        if (symbols || emoji || numeric) deleteKey(bottom, 1.2f);
        TextView enterKey = key(bottom, enterLabel(), 1.45f, true, this::enter, keyHeight());
        enterKey.setBackground(background(functionColor));
        enterKey.setTextColor(fg); enterKey.setTextSize(14); enterKey.setSingleLine(true);
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
        if(!ascii && !emojiSearch && (quick||cangjie)) ((KeyboardKey)button).legend(latin,String.valueOf(RADICALS.charAt(letter-'a')),muted);
    }

    private void typeLetter(char lower) {
        if (voiceListening) { cancelVoice(); render(); }
        if (emojiSearch) { emojiQuery += lower; refreshEmoji(); return; }
        String value = String.valueOf(shift || caps ? Character.toUpperCase(lower) : lower);
        if (secure || ascii) insert(value);
        else {
            if (composing.length() >= 48) selectCandidate();
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
        if(selectKey!=null) selectKey.setText(composing.length()>0?"選字":"速成");
        raw.setEnabled(composing.length() > 0);
        raw.setAlpha(composing.length() > 0 ? 1f : .45f);
        if (toolbar != null) toolbar.setVisibility(composing.length() == 0 ? View.VISIBLE : View.GONE);
        if (candidateBar != null) candidateBar.setVisibility(composing.length() == 0 ? View.GONE : View.VISIBLE);
        if (codePreview != null) codePreview.setVisibility(composing.length() == 0 ? View.GONE : View.VISIBLE);
        if (codePreview != null) codePreview.setText(composing.length() == 0 ? secure ? "密碼輸入" : loadFailed ? "字庫載入失敗" : dictionary == null ? "載入字庫…" : ascii ? "English" : "速成  ·  倉頡  ·  English" :
            (chooseFirst ? "逐字選取   " : "") + composing.toString().toUpperCase(Locale.ROOT));
        if (firstToggle != null) { firstToggle.setText(chooseFirst ? "整句" : "逐字"); firstToggle.setVisibility(quick && prefs.getBoolean("continuous",true) && composing.length() > 2 ? View.VISIBLE : View.GONE); }
        if (candidates.isEmpty()) { nextPage.setVisibility(View.GONE); return; }
        int pages = (candidates.size() + PAGE_SIZE - 1) / PAGE_SIZE;
        candidatePage %= pages;
        for (int i = 0; i < candidates.size(); i++) {
            String value = candidates.get(i);
            TextView item = new TextView(this); item.setText(value); item.setTextSize(23); item.setTextColor(fg);
            item.setGravity(Gravity.CENTER); item.setPadding(dp(8), 0, dp(8), 0); item.setMinWidth(dp(32)); item.setSingleLine(true);
            item.setContentDescription(value + (chooseFirst ? "，先輸入此字並保留後續字碼" : ""));
            if (i == candidatePage * PAGE_SIZE) { item.setTextColor(accent); item.setTypeface(null, Typeface.BOLD); }
            item.setBackgroundColor(Color.TRANSPARENT); item.setOnClickListener(v -> commit(value));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, dp(42)); params.setMargins(dp(3), dp(3), dp(3), dp(3));
            candidateRow.addView(item, params);
        }
        nextPage.setVisibility(View.VISIBLE);
        nextPage.setText((candidatePage + 1) + "/" + pages + (expanded ? "⌃" : "⌄")); nextPage.setTextSize(11);
        final int first = candidatePage * PAGE_SIZE;
        candidateScroll.post(() -> {
            if (first < candidateRow.getChildCount()) candidateScroll.scrollTo(candidateRow.getChildAt(first).getLeft(), 0);
        });
    }

    private void space() {
        if (emojiSearch) { emojiQuery += " "; refreshEmoji(); return; }
        if (composing.length() > 0 && !candidates.isEmpty()) { candidatePage++; displayCandidates(); }
        else if (composing.length() > 0) finishLiteral();
        else insert(" ");
    }

    private void selectCandidate() {
        if (!candidates.isEmpty()) commit(candidates.get(Math.min(candidatePage * PAGE_SIZE, candidates.size() - 1)));
        else finishLiteral();
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
        expanded = false;
        render();
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
        cancelVoice();
        finishLiteral(); InputConnection ic = getCurrentInputConnection(); if (ic != null) ic.commitText(text, 1);
    }

    private void delete() {
        if (voiceListening) { cancelVoice(); render(); }
        if (emojiSearch) { if (!emojiQuery.isEmpty()) emojiQuery = emojiQuery.substring(0, emojiQuery.length()-1); refreshEmoji(); return; }
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        if (composing.length() > 0) {
            composing.deleteCharAt(composing.length() - 1);
            if (composing.length() == 0) { ic.commitText("", 1); ic.finishComposingText(); }
            else ic.setComposingText(composing, 1);
            if(expanded){expanded=false;render();}else updateCandidates();
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
        if (info == null || (info.imeOptions & EditorInfo.IME_FLAG_NO_ENTER_ACTION) != 0) return "換行";
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
        if (emojiSearch) { emojiSearch = false; render(); return; }
        if (composing.length() > 0) { finishLiteral(); return; }
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        if (!sendDefaultEditorAction(true)) ic.commitText("\n", 1);
    }

    private void picker() { cancelVoice(); finishLiteral(); ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker(); }
    private void resetComposition() { expanded = false; emojiSearch = false; emojiQuery = ""; composing.setLength(0); candidates = Collections.emptyList(); consumedCodes.clear(); candidatePage = 0; chooseFirst = false; }
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

    private void cancelVoice() {
        voiceSession++;
        voiceListening = false;
        if (voiceRecognizer != null) {
            voiceRecognizer.cancel(); voiceRecognizer.destroy(); voiceRecognizer = null;
        }
    }

    private void voice() {
        if (voiceListening) { cancelVoice(); render(); return; }
        if (secure || numeric || getCurrentInputConnection() == null) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            startActivity(new Intent(this, VoicePermissionActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Toast.makeText(this, "手機未有可用嘅語音辨識服務", Toast.LENGTH_LONG).show(); return;
        }
        finishLiteral();
        final int session = ++voiceSession;
        final InputConnection editor = getCurrentInputConnection();
        voiceRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        voiceListening = true;
        voiceRecognizer.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle params) {
                if (session == voiceSession) Toast.makeText(KaiboardService.this, "請講嘢；再撳咪可取消", Toast.LENGTH_SHORT).show();
            }
            @Override public void onBeginningOfSpeech() {}
            @Override public void onRmsChanged(float rms) {}
            @Override public void onBufferReceived(byte[] buffer) {}
            @Override public void onEndOfSpeech() {}
            @Override public void onPartialResults(Bundle results) {}
            @Override public void onEvent(int type, Bundle params) {}
            @Override public void onError(int error) {
                if (session != voiceSession) return;
                cancelVoice(); render();
                String message = error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ? "請允許咪高峰權限" :
                    error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT ? "未聽清楚，請再試" :
                    "語音辨識暫時未能使用，請檢查辨識服務、語言及網絡";
                Toast.makeText(KaiboardService.this, message, Toast.LENGTH_LONG).show();
            }
            @Override public void onResults(Bundle results) {
                if (session != voiceSession) return;
                ArrayList<String> texts = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                boolean sameEditor = editor == getCurrentInputConnection() && isInputViewShown() && !secure;
                cancelVoice();
                if (sameEditor && texts != null && !texts.isEmpty()) insert(texts.get(0));
                render();
            }
        });
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, ascii ? "en-HK" : "yue-HK");
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        try { voiceRecognizer.startListening(intent); render(); }
        catch (RuntimeException exception) {
            cancelVoice(); render();
            Toast.makeText(this, "未能啟動語音辨識服務", Toast.LENGTH_LONG).show();
        }
    }

    private void systemTool(String name) {
        Toast.makeText(this, "請選擇 Samsung Keyboard，再使用" + name + "功能", Toast.LENGTH_LONG).show();
        picker();
    }

    private void tool(LinearLayout parent, String icon, String label, Runnable action, boolean selected) {
        KeyboardKey button = new KeyboardKey(this); button.icon(icon);
        button.setTextColor(selected ? accent : muted); button.setContentDescription(label);
        button.setBackground(selected ? background(dark ? 0xFF344760 : 0xFFB8CBE0) : background(bg));
        button.setOnClickListener(v -> { if (voiceListening && !icon.equals("mic")) cancelVoice(); action.run(); });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,dp(44),1);
        lp.setMargins(dp(3),dp(3),dp(3),dp(3)); parent.addView(button,lp);
    }

    private void renderExpandedCandidates() {
        ScrollView scroll = new ScrollView(this);
        android.widget.GridLayout grid = new android.widget.GridLayout(this); grid.setColumnCount(5);
        for (String value : candidates) {
            TextView item = new TextView(this); item.setText(value); item.setTextSize(21); item.setTextColor(fg);
            item.setGravity(Gravity.CENTER); item.setPadding(dp(5),dp(10),dp(5),dp(10));
            android.widget.GridLayout.LayoutParams lp = new android.widget.GridLayout.LayoutParams();
            lp.width = 0; lp.columnSpec = android.widget.GridLayout.spec(android.widget.GridLayout.UNDEFINED,1f);
            grid.addView(item,lp); item.setOnClickListener(v -> commit(value));
        }
        scroll.addView(grid); panel.addView(scroll,new LinearLayout.LayoutParams(-1,dp(210)));
    }

    private String recentEmoji() {
        return noLearning || !prefs.getBoolean("emoji_recent",true) ? "" : prefs.getString("recent_emoji","");
    }

    private void refreshEmoji() {
        if (emojiCatalog == null) return;
        emojiModel = new EmojiBrowserModel(emojiCatalog,emojiColumns,recentEmoji(),emojiQuery);
        if (emojiSearchLabel != null) emojiSearchLabel.setText("⌕  " + (emojiQuery.isEmpty() ? "搜尋 Emoji（英文名稱）" : emojiQuery));
        if (emojiAdapter != null) emojiAdapter.notifyDataSetChanged();
        if (emojiList != null) emojiList.setSelection(0);
    }

    private void highlightEmojiGroup(int group) {
        emojiGroup=group;
        for(int i=0;i<emojiTabs.size();i++) {
            TextView tab=emojiTabs.valueAt(i); boolean selected=emojiTabs.keyAt(i)==group;
            tab.setTextColor(selected?accent:muted); tab.setSelected(selected);
        }
        TextView tab=emojiTabs.get(group);
        if(tab!=null && emojiCategories!=null) {
            int left=tab.getLeft(),right=tab.getRight(),offset=emojiCategories.getScrollX();
            if(left<offset || right>offset+emojiCategories.getWidth())
                emojiCategories.smoothScrollTo(Math.max(0,left-emojiCategories.getWidth()/2+tab.getWidth()/2),0);
        }
    }

    private void commitEmoji(String symbol) {
        InputConnection ic=getCurrentInputConnection(); if(ic==null || !ic.commitText(symbol,1)) return;
        if(!noLearning && prefs.getBoolean("emoji_recent",true))
            prefs.edit().putString("recent_emoji",emojiCatalog.remember(recentEmoji(),symbol)).apply();
    }

    private boolean showSkinTones(View anchor, EmojiCatalog.Entry entry) {
        List<EmojiCatalog.Entry> variants=emojiCatalog.skinVariants(entry.symbol);
        if(variants.size()<2) return false;
        if(tonePopup!=null) tonePopup.dismiss();
        android.widget.GridLayout choices=new android.widget.GridLayout(this);choices.setColumnCount(6);
        choices.setPadding(dp(4),dp(4),dp(4),dp(4)); choices.setBackground(background(keyColor));
        for(EmojiCatalog.Entry variant:variants) {
            TextView choice=new TextView(this); choice.setText(variant.symbol);choice.setTextSize(27);
            choice.setGravity(Gravity.CENTER);choice.setTextColor(fg);choice.setContentDescription(variant.name);
            choices.addView(choice,new android.view.ViewGroup.LayoutParams(dp(44),dp(48)));
            choice.setOnClickListener(v->{commitEmoji(variant.symbol);if(tonePopup!=null)tonePopup.dismiss();});
        }
        ScrollView scroll=new ScrollView(this);scroll.addView(choices);
        // Keep the editor's input connection active while choosing a tone.
        tonePopup=new PopupWindow(scroll,dp(272),dp(Math.min(200,8+48*((variants.size()+5)/6))),false);
        tonePopup.setInputMethodMode(PopupWindow.INPUT_METHOD_NOT_NEEDED);
        tonePopup.setBackgroundDrawable(background(keyColor));tonePopup.setOutsideTouchable(true);tonePopup.setElevation(dp(8));
        tonePopup.showAsDropDown(anchor,0,-anchor.getHeight()-tonePopup.getHeight());
        anchor.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
        return true;
    }

    private void renderEmoji() {
        if (emojiCatalog == null) {
            TextView loading = new TextView(this); loading.setText("載入 Emoji…"); loading.setTextColor(fg); panel.addView(loading); return;
        }
        int width=getResources().getConfiguration().screenWidthDp;
        if(!prefs.getString("hand","full").equals("full")) width=(int)(width*.82f);
        emojiColumns=Math.max(5,(width-16)/38); emojiTabs.clear();
        emojiSearchLabel = new TextView(this); emojiSearchLabel.setTextSize(17); emojiSearchLabel.setTextColor(muted);
        emojiSearchLabel.setGravity(Gravity.CENTER_VERTICAL); emojiSearchLabel.setPadding(dp(12),0,dp(12),0);
        GradientDrawable searchBg = new GradientDrawable(); searchBg.setColor(dark ? 0xFF34373D : 0xFFB9BBC2); searchBg.setCornerRadius(dp(22));
        emojiSearchLabel.setBackground(searchBg);
        LinearLayout.LayoutParams searchLp = new LinearLayout.LayoutParams(-1,dp(38)); searchLp.setMargins(dp(8),dp(8),dp(8),dp(12));
        panel.addView(emojiSearchLabel, searchLp);
        emojiSearchLabel.setOnClickListener(v -> { emojiSearch = !emojiSearch; render(); });
        emojiList=new ListView(this);emojiList.setDivider(null);emojiList.setDividerHeight(0);
        emojiList.setVerticalScrollBarEnabled(true);emojiList.setPadding(dp(3),0,dp(3),0);
        emojiModel=new EmojiBrowserModel(emojiCatalog,emojiColumns,recentEmoji(),emojiQuery);
        emojiAdapter=new BaseAdapter() {
            @Override public int getCount(){return emojiModel.rows.size();}
            @Override public Object getItem(int p){return emojiModel.rows.get(p);}
            @Override public long getItemId(int p){return p;}
            @Override public boolean areAllItemsEnabled(){return false;}
            @Override public boolean isEnabled(int p){return false;}
            @Override public View getView(int position,View recycled,android.view.ViewGroup parent) {
                EmojiBrowserModel.Row model=emojiModel.rows.get(position);
                if(model.heading) {
                    TextView title=new TextView(KaiboardService.this);title.setText(model.group<0?"最近使用":EmojiCatalog.LABELS[model.group]);
                    title.setTextColor(muted);title.setTextSize(12);title.setPadding(dp(8),dp(6),0,dp(3));
                    if(android.os.Build.VERSION.SDK_INT>=28)title.setAccessibilityHeading(true);return title;
                }
                LinearLayout line=new LinearLayout(KaiboardService.this);
                for(int col=0;col<emojiColumns;col++) {
                    TextView cell=new TextView(KaiboardService.this);cell.setTextSize(27);cell.setTextColor(fg);cell.setGravity(Gravity.CENTER);
                    line.addView(cell,new LinearLayout.LayoutParams(0,dp(48),1));
                    if(col>=model.entries.size()) continue;
                    EmojiCatalog.Entry entry=model.entries.get(col);cell.setText(entry.symbol);cell.setContentDescription(entry.name);
                    cell.setOnClickListener(v->{commitEmoji(entry.symbol);if(prefs.getBoolean("haptic",true))v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);});
                    cell.setOnLongClickListener(v->showSkinTones(v,entry));
                }
                return line;
            }
        };
        emojiList.setAdapter(emojiAdapter);
        TextView empty=new TextView(this);empty.setText("沒有符合的 Emoji");empty.setTextColor(muted);empty.setGravity(Gravity.CENTER);
        panel.addView(empty,new LinearLayout.LayoutParams(-1,dp(40)));emojiList.setEmptyView(empty);
        panel.addView(emojiList,new LinearLayout.LayoutParams(-1,dp(emojiSearch?92:206)));
        if(emojiSearch){letters("qwertyuiop",false);letters("asdfghjkl",false);letters("zxcvbnm",true);}
        LinearLayout bottom=row(panel);
        TextView abc=key(bottom,"ABC",1.3f,false,()->{emoji=false;emojiSearch=false;emojiQuery="";render();},42);
        abc.setBackgroundColor(Color.TRANSPARENT);abc.setElevation(0);abc.setTextSize(16);
        emojiCategories=new HorizontalScrollView(this);emojiCategories.setHorizontalScrollBarEnabled(false);
        LinearLayout tabs=new LinearLayout(this);emojiCategories.addView(tabs);
        bottom.addView(emojiCategories,new LinearLayout.LayoutParams(0,dp(44),7));
        String[] marks={"recent","emoji","person","animal","food","car","ball","bulb","symbols","flag"};
        for(int i=-1;i<emojiCatalog.groupCount();i++) {
            final int group=i;KeyboardKey category=new KeyboardKey(this);category.icon(marks[i+1]);
            category.setTextColor(muted);category.setGravity(Gravity.CENTER);category.setContentDescription(i<0?"最近使用":EmojiCatalog.LABELS[i]);
            tabs.addView(category,new LinearLayout.LayoutParams(dp(Math.max(24,(width-16)*7/95)),dp(44)));emojiTabs.put(group,category);
            category.setOnClickListener(v->{
                if(!emojiQuery.isEmpty()){emojiQuery="";refreshEmoji();}
                Integer position=emojiModel.starts.get(group);
                if(position!=null){emojiList.setSelection(position);highlightEmojiGroup(group);}
            });
        }
        deleteKey(bottom,1.2f);
        emojiList.setOnScrollListener(new AbsListView.OnScrollListener(){
            @Override public void onScrollStateChanged(AbsListView view,int state){}
            @Override public void onScroll(AbsListView view,int first,int count,int total){
                if(total>0)highlightEmojiGroup(emojiModel.groupAt(first));
            }
        });
        emojiSearchLabel.setText("⌕  "+(emojiQuery.isEmpty()?"搜尋 Emoji（英文名稱）":emojiQuery));
        Integer initial=emojiModel.starts.get(emojiGroup);if(initial!=null)emojiList.setSelection(initial);
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
        button.setOnClickListener(v -> { if (voiceListening) cancelVoice(); if (prefs.getBoolean("haptic", true)) v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP); action.run(); });
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



