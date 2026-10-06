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
    private boolean strokeMode;
    private final StringBuilder strokeCode = new StringBuilder();
    private StrokePanel strokePanel;
    private void closeStroke() { if(strokePanel!=null){strokePanel.close();strokePanel=null;} }
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService loader = Executors.newSingleThreadExecutor();
    private final ScheduledExecutorService candidateWorker = Executors.newSingleThreadScheduledExecutor();
    private Future<?> pendingCandidates;
    private final ScheduledThreadPoolExecutor semanticWorker = new ScheduledThreadPoolExecutor(1);
    private Future<?> pendingSemantic;
    private SemanticRanker semanticRanker;
    private volatile int semanticFrozenGeneration = -1;
    private boolean editMode;
    private boolean clipboardMode, quickTextMode, expandNextCandidates;
    private final SessionClipboard sessionClipboard = new SessionClipboard();
    private final Runnable clipboardExpiry = this::expireClipboard;
    private void expireClipboard() {
        sessionClipboard.items();
        if (clipboardMode && root != null && !destroyed) render();
        else scheduleClipboardExpiry();
    }
    private void scheduleClipboardExpiry() {
        handler.removeCallbacks(clipboardExpiry);
        long age;
        try { age = Long.parseLong(prefs.getString("clipboard_clear_ms", "300000")); }
        catch (NumberFormatException invalid) { age = 300000; }
        sessionClipboard.setMaxAgeMillis(age);
        long delay = sessionClipboard.nextExpiryMillis();
        if (delay >= 0 && !destroyed) handler.postDelayed(clipboardExpiry, delay);
    }
    private TextView customTool;
    private void clearClipboardSession() {
        handler.removeCallbacks(clipboardExpiry);
        if (clipboardMode && root != null) root.removeAllViews();
        clipboardMode = false; quickTextMode = false; expandNextCandidates = false;
        sessionClipboard.clear();
    }
    private final TextEditorController textEditor = new TextEditorController();
    private final SwipeSelectionController swipeSelection = new SwipeSelectionController();
    private TextView editorSelect;
    private Runnable editingAction;
    private final java.util.concurrent.atomic.AtomicInteger candidateGeneration = new java.util.concurrent.atomic.AtomicInteger();
    private DictionaryEngine dictionary;
    private QuickDecoder decoder;
    private EnglishEngine englishEngine;
    private EnglishChineseEngine englishChineseEngine;
    private CandidateEngine candidateEngine;
    private QuickTypos quickTypos;
    private SharedPreferences personal, englishLearned;
    private final Map<String, InputCandidate> candidateDetails = new HashMap<>();
    private List<InputCandidate> corrections = Collections.emptyList();
    private InputCandidate autoUndo;
    private int autoUndoCursor = -1;
    private String autoUndoBefore = "", rejectedAutoCode = "";
    private boolean forceEnglish, forceChinese, reselectionLearned;
    private List<String> reselectionPhrases = Collections.emptyList();
        private TextView undoKey;
    private PopupWindow selectionPopup;
    private ReselectionRecord reselection;
    private InputCandidate restoredCandidate;
    private int selectionStart = -1, selectionEnd = -1;
    private EmojiCatalog emojiCatalog;
    private boolean loadFailed, destroyed;
    private SpeechRecognizer voiceRecognizer;
    private boolean voiceListening;
    private int voiceSession;
    private android.app.AlertDialog voiceDialog;
    private Runnable voiceSupportTimeout;
    private SharedPreferences prefs;
    private SharedPreferences learned;
    private boolean noLearning;
    private LinearLayout root, panel, candidateRow;
    private int navigationLeft, navigationRight, navigationBottom;
    private final int[] keyboardLocation = new int[2];
    private HorizontalScrollView candidateScroll;
    private ScrollView expandedScroll;
    private TextView codeLabel, expandedMode, nextPage, selectKey;
    private boolean chooseFirst, expanded, emojiSearch;
    private boolean nextSuggestionsDismissed;
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
    private boolean secure, numeric, directField, uriField, ascii, shift, caps, symbols, emoji, aiHelp;
    private boolean extraSymbols;
    private boolean quick, cangjie, english, dark;
    private static final int PAGE_SIZE = 7;
    private static final String RADICALS = "日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重";

    @Override public void onCreate() {
        super.onCreate(); prefs = Prefs.get(this); learned = getSharedPreferences("learned", MODE_PRIVATE);
        semanticWorker.setRemoveOnCancelPolicy(true);
        semanticRanker = new SemanticRanker(this);
        personal = getSharedPreferences("personal", MODE_PRIVATE);
        englishLearned = getSharedPreferences("english_learned", MODE_PRIVATE);
        loader.execute(() -> {
            try {
                DictionaryEngine loaded = new DictionaryEngine(
                    new InputStreamReader(getAssets().open("cangjie5.base.dict.yaml"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("english.txt"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("character_frequencies.tsv"), StandardCharsets.UTF_8));
                EnglishEngine englishWords = new EnglishEngine(new InputStreamReader(getAssets().open("english.txt"), StandardCharsets.UTF_8));
                EnglishChineseEngine meanings = EnglishChineseEngine.load(getAssets().open("english_chinese.b64"));
                // Exact Cangjie/Quick and English are usable before the large sentence model loads.
                handler.post(() -> { if (!destroyed) {
                    dictionary = loaded; englishEngine = englishWords; englishChineseEngine = meanings; updateCandidates();
                } });
                QuickDecoder phrases = new QuickDecoder(loaded, new InputStreamReader(getAssets().open("quick_phrases.tsv"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("hk_phrases.tsv"), StandardCharsets.UTF_8),
                    new InputStreamReader(getAssets().open("cantonese_phrases.tsv"), StandardCharsets.UTF_8),
                    OfflineLanguageModel.load(getAssets().open("language_model.b64")));
                EmojiCatalog emojis = new EmojiCatalog(new InputStreamReader(getAssets().open("emoji.tsv"), StandardCharsets.UTF_8));
                CandidateEngine mixed = new CandidateEngine(loaded, phrases, englishWords);
                QuickTypos repairs = new QuickTypos(loaded, phrases);
                handler.post(() -> { if (!destroyed) { dictionary = loaded; decoder = phrases; emojiCatalog = emojis;
                    englishEngine = englishWords; candidateEngine = mixed; quickTypos = repairs;
                    if (emoji) render(); else updateCandidates(); } });
            } catch (IOException e) {
                handler.post(() -> { if (!destroyed) { loadFailed = true; updateCandidates(); } });
            }
        });
    }

    @Override public View onCreateInputView() {
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            updateKeyboardPadding();
            return insets;
        });
        root.getViewTreeObserver().addOnGlobalLayoutListener(this::updateKeyboardPadding);
        render(); root.requestApplyInsets(); return root;
    }

    private void updateKeyboardPadding() {
        if (root == null) return;
        // The framework can consume insets before dispatching them to the input view.
        // Read the IME window's raw insets on each layout, including navigation mode changes.
        WindowInsets windowInsets = getWindow() == null ? null :
            getWindow().getWindow().getDecorView().getRootWindowInsets();
        if (windowInsets != null) {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets safe = windowInsets.getInsets(WindowInsets.Type.navigationBars() |
                    WindowInsets.Type.captionBar() | WindowInsets.Type.displayCutout());
                navigationLeft = safe.left; navigationRight = safe.right; navigationBottom = safe.bottom;
            } else {
                navigationLeft = windowInsets.getSystemWindowInsetLeft();
                navigationRight = windowInsets.getSystemWindowInsetRight();
                navigationBottom = windowInsets.getSystemWindowInsetBottom();
            }
        }
        int side = dp(splitLayout() ? Math.round(foldWidth() * .041f) : 4);
        int left = 0, right = 0, bottom = 0;
        if (root.isAttachedToWindow() && root.getHeight() > 0) {
            android.util.DisplayMetrics display = new android.util.DisplayMetrics();
            root.getDisplay().getRealMetrics(display);
            root.getLocationOnScreen(keyboardLocation);
            // Some IME windows already stop above the navigation bar. Add only the overlap.
            left = Math.max(0, navigationLeft - Math.max(0, keyboardLocation[0]));
            right = Math.max(0, navigationRight - Math.max(0,
                display.widthPixels - keyboardLocation[0] - root.getWidth()));
            bottom = Math.max(0, navigationBottom - Math.max(0,
                display.heightPixels - keyboardLocation[1] - root.getHeight()));
        }
        int top = dp(5), baseBottom = dp(6);
        if (root.getPaddingLeft() != side + left || root.getPaddingRight() != side + right ||
                root.getPaddingTop() != top || root.getPaddingBottom() != baseBottom + bottom) {
            if ((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) android.util.Log.d("KeyboardInsets", "navigationBottom=" +
                navigationBottom + " clearancePadding=" + bottom + " rootY=" + keyboardLocation[1] +
                " rootHeight=" + root.getHeight());
            root.setPadding(side + left, top, side + right, baseBottom + bottom);
        }
    }

    @Override public void onStartInput(EditorInfo info, boolean restarting) {
        cancelSemantic();
        super.onStartInput(info, restarting); resolvedCandidates = null; swipeSelection.reset();
        nextSuggestionsDismissed = false;
        clearClipboardSession();
        cancelVoice(); dismissSelectionPopup(); invalidateReselection(); resetComposition(); stopRepeat();
        closeStroke(); strokeMode = false; strokeCode.setLength(0); editMode = false; textEditor.reset();
        selectionStart = info.initialSelStart; selectionEnd = info.initialSelEnd;
        int type = info.inputType & InputType.TYPE_MASK_CLASS;
        int variation = info.inputType & InputType.TYPE_MASK_VARIATION;
        secure = InputPolicy.isSecure(info.inputType);
        noLearning = InputPolicy.noLearning(info.inputType, info.imeOptions);
        numeric = type == InputType.TYPE_CLASS_NUMBER || type == InputType.TYPE_CLASS_PHONE || type == InputType.TYPE_CLASS_DATETIME;
        uriField = type == InputType.TYPE_CLASS_TEXT && variation == InputType.TYPE_TEXT_VARIATION_URI;
        directField = secure || numeric || type == InputType.TYPE_NULL || type == InputType.TYPE_CLASS_TEXT &&
            (variation == InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS || variation == InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS);
        if (!restarting || secure || numeric || uriField) ascii = directField; shift = false; caps = false; symbols = false; extraSymbols = false; emoji = false; aiHelp = false; chooseFirst = false;
    }

    @Override public void onStartInputView(EditorInfo info, boolean restarting) {
        super.onStartInputView(info, restarting); render();
    }

    @Override public boolean onEvaluateFullscreenMode() { return false; }

    @Override public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && (selectionPopup != null || editMode || strokeMode || clipboardMode || quickTextMode)) {
            event.startTracking();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override public boolean onKeyUp(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && (selectionPopup != null || editMode || strokeMode || clipboardMode || quickTextMode)) {
            if (!event.isCanceled()) { if (clipboardMode || quickTextMode) { clipboardMode = quickTextMode = false; render(); } else if (strokeMode) { strokeMode = false; strokeCode.setLength(0); render(); } else if (editMode) { editMode = false; textEditor.reset(); render(); } else dismissSelectionPopup(); }
            return true;
        }
        return super.onKeyUp(keyCode, event);
    }

    @Override public void onUpdateSelection(int oldStart, int oldEnd, int start, int end, int composingStart, int composingEnd) {
        super.onUpdateSelection(oldStart, oldEnd, start, end, composingStart, composingEnd);
        selectionStart = start; selectionEnd = end;
        if (reselection != null && (start != reselection.cursor || end != reselection.cursor) && !canReselect()) invalidateReselection();
        if (composing.length() > 0 && (start != composingEnd || end != composingEnd)) {
            InputConnection ic = getCurrentInputConnection();
            if (ic != null) ic.finishComposingText();
            resetComposition(); updateCandidates();
        } else if (composing.length() == 0 && (start != oldStart || end != oldEnd)) {
            updateCandidates();
        }
    }

    @Override public void onFinishInputView(boolean finishingInput) {
        releaseSemantic();
        clearClipboardSession(); swipeSelection.reset();
        closeStroke(); strokeMode = false; strokeCode.setLength(0);
        cancelVoice(); dismissSelectionPopup(); invalidateReselection();
        if (tonePopup != null) tonePopup.dismiss();
        editMode = false; textEditor.reset();
        stopRepeat(); finishLiteral(); super.onFinishInputView(finishingInput);
    }

    @Override public void onFinishInput() {
        releaseSemantic();
        clearClipboardSession();
        closeStroke(); strokeMode = false; strokeCode.setLength(0);
        cancelVoice(); dismissSelectionPopup(); invalidateReselection(); stopRepeat(); resetComposition(); updateCandidates(); resolvedCandidates = null; super.onFinishInput();
    }

    @Override public void onDestroy() {
        cancelSemantic(); semanticRanker.close(); semanticWorker.shutdownNow();
        clearClipboardSession();
        closeStroke();
        destroyed = true; resolvedCandidates = null; textEditor.reset(); candidateGeneration.incrementAndGet(); cancelVoice(); dismissSelectionPopup(); invalidateReselection(); stopRepeat(); handler.removeCallbacksAndMessages(null); loader.shutdownNow(); candidateWorker.shutdownNow(); super.onDestroy();
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
        closeStroke();
        if (tonePopup != null) { tonePopup.dismiss(); tonePopup = null; }
        dismissSelectionPopup();
        // Release the previous Emoji view tree when returning to the keyboard/editor.
        emojiList = null; emojiAdapter = null; emojiModel = null; emojiSearchLabel = null; emojiCategories = null; emojiTabs.clear();
        stopRepeat(); colors(); expandedScroll = null; candidateRow = null; codeLabel = null; expandedMode = null; nextPage = null; selectKey = null; toolbar = null; candidateBar = null; undoKey = null; editorSelect = null; customTool = null;
        quick = prefs.getBoolean("quick", true); cangjie = prefs.getBoolean("cangjie", true); english = prefs.getBoolean("english", true);
        root.removeAllViews(); root.setBackgroundColor(bg); updateKeyboardPadding();
        LinearLayout dock = row(root);
        String hand = prefs.getString("hand", "full");
        if (hand.equals("right")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));
        panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL);
        dock.addView(panel, new LinearLayout.LayoutParams(0, -2, hand.equals("full") ? 1 : .82f));
        if (hand.equals("left")) dock.addView(new View(this), new LinearLayout.LayoutParams(0, 1, .18f));

        if (strokeMode && !secure && !numeric) {
            strokePanel = new StrokePanel(this,bg,fg,keyColor,accent,strokeCode,this::insert,
                () -> { strokeMode=false; render(); },this::delete,this::enter);
            panel.addView(strokePanel); return;
        }
        if (editMode) { renderTextEditor(); return; }
        if (clipboardMode || quickTextMode) { renderTextPanel(); return; }

        toolbar = row(panel);
        toolbar.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(60)));
        tool(toolbar, "emoji", "Emoji", () -> { if (!secure && !numeric) { finishLiteral(); emoji = !emoji; emojiSearch = false; emojiQuery = ""; render(); } }, emoji);
        tool(toolbar, "text_edit", "文字編輯", () -> {
            prepareCursorSwipe(); emoji = false; symbols = false; editMode = true; textEditor.reset(); render();
        }, false);
        undoKey = tool(toolbar, "undo", "重新選字", this::reselect, false);
        undoKey.setEnabled(canReselect()); undoKey.setAlpha(canReselect() ? 1f : .35f);
        String custom = prefs.getString("toolbar_action", "clipboard");
        String icon = "expand".equals(custom) ? "hide" : "quick_text".equals(custom) ? "symbols" : "undo".equals(custom) ? "undo" : "clipboard";
        String label = "expand".equals(custom) ? "候選展開" : "quick_text".equals(custom) ? "快捷文字" : "undo".equals(custom) ? "Undo（重新選字）" : "剪貼簿";
        customTool = tool(toolbar, icon, label, this::runCustomTool, "expand".equals(custom) && expandNextCandidates);
        customTool.setEnabled(!secure && ("undo".equals(custom) ? canReselect() : !numeric));
        customTool.setAlpha(customTool.isEnabled() ? 1f : .35f);
        TextView pen = tool(toolbar, "stroke", "筆劃", () -> {
            if(secure || numeric)return;
            finishLiteral(); cancelVoice(); emoji=false; symbols=false; expanded=false; editMode=false;
            strokeMode=true; render();
        }, false);
        pen.setEnabled(!secure && !numeric);
        TextView mic = tool(toolbar, "mic", voiceListening ? "停止語音輸入" : "語音輸入", this::voice, voiceListening);
        mic.setEnabled(!noLearning && !numeric);
        mic.setAlpha(mic.isEnabled() ? 1f : .35f);
        tool(toolbar, "more", "鍵盤設定", () -> {
            finishLiteral(); startActivity(new Intent(this, SettingsActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP));
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

        LinearLayout bar = new LinearLayout(this); candidateBar = bar;
        bar.setOrientation(LinearLayout.VERTICAL);
        bar.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        panel.addView(bar, new LinearLayout.LayoutParams(-1, dp(60)));
        LinearLayout codeRow = row(bar);
        codeRow.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(18)));
        codeLabel = new TextView(this); codeLabel.setTextColor(muted); codeLabel.setTextSize(11);
        codeLabel.setGravity(Gravity.START | Gravity.CENTER_VERTICAL); codeLabel.setSingleLine(true);
        codeLabel.setIncludeFontPadding(false);
        codeLabel.setEllipsize(android.text.TextUtils.TruncateAt.END);
        codeLabel.setPadding(dp(8), 0, dp(4), 0);
        codeRow.addView(codeLabel, new LinearLayout.LayoutParams(0, -1, 1));
        LinearLayout candidateLine = row(bar);
        candidateLine.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        candidateLine.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(42)));
        TextView cancelCandidates = new TextView(this) {
            private final android.graphics.Paint paint = new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
            @Override protected void onDraw(android.graphics.Canvas canvas) {
                paint.setColor(muted); paint.setStyle(android.graphics.Paint.Style.STROKE);
                paint.setStrokeWidth(dp(1.8f)); paint.setStrokeCap(android.graphics.Paint.Cap.ROUND);
                float cx = getWidth() / 2f, cy = getHeight() / 2f;
                canvas.drawCircle(cx, cy, dp(9), paint);
                float inset = dp(3.5f);
                canvas.drawLine(cx - inset, cy - inset, cx + inset, cy + inset, paint);
                canvas.drawLine(cx + inset, cy - inset, cx - inset, cy + inset, paint);
            }
        };
        cancelCandidates.setBackground(background(bg));
        cancelCandidates.setContentDescription("取消候選及聯想字，返回功能列");
        cancelCandidates.setOnClickListener(v -> dismissCandidates());
        candidateLine.addView(cancelCandidates, new LinearLayout.LayoutParams(dp(36), -1));
        candidateScroll = new HorizontalScrollView(this); candidateScroll.setHorizontalScrollBarEnabled(false); candidateScroll.setFillViewport(false);
        candidateScroll.setOnTouchListener((v,e) -> { if(e.getActionMasked()==MotionEvent.ACTION_DOWN)freezeSemantic(); return false; });
        candidateScroll.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        candidateRow = new LinearLayout(this); candidateRow.setOrientation(LinearLayout.HORIZONTAL);
        candidateRow.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        candidateRow.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        candidateScroll.addView(candidateRow, new HorizontalScrollView.LayoutParams(-2, -1));
        candidateLine.addView(candidateScroll, new LinearLayout.LayoutParams(0, -1, 1));
        nextPage = new TextView(this) {
            private final android.graphics.Paint arrowPaint = new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
            private final android.graphics.Path arrowPath = new android.graphics.Path();
            @Override protected void onDraw(android.graphics.Canvas canvas) {
                arrowPaint.setColor(fg); arrowPaint.setStyle(android.graphics.Paint.Style.STROKE);
                arrowPaint.setStrokeWidth(dp(2)); arrowPaint.setStrokeCap(android.graphics.Paint.Cap.ROUND);
                arrowPaint.setStrokeJoin(android.graphics.Paint.Join.ROUND);
                float cx = getWidth() / 2f, cy = getHeight() / 2f;
                arrowPath.reset();
                if (expanded) {
                    arrowPath.moveTo(cx - dp(9), cy + dp(4.5f));
                    arrowPath.lineTo(cx, cy - dp(4.5f));
                    arrowPath.lineTo(cx + dp(9), cy + dp(4.5f));
                } else {
                    arrowPath.moveTo(cx - dp(4.5f), cy - dp(9));
                    arrowPath.lineTo(cx + dp(4.5f), cy);
                    arrowPath.lineTo(cx - dp(4.5f), cy + dp(9));
                }
                canvas.drawPath(arrowPath, arrowPaint);
            }
        };
        nextPage.setBackground(background(bg));
        nextPage.setOnClickListener(v -> { expanded = !expanded; render(); });
        candidateLine.addView(nextPage, new LinearLayout.LayoutParams(dp(36), -1));
        nextPage.setContentDescription("展開或收起候選字");
        updateCandidates();

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
                {"，","？","！","：","；","（","）","《","》","⌫"}}
                : new String[][]{{"1","2","3","4","5","6","7","8","9","0"},
                {"@","#","$","%","&","*","-","+","(",")"},
                {"?","!",":",";","'","\"","/","=","?","⌫"}};
            for (String[] group : symbolRows) {
                LinearLayout line = row(panel);
                for (String value : group) {
                    if ("⌫".equals(value)) deleteKey(line, 1f);
                    else key(line, value, 1, false, () -> insert(value), keyHeight());
                }
            }
        } else {
            if (prefs.getBoolean("numbers", true)) {
                LinearLayout line = row(panel); int i = 0;
                for (char n : "1234567890".toCharArray()) {
                    if (splitLayout() && i++ == 5) splitGap(line);
                    int numberHeight = splitLayout() || coverReferenceLayout() ? Math.round(keyHeight() * .92f) : 37;
                    TextView number = key(line, "" + n, 1, false, () -> insert("" + n), numberHeight);
                    if (coverReferenceLayout()) number.setTextSize(numberHeight * .58f);
                }
            }
            letters("qwertyuiop", false); letters("asdfghjkl", false); letters("zxcvbnm", true);
        }

        LinearLayout bottom = row(panel);
        boolean foldLetters = splitLayout() && !numeric && !symbols && !emoji;
        int bottomHeight = keyHeight() + (foldLetters ? 4 : 0);
        if (!numeric) {
            TextView modeKey = key(bottom, symbols || emoji ? "ABC" : foldLetters ? "?123" : "123", foldLetters ? 1.35f : 1.25f, true, () -> {
            finishLiteral(); if (emoji) emoji = false; else symbols = !symbols; render();
            }, bottomHeight);
            if (foldLetters) modeKey.setBackground(new android.graphics.drawable.InsetDrawable(background(functionColor, bottomHeight / 2f), dp(foldWidth() * .0055f), dp(4), dp(foldWidth() * .0055f), dp(4)));
        }
        if (symbols && !emoji && !numeric) key(bottom, extraSymbols ? "123" : "#+=", 1, true, () -> { extraSymbols = !extraSymbols; render(); }, keyHeight());
        if (foldLetters) key(bottom, "/", 1, false, () -> insert("/"), bottomHeight);
        TextView select = key(bottom, "🌐", 1, true, this::toggleLanguage, bottomHeight);
        selectKey = select; select.setEnabled(!secure && !numeric);
        select.setTextColor(ascii || englishIntent() ? accent : fg);
        select.setContentDescription("切換中英文，長按選擇系統鍵盤");
        select.setOnLongClickListener(v -> { picker(); return true; });
        if (!numeric) {
            String spaceLabel = foldLetters ? ascii || englishIntent() ? "English" : quick ? "速成" : cangjie ? "倉頡" : "English" : "";
            TextView space = key(bottom, spaceLabel, foldLetters ? 8f : splitLayout() ? 6.4f : symbols ? 4.8f : 3.6f, false, this::space, bottomHeight);
            if (!foldLetters) ((KeyboardKey) space).icon("space");
            space.setContentDescription("空白鍵，左右滑動移動游標"); attachSpaceGesture(space);
            if (!foldLetters) {
                TextView comma = key(bottom, symbols || uriField || ascii || englishIntent() ? "," : "，", .9f, false,
                    () -> insert(symbols || uriField || ascii || englishIntent() ? "," : "，"), keyHeight());
                comma.setContentDescription("逗號，長按快捷標點");
                comma.setOnLongClickListener(v -> { punctuation(comma); return true; });
            }
            TextView period = key(bottom, ".", foldLetters ? 1f : .9f, false,
                () -> insert("."), bottomHeight);
            period.setContentDescription("句號，長按快捷標點");
            period.setOnLongClickListener(v -> { punctuation(period); return true; });
        }
        if (emoji || numeric) deleteKey(bottom, 1.2f);
        TextView enterKey = key(bottom, enterLabel(), foldLetters ? 1.35f : 1.45f, true, this::enter, bottomHeight);
        ((KeyboardKey) enterKey).icon(null);
        enterKey.setContentDescription(enterLabel());
        enterKey.setTextColor(fg); enterKey.setTextSize(14); enterKey.setSingleLine(true);
        if (foldLetters) {
            enterKey.setBackground(new android.graphics.drawable.InsetDrawable(background(accent, bottomHeight / 2f), dp(foldWidth() * .0055f), dp(4), dp(foldWidth() * .0055f), dp(4)));
            enterKey.setTextColor(dark ? 0xFF172338 : Color.WHITE);
        }
        if (getWindow() != null) {
            getWindow().getWindow().setNavigationBarColor(bg);
            View decor = getWindow().getWindow().getDecorView();
            int flags = decor.getSystemUiVisibility();
            decor.setSystemUiVisibility(dark ? flags & ~View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR :
                flags | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }
    }

    private void runCustomTool() {
        if (secure || numeric) return;
        String action = prefs.getString("toolbar_action", "clipboard");
        if ("undo".equals(action)) { reselect(); return; }
        if ("expand".equals(action)) {
            if (!candidates.isEmpty() && composing.length() > 0) { expanded = !expanded; render(); }
            else {
                expandNextCandidates = !expandNextCandidates;
                Toast.makeText(this, expandNextCandidates ? "下次輸入字碼時展開候選" : "已取消自動展開", Toast.LENGTH_SHORT).show();
                render();
            }
            return;
        }
        finishLiteral(); cancelVoice(); emoji = symbols = expanded = editMode = false;
        quickTextMode = "quick_text".equals(action); clipboardMode = !quickTextMode;
        if (clipboardMode) readClipboardOnDemand();
        render();
    }

    private void readClipboardOnDemand() {
        if (secure) return;
        scheduleClipboardExpiry();
        if (noLearning) sessionClipboard.clear();
        android.content.ClipboardManager manager = (android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
        try {
            ClipData clip = manager == null ? null : manager.getPrimaryClip();
            if (clip == null) return;
            // Never retain Android-marked sensitive clips. Plain text only: do not resolve content URIs.
            android.os.PersistableBundle extras = clip.getDescription().getExtras();
            if (extras != null && extras.getBoolean("android.content.extra.IS_SENSITIVE", false)) return;
            for (int i = clip.getItemCount() - 1; i >= 0; i--) {
                CharSequence value = clip.getItemAt(i).getText();
                if (value != null) sessionClipboard.add(value.toString(), !noLearning);
            }
        } catch (SecurityException ignored) {
            Toast.makeText(this, "未能讀取剪貼簿", Toast.LENGTH_SHORT).show();
        } finally {
            scheduleClipboardExpiry();
        }
    }

    private KeyboardKey textPanelButton(String icon, String description, Runnable action) {
        KeyboardKey button = new KeyboardKey(this);
        button.icon(icon); button.setTextColor(fg); button.setGravity(Gravity.CENTER);
        button.setContentDescription(description); button.setTooltipText(description);
        button.setFocusable(true);
        button.setBackground(new android.graphics.drawable.InsetDrawable(textPanelBackground(functionColor, 24), dp(4)));
        button.setOnClickListener(v -> {
            if (prefs.getBoolean("haptic", true)) v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);
            action.run();
        });
        return button;
    }

    private android.graphics.drawable.Drawable textPanelBackground(int color, int radius) {
        GradientDrawable shape = new GradientDrawable(); shape.setColor(color); shape.setCornerRadius(dp(radius));
        return new android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(dark ? 0x40FFFFFF : 0x22000000), shape, null);
    }

    private void renderTextPanel() {
        if (clipboardMode) scheduleClipboardExpiry();
        LinearLayout header = row(panel); header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(4), 0, dp(4), 0);
        header.addView(textPanelButton("back", "返回鍵盤", () -> { clipboardMode = quickTextMode = false; render(); }),
                new LinearLayout.LayoutParams(dp(48), dp(48)));
        TextView title = new TextView(this); title.setText(quickTextMode ? "快捷文字" : "剪貼簿");
        title.setTextColor(fg); title.setTextSize(20); title.setGravity(Gravity.CENTER_VERTICAL);
        title.setPadding(dp(8), 0, dp(8), 0);
        header.addView(title, new LinearLayout.LayoutParams(0, dp(58), 1));
        if (quickTextMode) {
            header.addView(textPanelButton("pen", "管理快捷文字", () -> startActivity(new Intent(this, SettingsActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP))),
                    new LinearLayout.LayoutParams(dp(48), dp(48)));
        } else {
            header.addView(textPanelButton("refresh", "更新剪貼簿", () -> { readClipboardOnDemand(); render(); }),
                    new LinearLayout.LayoutParams(dp(48), dp(48)));
            header.addView(textPanelButton("trash", "清空剪貼簿暫存", () -> { sessionClipboard.clear(); render(); }),
                    new LinearLayout.LayoutParams(dp(48), dp(48)));
        }
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true);
        int height = 4 * (keyHeight() + 8) + (prefs.getBoolean("numbers", true) ? 45 : 0);
        panel.addView(scroll, new LinearLayout.LayoutParams(-1, dp(height)));
        LinearLayout list = new LinearLayout(this); list.setOrientation(LinearLayout.VERTICAL);
        list.setPadding(dp(6), dp(6), dp(6), dp(10)); scroll.addView(list);
        List<String> values = quickTextMode ? QuickTexts.read(prefs) : sessionClipboard.items();
        TextView section = new TextView(this); section.setText(quickTextMode ? "常用文字" : "最近");
        section.setTextColor(muted); section.setTextSize(13); section.setPadding(dp(6), 0, dp(6), dp(8)); list.addView(section);
        if (values.isEmpty()) {
            LinearLayout empty = new LinearLayout(this); empty.setOrientation(LinearLayout.VERTICAL);
            empty.setGravity(Gravity.CENTER); empty.setPadding(dp(20), dp(24), dp(20), dp(24));
            empty.setBackground(textPanelBackground(keyColor, 16));
            KeyboardKey illustration = new KeyboardKey(this); illustration.icon("clipboard"); illustration.setTextColor(muted);
            illustration.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
            empty.addView(illustration, new LinearLayout.LayoutParams(dp(40), dp(40)));
            TextView hint = new TextView(this); hint.setText(quickTextMode ? "未有快捷文字，請到設定新增。" : "未有可用文字。複製後輕按右上角更新。");
            hint.setTextColor(muted); hint.setTextSize(15); hint.setGravity(Gravity.CENTER); hint.setPadding(0,dp(8),0,0);
            empty.addView(hint); list.addView(empty);
        }
        int columns = getResources().getConfiguration().screenWidthDp >= 600 ? 3 :
                getResources().getConfiguration().screenWidthDp >= 340 ? 2 : 1;
        LinearLayout line = null;
        for (int i = 0; i < values.size(); i++) {
            String value = values.get(i);
            if (i % columns == 0) { line = row(list); line.setGravity(Gravity.TOP); }
            LinearLayout card = new LinearLayout(this); card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(12),dp(4),dp(8),dp(12)); card.setBackground(textPanelBackground(keyColor, 14));
            card.setFocusable(true); card.setContentDescription((quickTextMode ? "貼上快捷文字：" : "貼上剪貼簿：") + value);
            card.setOnClickListener(v -> { if (!secure) insert(value); });
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,-2,1); lp.setMargins(dp(4),dp(4),dp(4),dp(4)); line.addView(card,lp);
            LinearLayout cardHeader = row(card); cardHeader.setGravity(Gravity.CENTER_VERTICAL);
            KeyboardKey type = new KeyboardKey(this); type.icon(value.trim().matches("(?i)^https?://.*") ? "link" : "clipboard");
            type.setTextColor(muted); type.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
            cardHeader.addView(type, new LinearLayout.LayoutParams(dp(24),dp(44)));
            View spacer = new View(this); cardHeader.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1));
            if (!quickTextMode) {
                KeyboardKey remove = textPanelButton("close", "刪除剪貼簿項目：" + value, () -> { sessionClipboard.remove(value); render(); });
                remove.setBackground(new android.graphics.drawable.InsetDrawable(textPanelBackground(keyColor, 22), dp(4)));
                cardHeader.addView(remove, new LinearLayout.LayoutParams(dp(44), dp(44)));
            }
            TextView item = new TextView(this); item.setText(value); item.setTextSize(16); item.setTextColor(fg);
            item.setMaxLines(3); item.setEllipsize(TextUtils.TruncateAt.END); item.setMinHeight(dp(48));
            item.setPadding(0, dp(2), dp(4), 0); item.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
            card.addView(item, new LinearLayout.LayoutParams(-1,-2));
        }
        if (line != null && values.size() % columns != 0) {
            for (int i = values.size() % columns; i < columns; i++) {
                View spacer = new View(this); LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,1,1);
                lp.setMargins(dp(4),dp(4),dp(4),dp(4)); line.addView(spacer,lp);
            }
        }
    }

    private void renderTextEditor() {
        LinearLayout header = row(panel);
        TextView back = key(header, "‹", .65f, true, () -> { editMode = false; textEditor.reset(); render(); }, 50);
        back.setContentDescription("返回鍵盤");
        TextView title = new TextView(this); title.setText("文字編輯"); title.setTextSize(20); title.setTextColor(fg);
        title.setGravity(Gravity.CENTER_VERTICAL); header.addView(title, new LinearLayout.LayoutParams(0, dp(50), 3));
        int height = Math.max(48, (4 * (keyHeight() + 8) + (prefs.getBoolean("numbers", true) ? 45 : 0)) / 4);
        LinearLayout controls = row(panel);
        editKey(controls, "‹", "游標向左", () -> textEditor.move(getCurrentInputConnection(), KeyEvent.KEYCODE_DPAD_LEFT), 1, height * 3, true);
        LinearLayout middle = new LinearLayout(this); middle.setOrientation(LinearLayout.VERTICAL);
        controls.addView(middle, new LinearLayout.LayoutParams(0, -2, 1));
        editKey(middle, "↑", "游標向上", () -> textEditor.move(getCurrentInputConnection(), KeyEvent.KEYCODE_DPAD_UP), 1, height, true);
        editorSelect = editKey(middle, "選取", "開始或停止選取文字", () -> {
            textEditor.setSelecting(!textEditor.selecting, getCurrentInputConnection());
            editorSelect.setTextColor(textEditor.selecting ? accent : fg); editorSelect.setSelected(textEditor.selecting);
        }, 1, height, false);
        editKey(middle, "↓", "游標向下", () -> textEditor.move(getCurrentInputConnection(), KeyEvent.KEYCODE_DPAD_DOWN), 1, height, true);
        editKey(controls, "›", "游標向右", () -> textEditor.move(getCurrentInputConnection(), KeyEvent.KEYCODE_DPAD_RIGHT), 1, height * 3, true);
        LinearLayout actions = new LinearLayout(this); actions.setOrientation(LinearLayout.VERTICAL);
        controls.addView(actions, new LinearLayout.LayoutParams(0, -2, 1));
        editKey(actions, "全部選取", "全部選取", () -> textEditor.action(getCurrentInputConnection(), android.R.id.selectAll), 1, height, false).setEnabled(!secure);
        editKey(actions, "複製", "複製選取文字", () -> textEditor.action(getCurrentInputConnection(), android.R.id.copy), 1, height, false).setEnabled(!secure);
        editKey(actions, "貼上", "貼上文字", () -> textEditor.action(getCurrentInputConnection(), android.R.id.paste), 1, height, false).setEnabled(!secure);
        LinearLayout bottom = row(panel);
        editKey(bottom, "|‹", "移到文字開頭", () -> textEditor.move(getCurrentInputConnection(), KeyEvent.KEYCODE_MOVE_HOME), 1.5f, height, true);
        editKey(bottom, "›|", "移到文字結尾", () -> textEditor.move(getCurrentInputConnection(), KeyEvent.KEYCODE_MOVE_END), 1.5f, height, true);
        editKey(bottom, "⌫", "刪除選取文字或前一個字", this::delete, 1, height, true);
    }

    private TextView editKey(LinearLayout parent, String label, String description, Runnable action, float weight, int height, boolean repeat) {
        TextView button = key(parent, label, weight, false, action, height - 8);
        if (parent.getOrientation() == LinearLayout.VERTICAL)
            button.setLayoutParams(new LinearLayout.LayoutParams(-1, dp(height)));
        button.setTextSize(label.length() > 2 ? 15 : 25); button.setContentDescription(description);
        if (repeat) button.setOnTouchListener((v, event) -> {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    stopRepeat(); editingAction = action; v.performClick(); v.setPressed(true); handler.postDelayed(repeatEditing, 400); break;
                case MotionEvent.ACTION_UP: case MotionEvent.ACTION_CANCEL: stopRepeat(); v.setPressed(false); break;
            }
            return true;
        });
        return button;
    }
    private final Runnable repeatEditing = new Runnable() {
        @Override public void run() { if (editingAction != null) { editingAction.run(); handler.postDelayed(this, 65); } }
    };

    private void letters(String letters, boolean withShift) {
        LinearLayout line = prefs.getBoolean("swipe_cursor", true) && !secure && !emojiSearch ?
            new CursorGestureRow(this, this::prepareSelectionSwipe, steps -> swipeSelection.move(getCurrentInputConnection(), steps)) : new LinearLayout(this);
        panel.addView(line, new LinearLayout.LayoutParams(-1, -2));
        if (splitLayout()) {
            LinearLayout left = new LinearLayout(this), right = new LinearLayout(this);
            line.addView(left, new LinearLayout.LayoutParams(0,-2,1)); splitGap(line);
            line.addView(right, new LinearLayout.LayoutParams(0,-2,1));
            String leftLetters, rightLetters;
            if (withShift) {
                shiftKey(left,1.25f);
                leftLetters = "zxcv"; rightLetters = "vbnm";
            } else if (letters.length()==9) {
                left.addView(new View(this),new LinearLayout.LayoutParams(0,1,.3f));
                leftLetters = "asdfg"; rightLetters = "ghjkl";
            } else {
                leftLetters = letters.substring(0,5); rightLetters = letters.substring(5);
            }
            for (char letter : leftLetters.toCharArray()) addLetterKey(left,letter);
            for (char letter : rightLetters.toCharArray()) addLetterKey(right,letter);
            if (withShift) deleteKey(right,1.25f);
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
        ((KeyboardKey)button).typingTouch(true);
        button.setContentDescription("英文字母 "+latin);
        if(!ascii && !emojiSearch && (quick||cangjie)) ((KeyboardKey)button).legend(latin,String.valueOf(RADICALS.charAt(letter-'a')),muted,splitLayout());
    }

    private void typeLetter(char lower) {
        nextSuggestionsDismissed = false;
        swipeSelection.reset();
        if (voiceListening) { cancelVoice(); render(); }
        if (emojiSearch) { emojiQuery += lower; refreshEmoji(); return; }
        invalidateReselection(); restoredCandidate = null;
        String value = String.valueOf(shift || caps ? Character.toUpperCase(lower) : lower);
        if (secure || ascii && !prefs.getBoolean("english_chinese", true)) insert(value);
        else {
            maybeAutocorrect(lower);
            if (composing.length() >= 48) selectCandidate();
            composing.append(value); InputConnection ic = getCurrentInputConnection();
            if (ic != null) ic.setComposingText(composing, 1);
            updateCandidates();
        }
        if (shift && !caps) { shift = false; render(); }
    }

    private String context() {
        if (noLearning || !prefs.getBoolean("context_candidates", true)) return "";
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return "";
        CharSequence preceding = ic.getTextBeforeCursor(256, 0); if (preceding == null) return "";
        String text = preceding.toString(), code = composing.toString();
        if (!code.isEmpty() && text.endsWith(code)) text = text.substring(0, text.length() - code.length());
        return SemanticPrompt.window(text);
    }

    private List<String> personalEnglish() {
        List<String> result = new ArrayList<>(); if (noLearning) return result;
        for (Map.Entry<String, ?> entry : personal.getAll().entrySet())
            if (entry.getKey().startsWith("e:") && entry.getValue() instanceof String) result.add((String) entry.getValue());
        if (prefs.getBoolean("learning", false)) {
            List<String> words = new ArrayList<>(englishLearned.getAll().keySet());
            words.sort(Comparator.comparingInt((String word) -> englishLearned.getInt(word, 0)));
            result.addAll(words);
        }
        return result;
    }

    private boolean englishIntent() {
        return ascii || forceEnglish || !forceChinese && prefs.getBoolean("english", true) && englishEngine != null
            && (englishEngine.likelyEnglish(composing.toString(), personalEnglish())
                || prefs.getBoolean("english_chinese",true) && composing.length()>=3 && englishChineseEngine!=null && !englishChineseEngine.lookup(composing.toString()).isEmpty());
    }

    private List<String> englishSuggestions(String input) {
        List<String> result = new ArrayList<>(englishEngine.suggest(input, personalEnglish(), prefs.getBoolean("english_repair", true)));
        if (!noLearning && prefs.getBoolean("learning", false) && result.size() > 1)
            result.subList(1,result.size()).sort(Comparator.comparingInt((String word) -> englishLearned.getInt(word,0)).reversed());
        return result;
    }

    private String pinPrefix(String code) {
        return "p:" + (quick ? "Q" : "-") + (cangjie ? "C" : "-") + ":" + code.toLowerCase(Locale.ROOT) + ":";
    }

    private void addCandidate(LinkedHashSet<String> result, InputCandidate candidate) {
        if (candidate.text.isEmpty()) return;
        if (result.add(candidate.text)) candidateDetails.put(candidate.text, candidate);
        consumedCodes.putIfAbsent(candidate.text, candidate.source.length());
    }

    private CandidateRequest resolvedCandidates;

    /** All mutable editor/personal state is copied on the UI thread before searching. */
    private final class CandidateRequest {
        final String input, preceding;
        final boolean quick, cangjie, continuous, chooseFirst, forceEnglish, forceChinese, noLearning, secure, isEnglish, nextSuggestionsDismissed;
        final InputCandidate restoredCandidate;
        final Map<String, ?> personal, counts, englishCounts, settings;
        final List<String> englishWords;
        final Map<String, InputCandidate> details = new HashMap<>();
        final Map<String, Integer> consumed = new HashMap<>();
        boolean computed;
        List<String> values = Collections.emptyList();
        List<InputCandidate> corrections = Collections.emptyList();
        CandidateRequest() {
            input = composing.toString(); preceding = context();
            nextSuggestionsDismissed = KaiboardService.this.nextSuggestionsDismissed;
            quick = KaiboardService.this.quick; cangjie = KaiboardService.this.cangjie;
            chooseFirst = KaiboardService.this.chooseFirst; forceEnglish = KaiboardService.this.forceEnglish || ascii;
            forceChinese = KaiboardService.this.forceChinese; noLearning = KaiboardService.this.noLearning;
            secure = KaiboardService.this.secure; restoredCandidate = KaiboardService.this.restoredCandidate;
            settings = new HashMap<>(prefs.getAll());
            personal = noLearning ? Collections.emptyMap() : new HashMap<>(KaiboardService.this.personal.getAll());
            counts = noLearning || !enabled("learning", false) ? Collections.emptyMap() : new HashMap<>(learned.getAll());
            englishCounts = noLearning || !enabled("learning", false) ? Collections.emptyMap() : new HashMap<>(englishLearned.getAll());
            englishWords = new ArrayList<>(personalEnglish());
            continuous = quick && enabled("continuous", true) && input.length() > 2 && !secure;
            isEnglish = forceEnglish || !forceChinese && enabled("english", true) && englishEngine != null
                && (englishEngine.likelyEnglish(input, englishWords)
                    || enabled("english_chinese",true) && input.length()>=3 && englishChineseEngine!=null && !englishChineseEngine.lookup(input).isEmpty());
        }
        boolean enabled(String name, boolean fallback) { Object value = settings.get(name); return value instanceof Boolean ? (Boolean)value : fallback; }
        int learnedCount(String code, String word) {
            if (noLearning || !enabled("learning", false)) return 0;
            Object value = counts.get(LearningRanker.isLearnable(word)
                ? LearningRanker.key(code, quick, cangjie, word) : PhraseLearning.key(word));
            return value instanceof Integer ? (Integer)value : 0;
        }
        int phraseCount(String word) { return learnedCount("", word); }
        String pinPrefix(String code) { return "p:" + (quick ? "Q" : "-") + (cangjie ? "C" : "-") + ":" + code.toLowerCase(Locale.ROOT) + ":"; }
        List<String> englishSuggestions() {
            List<String> result = new ArrayList<>(englishEngine.suggest(input, englishWords, enabled("english_repair", true)));
            if (!noLearning && enabled("learning", false) && result.size() > 1)
                result.subList(1, result.size()).sort(Comparator.comparingInt((String word) -> {
                    Object count = englishCounts.get(word); return count instanceof Integer ? (Integer)count : 0;
                }).reversed());
            return result;
        }
        void add(LinkedHashSet<String> result, InputCandidate candidate) {
            if (candidate.text.isEmpty()) return;
            if (result.add(candidate.text)) details.put(candidate.text, candidate);
            consumed.putIfAbsent(candidate.text, candidate.source.length());
        }
    }

    private void updateCandidates() {
        cancelSemantic();
        if (pendingCandidates != null) { pendingCandidates.cancel(true); pendingCandidates = null; }
        final int generation = candidateGeneration.incrementAndGet();
        final CandidateRequest request = new CandidateRequest();
        if (!request.continuous || request.chooseFirst || candidateEngine == null) {
            computeCandidates(request); applyCandidates(request); scheduleSemantic(request, generation); return;
        }
        // Immediately usable exact first-character choices; never show stale choices from an older code.
        LinkedHashSet<String> immediate = new LinkedHashSet<>();
        if (request.isEnglish) {
            request.add(immediate, InputCandidate.english(request.input,request.input)); addTranslations(request,immediate);
            for (String word : request.englishSuggestions()) request.add(immediate, InputCandidate.english(request.input, word));
        }
        else addPrefixChoices(request, immediate, 7);
        request.values = new ArrayList<>(immediate);
        applyCandidates(request);
        if (destroyed) return;
        pendingCandidates = candidateWorker.schedule(() -> {
            if (candidateGeneration.get() != generation) return;
            CandidateRequest finished = request;
            finished.details.clear(); finished.consumed.clear();
            computeCandidates(finished);
            handler.post(() -> {
                if (!destroyed && candidateGeneration.get() == generation && composing.toString().equals(finished.input))
                    { applyCandidates(finished); scheduleSemantic(finished, generation); }
            });
        }, 30, TimeUnit.MILLISECONDS);
    }

    private void cancelSemantic() {
        if (pendingSemantic != null) { pendingSemantic.cancel(false); pendingSemantic = null; }
        if (semanticRanker != null) semanticRanker.cancel();
    }
    private void releaseSemantic() {
        cancelSemantic();
        if (!semanticWorker.isShutdown()) semanticWorker.execute(() -> semanticRanker.close());
    }
    @Override public void onTrimMemory(int level) {
        super.onTrimMemory(level);
        if (level >= android.content.ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW) releaseSemantic();
    }
    private void freezeSemantic() {
        semanticFrozenGeneration = candidateGeneration.get(); cancelSemantic();
    }
    private void scheduleSemantic(CandidateRequest request, int generation) {
        if (destroyed || !BuildConfig.SEMANTIC_MODEL || request.secure || request.noLearning || request.isEnglish
                || request.chooseFirst || request.restoredCandidate != null || request.input.isEmpty()
                || !request.enabled("context_candidates", true) || !request.enabled("semantic_candidates", true)
                || semanticFrozenGeneration == generation) return;
        List<String> exact = new ArrayList<>();
        for (String value : request.values) {
            InputCandidate detail = request.details.get(value);
            if (detail == null) continue;
            if (request.personal.containsKey(request.pinPrefix(detail.effectiveCode()) + value)
                    || request.personal.containsKey("c:" + request.input.toLowerCase(Locale.ROOT) + ":" + value)
                    || decoder.knownWord(value) && request.learnedCount(request.input, value) > 0) return;
            if (!detail.corrected && !detail.englishOnly() && detail.source.equals(request.input)
                    && detail.effectiveCode().equals(request.input) && detail.segments.stream().noneMatch(s -> s.translated))
                exact.add(value);
        }
        if (exact.size() < 2) return;
        List<String> original = new ArrayList<>(request.values);
        pendingSemantic = semanticWorker.schedule(() -> {
            android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
            List<String> ranked = semanticRanker.rerank(request.preceding, original, exact,
                () -> candidateGeneration.get() == generation && semanticFrozenGeneration != generation && !Thread.currentThread().isInterrupted());
            if (ranked.equals(original)) return;
            handler.post(() -> {
                if (!destroyed && candidateGeneration.get() == generation && semanticFrozenGeneration != generation
                        && composing.toString().equals(request.input) && isInputViewShown()) {
                    request.values = ranked; applyCandidates(request);
                }
            });
        }, 350, TimeUnit.MILLISECONDS);
    }

    private void addTranslations(CandidateRequest request, LinkedHashSet<String> result) {
        if (request.secure || !request.enabled("english_chinese",true) || englishChineseEngine==null)return;
        List<String> meanings=englishChineseEngine.lookup(request.input,request.preceding,this::repairScore);
        for (String text:meanings.subList(0,Math.min(3,meanings.size())))request.add(result,InputCandidate.translation(request.input,text));
    }

    private void addPrefixChoices(CandidateRequest request, LinkedHashSet<String> result, int limit) {
        if (dictionary == null || !request.quick || request.forceEnglish) return;
        for (int size = Math.min(2, request.input.length()); size >= 1; size--) {
            String part = request.input.substring(0, size);
            List<String> words = new ArrayList<>(dictionary.quickCandidates(part));
            if (decoder != null && !request.preceding.isEmpty()) words.sort(Comparator.comparingDouble(
                (String word) -> decoder.languageScore(request.preceding, word)).reversed());
            words = LearningRanker.rank(words, word -> request.learnedCount(part, word));
            for (int i = 0; i < Math.min(limit, words.size()); i++) request.add(result, InputCandidate.chinese(dictionary, part, words.get(i)));
        }
    }

    private void applyCandidates(CandidateRequest request) {
        if (request.computed) resolvedCandidates = request;
        candidatePage = 0; consumedCodes.clear(); candidateDetails.clear();
        consumedCodes.putAll(request.consumed); candidateDetails.putAll(request.details);
        candidates = new ArrayList<>(request.values); corrections = request.corrections;
        if (expandNextCandidates && !candidates.isEmpty() && composing.length() > 0) {
            expandNextCandidates = false; expanded = true; render(); return;
        }
        displayCandidates();
        if (expanded && expandedScroll != null) renderExpandedCandidates();
    }

    private void computeCandidates(CandidateRequest request) {
        String input = request.input, preceding = request.preceding;
        boolean quick = request.quick, cangjie = request.cangjie, continuous = request.continuous,
            chooseFirst = request.chooseFirst, forceEnglish = request.forceEnglish, forceChinese = request.forceChinese,
            noLearning = request.noLearning, secure = request.secure;
        InputCandidate restoredCandidate = request.restoredCandidate;
        LinkedHashSet<String> results = new LinkedHashSet<>();
        if (!secure && !numeric && !request.noLearning && !request.nextSuggestionsDismissed && input.isEmpty() && decoder != null
                && request.enabled("next_suggestions", true)) {
            InputConnection ic = getCurrentInputConnection();
            CharSequence selected = ic == null ? null : ic.getSelectedText(0);
            if (selected == null || selected.length() == 0)
                for (String tail : decoder.nextSuggestions(preceding, 12, request::phraseCount))
                    request.add(results, new InputCandidate("", Collections.singletonList(
                        new InputCandidate.Segment("", tail, false)), false));
        }
        if (!secure && !input.isEmpty()) {
            if (continuous && chooseFirst && dictionary != null) {
                for (int size = 2; size >= 1; size--) {
                    String part = input.substring(0, size);
                    for (String word : LearningRanker.rank(dictionary.quickCandidates(part), w -> request.learnedCount(part, w)))
                        request.add(results, InputCandidate.chinese(dictionary, part, word));
                }
            } else {
                boolean isEnglish = request.isEnglish;
                if (englishEngine != null && request.enabled("english", true) && isEnglish) {
                    request.add(results,InputCandidate.english(input,input));addTranslations(request,results);
                }
                if (englishEngine != null && request.enabled("english", true) && isEnglish)
                    for (String word : request.englishSuggestions())
                        request.add(results, InputCandidate.english(input, word));
                if (candidateEngine == null && dictionary != null && !forceEnglish) {
                    for (String word : dictionary.lookup(input, quick, cangjie, false))
                        if (!word.equals(input)) request.add(results, InputCandidate.chinese(dictionary, input, word));
                }
                if (candidateEngine != null && !forceEnglish) {
                    if (continuous && !forceChinese && request.enabled("mixed", true) && request.enabled("english", true))
                        for (InputCandidate candidate : candidateEngine.mixed(input, preceding, request.englishWords, request::learnedCount)) request.add(results, candidate);
                    if (continuous && !forceChinese && !request.isEnglish && request.enabled("mixed",true) && request.enabled("english_chinese",true) && englishChineseEngine!=null)
                        for(InputCandidate candidate:englishChineseEngine.mixedSuffix(input,preceding,candidateEngine,request::learnedCount))request.add(results,candidate);
                    for (InputCandidate candidate : candidateEngine.chinese(input, preceding, continuous, quick, cangjie, request::learnedCount)) request.add(results, candidate);
                }
                if (!noLearning && dictionary != null) {
                    String prefix = "c:" + input.toLowerCase(Locale.ROOT) + ":";
                    for (Map.Entry<String, ?> entry : request.personal.entrySet())
                        if (entry.getKey().startsWith(prefix) && entry.getValue() instanceof String)
                            request.add(results, InputCandidate.chinese(dictionary, input, (String) entry.getValue()));
                }
                if (englishEngine != null && request.enabled("english", true) && !isEnglish)
                    for (String word : request.englishSuggestions())
                        request.add(results, InputCandidate.english(input, word));
            }
            if (!request.isEnglish) addTranslations(request,results);
            if (!noLearning) {
                String prefix = request.pinPrefix(input);
                for (Map.Entry<String, ?> entry : request.personal.entrySet()) if (entry.getKey().startsWith(prefix) && entry.getValue() instanceof String) {
                    String text = (String) entry.getValue();
                    if (EnglishEngine.validWord(text)) {
                        if (!forceChinese) request.add(results, InputCandidate.english(input,text));
                    } else if (!forceEnglish && dictionary != null) request.add(results, InputCandidate.chinese(dictionary,input,text));
                }
            }
            if (restoredCandidate != null && restoredCandidate.source.equals(input)) {
                request.add(results, restoredCandidate);
            }
            if (quick && !chooseFirst && !request.isEnglish && quickTypos != null && request.enabled("quick_repair", true)) {
                List<InputCandidate> baselines = new ArrayList<>();
                for (String word : results) {
                    InputCandidate detail = request.details.get(word);
                    if (!detail.englishOnly() && dictionary.matchQuickCodes(input, detail.text).size() > 0) { baselines.add(detail); if (baselines.size() == 3) break; }
                }
                List<InputCandidate> repaired = quickTypos.suggest(input, baselines, preceding);
                List<InputCandidate> distinct = new ArrayList<>();
                for (InputCandidate candidate : repaired) if (!results.contains(candidate.text)) distinct.add(candidate);
                request.corrections = distinct;
            }
            if (cangjie && !chooseFirst && !request.isEnglish && !forceEnglish && dictionary != null
                    && request.enabled("cangjie_repair", true)) {
                List<InputCandidate> repairs = new ArrayList<>(request.corrections);
                repairs.addAll(ChineseAutocorrect.cangjieRepairs(dictionary, input));
                request.corrections = repairs;
            }
            if (results.isEmpty()) request.add(results, InputCandidate.english(input, input));
        }
        if (continuous && !chooseFirst && !request.isEnglish && !forceEnglish) {
            LinkedHashSet<String> ordered = new LinkedHashSet<>();
            int count = 0;
            for (String value : results) { ordered.add(value); if (++count == 3) break; }
            addPrefixChoices(request, ordered, 2);
            ordered.addAll(results); results = ordered;
        }
        request.values = new ArrayList<>(results);
        if (!noLearning) request.values.sort(Comparator.comparingInt((String value) ->
            request.personal.containsKey(request.pinPrefix(request.details.get(value).effectiveCode()) + value) ? 2 :
            request.personal.containsKey("c:" + input.toLowerCase(Locale.ROOT) + ":" + value) ? 1 : 0).reversed());
        if (!request.corrections.isEmpty()) {
            LinkedHashSet<String> combined = new LinkedHashSet<>();
            for (int i=0;i<Math.min(3,request.values.size());i++) combined.add(request.values.get(i));
            double baselineScore = Double.NEGATIVE_INFINITY;
            for (String value : request.values) {
                InputCandidate detail = request.details.get(value);
                if (detail != null && detail.source.length() == input.length() && !detail.englishOnly())
                    baselineScore = Math.max(baselineScore, repairScore(preceding, value));
            }
            int promoted = 0;
            for (InputCandidate candidate : request.corrections) {
                if (promoted < 2 && !results.contains(candidate.text)
                    && repairScore(preceding, candidate.text) > baselineScore + Math.log(4)) {
                    request.add(combined, candidate); promoted++;
                }
            }
            combined.addAll(request.values);
            for (InputCandidate candidate : request.corrections)
                if (!results.contains(candidate.text)) request.add(combined,candidate);
            request.values = new ArrayList<>(combined);
        }
        if(request.enabled("english_chinese",true)){
            LinkedHashSet<String> visible=new LinkedHashSet<>();
            if(!request.values.isEmpty())visible.add(request.values.get(0));
            int promoted=0;
            for(String value:request.values){
                InputCandidate detail=request.details.get(value);
                if(detail!=null && detail.segments.stream().anyMatch(segment->segment.translated) && promoted<2){visible.add(value);promoted++;}
            }
            visible.addAll(request.values);request.values=new ArrayList<>(visible);
        }
        for (String word : request.values) request.consumed.putIfAbsent(word, input.length());
        request.computed = true;
    }

    private int learnedCount(String code, String word) {
        return noLearning || !prefs.getBoolean("learning", false) ? 0 : learned.getInt(
            LearningRanker.isLearnable(word) ? LearningRanker.key(code, quick, cangjie, word) : PhraseLearning.key(word), 0);
    }

    private void toggleLanguage() {
        if (secure || numeric) return;
        if (ascii || composing.length() == 0) {
            finishLiteral(); ascii = !ascii; forceEnglish = forceChinese = false; render();
        } else {
            boolean wasEnglish = englishIntent(); forceEnglish = !wasEnglish; forceChinese = wasEnglish;
            chooseFirst = false; updateCandidates();
        }
    }

    private void dismissCandidates() {
        // Keep committed text and its reselection record intact. No candidate is accepted here.
        candidateGeneration.incrementAndGet();
        if (pendingCandidates != null) { pendingCandidates.cancel(true); pendingCandidates = null; }
        if (composing.length() > 0) {
            InputConnection ic = getCurrentInputConnection();
            if (ic != null) ic.finishComposingText();
            composing.setLength(0); forceEnglish = forceChinese = false; chooseFirst = false;
            restoredCandidate = null;
        }
        nextSuggestionsDismissed = true;
        resolvedCandidates = null; candidates = Collections.emptyList(); corrections = Collections.emptyList();
        candidateDetails.clear(); consumedCodes.clear(); candidatePage = 0;
        expanded = false; expandNextCandidates = false;
        dismissSelectionPopup(); render();
    }

    private void displayCandidates() {
        if (candidateRow == null) return;
        candidateRow.removeAllViews();
        if (expandedMode != null) {
            expandedMode.setText(ascii || englishIntent() ? "中文" : "英文");
            expandedMode.setEnabled(!secure && !numeric);
        }
        if (undoKey != null) { undoKey.setEnabled(canReselect()); undoKey.setAlpha(canReselect() ? 1f : .35f); }
        if (customTool != null && "undo".equals(prefs.getString("toolbar_action", "clipboard"))) {
            customTool.setEnabled(canReselect()); customTool.setAlpha(canReselect() ? 1f : .35f);
        }
        if(selectKey!=null) selectKey.setTextColor(ascii || englishIntent() ? accent : fg);
        boolean active = (composing.length() > 0 || !candidates.isEmpty()) && !secure && !numeric;
        if (toolbar != null) toolbar.setVisibility(active ? View.GONE : View.VISIBLE);
        if (candidateBar != null) candidateBar.setVisibility(active ? View.VISIBLE : View.GONE);
        if (codeLabel != null) {
            String code = composing.toString();
            StringBuilder label = new StringBuilder();
            for (char c : code.toCharArray()) {
                int index = Character.toLowerCase(c) - 'a';
                label.append(!englishIntent() && (quick || cangjie) && index >= 0 && index < 26
                    ? RADICALS.charAt(index) : c);
            }
            String radicals = label.toString();
            codeLabel.setText(code.isEmpty() && !candidates.isEmpty() ? "聯想字" : radicals.equals(code) ? code : code + "  " + radicals);
            codeLabel.setContentDescription("輸入碼：" + code);
        }
        if (restoredCandidate != null) {
            TextView edit = new TextView(this); edit.setText("分段改選"); edit.setTextColor(accent); edit.setTextSize(15);
            edit.setGravity(Gravity.CENTER); edit.setPadding(dp(8),0,dp(8),0); edit.setContentDescription("分段改選");
            edit.setOnClickListener(v -> segmentMenu(edit, restoredCandidate));
            candidateRow.addView(edit, new LinearLayout.LayoutParams(-2, dp(42)));
        }
        if (candidates.isEmpty()) { nextPage.setVisibility(View.INVISIBLE); return; }
        int pages = (candidates.size() + PAGE_SIZE - 1) / PAGE_SIZE;
        candidatePage %= pages;
        for (int i = 0; i < candidates.size(); i++) {
            String value = candidates.get(i);
            boolean partial = consumedCodes.getOrDefault(value, composing.length()) < composing.length();
            boolean corrected = candidateDetails.get(value) != null && candidateDetails.get(value).corrected;
            TextView item = new TextView(this); item.setText(value); item.setTextSize(23); item.setTextColor(fg);
            item.setGravity(Gravity.CENTER); item.setPadding(dp(12), 0, dp(12), 0); item.setMinWidth(dp(48)); item.setSingleLine(true);
            boolean translated = candidateDetails.get(value)!=null && candidateDetails.get(value).segments.stream().anyMatch(s -> s.translated);
            item.setContentDescription((translated ? "英轉中候選：" : corrected ? "修正候選：" : "") + value + (partial || chooseFirst ? "，先輸入此字並保留後續字碼" : ""));
            if (i == candidatePage * PAGE_SIZE) { item.setTextColor(accent); item.setTypeface(null, Typeface.BOLD); }
            item.setBackgroundColor(Color.TRANSPARENT); item.setOnClickListener(v -> commit(value));
            item.setOnTouchListener((v, event) -> { if(event.getActionMasked()==MotionEvent.ACTION_DOWN)freezeSemantic(); return false; });
            if (composing.length() > 0) item.setOnLongClickListener(v -> { candidateMenu(item, candidateDetails.get(value)); return true; });
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, dp(42)); params.setMargins(0, 0, 0, 0);
            candidateRow.addView(item, params);
        }
        nextPage.setVisibility(View.VISIBLE);
        nextPage.invalidate();
        final int first = candidatePage * PAGE_SIZE;
        candidateScroll.post(() -> {
            if (first < candidateRow.getChildCount()) candidateScroll.scrollTo(candidateRow.getChildAt(first).getLeft(), 0);
        });
    }

    private double repairScore(String preceding, String text) {
        return decoder == null ? Math.log(dictionary.frequency(text)) : decoder.languageScore(preceding, text);
    }

    private boolean maybeAutocorrect(Character next) {
        String code = composing.toString();
        if (!prefs.getBoolean("chinese_autocorrect", true) || secure || numeric || ascii || strokeMode
                || forceEnglish || chooseFirst || dictionary == null || decoder == null || englishIntent()
                || code.equals(rejectedAutoCode) || code.length() < 2 || code.length() > 16) return false;
        if (!ChineseAutocorrect.allowTrigger(next != null, forceChinese, prefs.getBoolean("english", true))) return false;
        if (next != null) {
            // Preserve Quick phrase composition and legitimate longer Cangjie codes.
            if (quick && prefs.getBoolean("continuous", true) && (code.length() < 4 || code.length()%2 != 0)) return false;
            if (cangjie && dictionary.hasCangjiePrefix(code + next)) return false;
            if (!quick && (!cangjie || code.length() < 3
                    || code.length() < 5 && dictionary.hasCangjiePrefix(code))) return false;
        }
        if (pendingCandidates != null) { pendingCandidates.cancel(true); pendingCandidates = null; }
        candidateGeneration.incrementAndGet();
        CandidateRequest request = resolvedCandidates;
        if (request == null || request.quick != quick || request.cangjie != cangjie
                || !request.input.equals(code) || !request.preceding.equals(context())) {
            request = new CandidateRequest();
            computeCandidates(request);
        }
        final String preceding = request.preceding;
        InputCandidate chosen = ChineseAutocorrect.choose(code, request.preceding,
            request.details.values(), request.corrections, text -> repairScore(preceding, text));
        if (chosen == null || !decoder.supportsCorrection(request.preceding, chosen.text)) return false;
        commitDetail(chosen, false);
        if (composing.length() != 0) return false;
        InputConnection ic = getCurrentInputConnection();
        CharSequence before = ic == null ? null : ic.getTextBeforeCursor(128, 0);
        ExtractedText extracted = ic == null ? null : ic.getExtractedText(new ExtractedTextRequest(), 0);
        if (before != null && before.toString().endsWith(chosen.text) && extracted != null
                && extracted.selectionStart == extracted.selectionEnd) {
            autoUndo = chosen; autoUndoBefore = before.toString();
            autoUndoCursor = extracted.startOffset + extracted.selectionEnd;
        }
        return true;
    }

    private boolean undoAutocorrect(InputConnection ic) {
        if (autoUndo == null || composing.length() != 0) return false;
        CharSequence before = ic.getTextBeforeCursor(128, 0), selected = ic.getSelectedText(0);
        ExtractedText extracted = ic.getExtractedText(new ExtractedTextRequest(), 0);
        InputCandidate record = autoUndo; autoUndo = null;
        if (extracted == null || extracted.selectionStart != extracted.selectionEnd
                || extracted.startOffset + extracted.selectionEnd != autoUndoCursor
                || before == null || !before.toString().equals(autoUndoBefore)
                || selected != null && selected.length() > 0) return false;
        ic.beginBatchEdit();
        boolean removed = ic.deleteSurroundingText(record.text.length(), 0);
        if (removed) {
            composing.append(record.source); rejectedAutoCode = record.source;
            ic.setComposingText(composing, 1);
        }
        ic.endBatchEdit();
        if (removed) { invalidateReselection(); updateCandidates(); }
        return removed;
    }

    private void space() {
        if (emojiSearch) { emojiQuery += " "; refreshEmoji(); return; }
        // Explicit Cangjie confirmation accepts the highlighted candidate.
        if (composing.length() > 0 && cangjie && !englishIntent() && !candidates.isEmpty()) {
            selectCandidate(); return;
        }
        if (composing.length() > 0 && maybeAutocorrect(null)) return;
        if (composing.length() > 0 && englishIntent()) {
            String word = composing.toString();
            List<InputCandidate.Segment> parts = Arrays.asList(new InputCandidate.Segment(word,word,true),
                new InputCandidate.Segment(""," ",true));
            commitDetail(new InputCandidate(word,parts,false),true);
        }
        else if (composing.length() > 0 && !candidates.isEmpty()) { candidatePage++; displayCandidates(); }
        else if (composing.length() > 0) finishLiteral();
        else insert(" ");
    }

    private void selectCandidate() {
        if (!candidates.isEmpty()) commit(candidates.get(Math.min(candidatePage * PAGE_SIZE, candidates.size() - 1)));
        else finishLiteral();
    }

    private void commit(String value) {
        autoUndo = null; rejectedAutoCode = "";
        InputCandidate detail = candidateDetails.get(value);
        if (detail == null) detail = InputCandidate.english(composing.toString(), value);
        commitDetail(detail, true);
    }

    private void commitDetail(InputCandidate detail, boolean learn) {
        if (detail.text.isEmpty() || !composing.toString().startsWith(detail.source)) return;
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        int consumed = Math.min(detail.source.length(), composing.length());
        String remaining = composing.substring(consumed);
        List<String> selectedPhrases = decoder == null || !learn ? Collections.emptyList()
            : PhraseLearning.selectedWords(context(), detail, decoder::knownWord,
                prefs.getBoolean("learning", false), noLearning);
        invalidateReselection();
        ic.beginBatchEdit();
        boolean accepted = ic.commitText(detail.text, 1);
        if (accepted && learn && !noLearning && prefs.getBoolean("learning", false)) {
            for (InputCandidate.Segment segment : detail.segments) {
                if (segment.translated || segment.code.isEmpty()) continue;
                if (segment.english) learnEnglish(segment.text);
                else if (LearningRanker.isLearnable(segment.text)) learnCharacter(segment.code, segment.text);
            }
            for (String word : selectedPhrases) incrementPhrase(word);
        }
        if (accepted) {
            nextSuggestionsDismissed = false;
            composing.setLength(0); composing.append(remaining); chooseFirst = false; forceEnglish = forceChinese = false; restoredCandidate = null;
            if (remaining.isEmpty()) ic.finishComposingText(); else ic.setComposingText(remaining, 1);
        }
        ic.endBatchEdit();
        if (accepted && learn && remaining.isEmpty() && !secure && !detail.source.isEmpty()) {
            ExtractedText extracted = ic.getExtractedText(new ExtractedTextRequest(), 0);
            CharSequence before = ic.getTextBeforeCursor(128, 0);
            if (extracted != null && extracted.selectionStart == extracted.selectionEnd && before != null) {
                int cursor = extracted.startOffset + extracted.selectionEnd;
                reselection = new ReselectionRecord(detail, cursor, before.toString());
                reselectionLearned = !noLearning && prefs.getBoolean("learning", false);
                reselectionPhrases = selectedPhrases;
                selectionStart = selectionEnd = cursor;
            }
        }
        expanded = false; render();
    }

    private void learnEnglish(String word) {
        if (noLearning || !prefs.getBoolean("learning", false) || !EnglishEngine.validWord(word)) return;
        SharedPreferences.Editor editor = englishLearned.edit();
        Map<String, ?> all = englishLearned.getAll();
        if (!all.containsKey(word) && all.size() >= 500)
            editor.remove(Collections.min(all.keySet(), Comparator.comparingInt(w -> englishLearned.getInt(w, 0))));
        editor.putInt(word, Math.min(100000, englishLearned.getInt(word, 0) + 1)).apply();
    }

    private void learnCharacter(String code, String character) {
        if (noLearning || !prefs.getBoolean("learning", false) || !LearningRanker.isLearnable(character)) return;
        String key = LearningRanker.key(code, quick, cangjie, character);
        SharedPreferences.Editor edit = learned.edit();
        Map<String, ?> all = learned.getAll();
        List<String> characterKeys = new ArrayList<>();
        for (String existing : all.keySet()) if (!existing.startsWith("W:")) characterKeys.add(existing);
        if (!all.containsKey(key) && characterKeys.size() >= 2000) {
            String leastUsed = Collections.min(characterKeys, Comparator.comparingInt(k -> learned.getInt(k, 0)));
            edit.remove(leastUsed);
        }
        edit.putInt(key, Math.min(100000, learned.getInt(key, 0) + 1)).apply();
    }

    private void incrementPhrase(String word) {
        if (decoder == null || !decoder.knownWord(word)) return;
        String key = PhraseLearning.key(word);
        Map<String, ?> all = learned.getAll();
        List<String> phraseKeys = new ArrayList<>();
        for (String existing : all.keySet()) if (existing.startsWith("W:")) phraseKeys.add(existing);
        SharedPreferences.Editor edit = learned.edit();
        if (!all.containsKey(key) && phraseKeys.size() >= 1000)
            edit.remove(Collections.min(phraseKeys, Comparator.comparingInt(k -> learned.getInt(k, 0))));
        edit.putInt(key, Math.min(100000, learned.getInt(key, 0) + 1)).apply();
    }

    private void finishLiteral() {
        if (composing.length() > 0) commitDetail(InputCandidate.english(composing.toString(), composing.toString()), false);
    }

    private void insert(String text) {
        nextSuggestionsDismissed = false;
        swipeSelection.reset();
        if (text.equals("'") && !secure && !ascii && composing.length() >= 2 && composing.toString().matches("[A-Za-z]+")) {
            composing.append(text); forceEnglish = true; forceChinese = false;
            InputConnection ic = getCurrentInputConnection(); if (ic != null) ic.setComposingText(composing,1);
            updateCandidates(); return;
        }
        autoUndo = null; rejectedAutoCode = "";
        cancelVoice(); invalidateReselection(); restoredCandidate = null;
        finishLiteral(); InputConnection ic = getCurrentInputConnection(); if (ic != null) ic.commitText(text, 1);
        updateCandidates();
    }

    private void delete() {
        swipeSelection.reset();
        if (voiceListening) { cancelVoice(); render(); }
        invalidateReselection(); restoredCandidate = null;
        if (emojiSearch) { if (!emojiQuery.isEmpty()) emojiQuery = emojiQuery.substring(0, emojiQuery.length()-1); refreshEmoji(); return; }
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        if (undoAutocorrect(ic)) return;
        if (editMode && textEditor.selecting) {
            textEditor.reset();
            if (editorSelect != null) { editorSelect.setSelected(false); editorSelect.setTextColor(fg); }
        }
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
            default: return "換行";
        }
    }

    private void enter() {
        invalidateReselection();
        if (emojiSearch) { emojiSearch = false; render(); return; }
        if (composing.length() > 0) { finishLiteral(); return; }
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return;
        if (!sendDefaultEditorAction(true)) ic.commitText("\n", 1);
    }

    private void picker() { cancelVoice(); invalidateReselection(); finishLiteral(); ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker(); }
    private void resetComposition() { autoUndo = null; rejectedAutoCode = ""; candidateGeneration.incrementAndGet(); forceEnglish = forceChinese = false; restoredCandidate = null; expanded = false; emojiSearch = false; emojiQuery = ""; composing.setLength(0); candidates = Collections.emptyList(); consumedCodes.clear(); candidatePage = 0; chooseFirst = false; }
    private void sendKey(int keyCode) { InputConnection ic = getCurrentInputConnection(); if (ic != null) {
        ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, keyCode)); ic.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, keyCode));
    } }

    private final Runnable repeatDelete = new Runnable() {
        @Override public void run() { delete(); handler.postDelayed(this, 65); }
    };
    private void stopRepeat() { handler.removeCallbacks(repeatDelete); handler.removeCallbacks(repeatEditing); editingAction = null; }

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
                        if (!moved && Math.abs(event.getX() - startX) > dp(18)) { moved = true; prepareCursorSwipe(); }
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
        if (voiceSupportTimeout != null) { handler.removeCallbacks(voiceSupportTimeout); voiceSupportTimeout = null; }
        if (voiceDialog != null) { voiceDialog.dismiss(); voiceDialog = null; }
        if (voiceRecognizer != null) {
            SpeechRecognizer old = voiceRecognizer; voiceRecognizer = null;
            try { old.cancel(); } catch (RuntimeException ignored) { }
            try { old.destroy(); } catch (RuntimeException ignored) { }
        }
    }

    private void voice() {
        if (voiceListening) { cancelVoice(); render(); return; }
        if (noLearning || numeric || getCurrentInputConnection() == null) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            startActivity(new Intent(this, VoicePermissionActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            return;
        }
        startVoice(prefs.getBoolean("voice_offline_only", false));
    }

    private void voiceRecovery(String reason) {
        if (destroyed || noLearning || numeric || !isInputViewShown() || getCurrentInputConnection() == null) return;
        final InputConnection editor = getCurrentInputConnection();
        final int session = voiceSession;
        android.app.AlertDialog.Builder builder = new android.app.AlertDialog.Builder(this)
            .setTitle("語音輸入")
            .setMessage(reason + "\n\n你已開啟只用裝置內辨識。可在設定關閉此選項，或今次用手機預設語音服務；該服務可能透過網絡處理語音。鍵盤唔會儲存錄音，亦唔會自動轉用網上辨識。")
            .setNegativeButton("取消", null)
            .setNeutralButton("語音設定", (dialog, which) -> {
                try { startActivity(new Intent("android.settings.VOICE_INPUT_SETTINGS").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); }
                catch (ActivityNotFoundException unavailable) {
                    startActivity(new Intent(android.provider.Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                }
            });
        if (SpeechRecognizer.isRecognitionAvailable(this)) builder.setPositiveButton("今次用系統語音", (dialog, which) -> {
            if (session == voiceSession && editor == getCurrentInputConnection() && isInputViewShown() && !noLearning)
                startVoice(false);
        });
        voiceDialog = builder.create();
        Window window = voiceDialog.getWindow();
        if (window == null || getWindow() == null) { voiceDialog = null; return; }
        WindowManager.LayoutParams attributes = window.getAttributes();
        attributes.type = WindowManager.LayoutParams.TYPE_APPLICATION_ATTACHED_DIALOG;
        attributes.token = getWindow().getWindow().getDecorView().getWindowToken();
        window.setAttributes(attributes);
        window.addFlags(WindowManager.LayoutParams.FLAG_ALT_FOCUSABLE_IM);
        final android.app.AlertDialog shown = voiceDialog;
        shown.setOnDismissListener(dialog -> { if (voiceDialog == shown) voiceDialog = null; });
        try { voiceDialog.show(); }
        catch (WindowManager.BadTokenException exception) {
            voiceDialog = null; Toast.makeText(this, reason, Toast.LENGTH_LONG).show();
        }
    }

    private void startVoice(boolean onDevice) {
        if (noLearning || numeric || destroyed || !isInputViewShown() || getCurrentInputConnection() == null) return;
        cancelVoice();
        if (onDevice && (Build.VERSION.SDK_INT < 31 || !SpeechRecognizer.isOnDeviceRecognitionAvailable(this))) {
            voiceRecovery("手機未有可用嘅裝置內語音辨識服務。"); return;
        }
        finishLiteral();
        final int session = ++voiceSession;
        final InputConnection editor = getCurrentInputConnection();
        final boolean englishVoice = ascii;
        try { voiceRecognizer = onDevice ? SpeechRecognizer.createOnDeviceSpeechRecognizer(this) : SpeechRecognizer.createSpeechRecognizer(this); }
        catch (RuntimeException exception) {
            cancelVoice();
            if (onDevice) voiceRecovery("未能連接裝置內語音辨識服務。");
            else Toast.makeText(this, "未能連接系統語音服務；請檢查語音設定", Toast.LENGTH_LONG).show();
            return;
        }
        voiceListening = true;
        final Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, englishVoice ? "en-HK" : "yue-HK");
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, onDevice);
        intent.putExtra("android.speech.extra.MASK_OFFENSIVE_WORDS", false);
        final boolean[] triedAlternate = {false};
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
                String alternate = VoicePolicy.alternate(intent.getStringExtra(RecognizerIntent.EXTRA_LANGUAGE), englishVoice);
                if (!triedAlternate[0] && alternate != null &&
                    (error == SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED || error == SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE)) {
                    triedAlternate[0] = true;
                    intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, alternate);
                    handler.postDelayed(() -> listenVoice(session, intent, onDevice), 150);
                    return;
                }
                cancelVoice(); render();
                if (onDevice && VoicePolicy.recovery(error)) voiceRecovery(VoicePolicy.error(error));
                else Toast.makeText(KaiboardService.this, VoicePolicy.error(error), Toast.LENGTH_LONG).show();
            }
            @Override public void onResults(Bundle results) {
                if (session != voiceSession) return;
                ArrayList<String> texts = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                boolean sameEditor = editor == getCurrentInputConnection() && isInputViewShown() && !noLearning;
                cancelVoice();
                if (sameEditor && texts != null && !texts.isEmpty()) insert(texts.get(0));
                render();
            }
        });
        render();
        if (onDevice && Build.VERSION.SDK_INT >= 33) {
            final boolean[] started = {false};
            voiceSupportTimeout = () -> {
                if (session == voiceSession && !started[0]) {
                    started[0] = true; listenVoice(session, intent, onDevice);
                }
            };
            handler.postDelayed(voiceSupportTimeout, 3500);
            try {
                voiceRecognizer.checkRecognitionSupport(intent, handler::post, new RecognitionSupportCallback() {
                    @Override public void onSupportResult(RecognitionSupport support) {
                        if (session != voiceSession || started[0]) return;
                        started[0] = true; handler.removeCallbacks(voiceSupportTimeout); voiceSupportTimeout = null;
                        List<String> languages = new ArrayList<>(support.getInstalledOnDeviceLanguages());
                        if (!onDevice) languages.addAll(support.getOnlineLanguages());
                        String language = VoicePolicy.language(englishVoice, languages);
                        if (language == null && onDevice) {
                            cancelVoice(); render();
                            voiceRecovery("手機未有可用嘅" + (englishVoice ? "英文" : "廣東話") + "離線語音模型；請在語音設定檢查語言支援。");
                        } else {
                            if (language != null) intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, language);
                            listenVoice(session, intent, onDevice);
                        }
                    }
                    @Override public void onError(int error) {
                        if (session != voiceSession || started[0]) return;
                        started[0] = true; handler.removeCallbacks(voiceSupportTimeout); voiceSupportTimeout = null;
                        // Some OEM services implement recognition but cannot answer support queries.
                        listenVoice(session, intent, onDevice);
                    }
                });
            } catch (RuntimeException exception) {
                if (!started[0]) { started[0] = true; handler.removeCallbacks(voiceSupportTimeout); voiceSupportTimeout = null; listenVoice(session, intent, onDevice); }
            }
        } else listenVoice(session, intent, onDevice);
    }

    private void listenVoice(int session, Intent intent, boolean onDevice) {
        if (session != voiceSession || voiceRecognizer == null || noLearning || !isInputViewShown()) return;
        try { voiceRecognizer.startListening(intent); }
        catch (RuntimeException exception) {
            cancelVoice(); render();
            if (onDevice) voiceRecovery("未能啟動裝置內語音辨識服務。");
            else Toast.makeText(this, "未能啟動系統語音服務；請檢查咪高峰權限及語音設定", Toast.LENGTH_LONG).show();
        }
    }

    private void invalidateReselection() {
        reselection = null; reselectionLearned = false;
        reselectionPhrases = Collections.emptyList();
        if (undoKey != null) { undoKey.setEnabled(false); undoKey.setAlpha(.35f); }
    }

    private boolean canReselect() {
        if (reselection == null || secure || composing.length() > 0) return false;
        InputConnection ic = getCurrentInputConnection(); if (ic == null) return false;
        ExtractedText text = ic.getExtractedText(new ExtractedTextRequest(), 0);
        return text != null && reselection.valid(text.startOffset + text.selectionStart,
            text.startOffset + text.selectionEnd, ic.getTextBeforeCursor(128, 0));
    }

    private void reselect() {
        if (!canReselect()) { invalidateReselection(); return; }
        ReselectionRecord record = reselection;
        boolean undoLearning = reselectionLearned;
        List<String> undoPhrases = reselectionPhrases;
        InputConnection ic = getCurrentInputConnection();
        invalidateReselection(); cancelVoice();
        ic.beginBatchEdit();
        boolean selected = ic.setSelection(record.cursor - record.candidate.text.length(), record.cursor);
        boolean accepted = selected && ic.setComposingText(record.candidate.source, 1);
        if (accepted) {
            composing.setLength(0); composing.append(record.candidate.source);
            restoredCandidate = record.candidate; chooseFirst = false; forceEnglish = forceChinese = false;
        }
        ic.endBatchEdit();
        if (accepted) {
            if (undoLearning) for (String word : undoPhrases) {
                String key = PhraseLearning.key(word);
                int count = learned.getInt(key, 0);
                if (count <= 1) learned.edit().remove(key).apply();
                else learned.edit().putInt(key, count - 1).apply();
            }
            if (undoLearning) for (InputCandidate.Segment segment : record.candidate.segments) {
                if (segment.translated || segment.code.isEmpty()) continue;
                if (segment.english) {
                    int count = englishLearned.getInt(segment.text,0);
                    if (count <= 1) englishLearned.edit().remove(segment.text).apply();
                    else englishLearned.edit().putInt(segment.text,count-1).apply();
                } else if (LearningRanker.isLearnable(segment.text)) {
                    String key = LearningRanker.key(segment.code,quick,cangjie,segment.text);
                    int count = learned.getInt(key,0);
                    if (count <= 1) learned.edit().remove(key).apply(); else learned.edit().putInt(key,count-1).apply();
                }
            }
            expanded = false; render();
        }
    }

    private void prepareCursorSwipe() {
        cancelVoice(); stopRepeat(); dismissSelectionPopup(); invalidateReselection(); restoredCandidate = null;
        InputConnection ic = getCurrentInputConnection();
        if (ic != null && composing.length() > 0) ic.finishComposingText();
        resetComposition(); updateCandidates();
    }

    private void prepareSelectionSwipe() {
        prepareCursorSwipe();
        if (!swipeSelection.begin(getCurrentInputConnection()))
            Toast.makeText(this, "此輸入欄未支援掃動選字，請使用文字編輯", Toast.LENGTH_SHORT).show();
    }

    private void moveCursor(int steps) {
        swipeSelection.reset();
        int direction = steps < 0 ? KeyEvent.KEYCODE_DPAD_LEFT : KeyEvent.KEYCODE_DPAD_RIGHT;
        for (int i = 0; i < Math.abs(steps); i++) sendKey(direction);
    }

    private void dismissSelectionPopup() {
        if (selectionPopup != null) { selectionPopup.dismiss(); selectionPopup = null; }
    }

    private void popupChoices(View anchor, List<String> labels, java.util.function.IntConsumer selected) {
        dismissSelectionPopup();
        LinearLayout items = new LinearLayout(this); items.setOrientation(LinearLayout.VERTICAL);
        items.setPadding(dp(6), dp(6), dp(6), dp(6)); items.setBackground(background(functionColor));
        for (int i = 0; i < labels.size(); i++) {
            final int index = i;
            TextView item = new TextView(this); item.setText(labels.get(i)); item.setTextColor(fg); item.setTextSize(18);
            item.setPadding(dp(14), dp(10), dp(14), dp(10)); item.setMinHeight(dp(44));
            item.setContentDescription(labels.get(i));
            item.setOnClickListener(v -> { dismissSelectionPopup(); selected.accept(index); });
            items.addView(item, new LinearLayout.LayoutParams(-1, -2));
        }
        ScrollView scroll = new ScrollView(this); scroll.addView(items);
        int width = Math.min(getResources().getDisplayMetrics().widthPixels - dp(16), dp(330));
        selectionPopup = new PopupWindow(scroll, width, Math.min(dp(260), dp(12 + labels.size() * 52)), false);
        selectionPopup.setBackgroundDrawable(background(functionColor)); selectionPopup.setOutsideTouchable(true);
        selectionPopup.setElevation(dp(8));
        selectionPopup.showAtLocation(root, Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL, 0, Math.max(dp(60), root.getHeight()/2));
    }

    private void candidateMenu(View anchor, InputCandidate candidate) {
        if (candidate == null || secure) return;
        String key = pinPrefix(candidate.effectiveCode()) + candidate.text;
        boolean pinned = !noLearning && personal.contains(key);
        List<String> labels = new ArrayList<>(); labels.add("分段改選");
        if (candidate.corrected) labels.set(0, "修正字碼「" + candidate.effectiveCode() + "」・分段改選");
        if (!noLearning) labels.add(pinned ? "取消置頂" : "置頂此候選");
        popupChoices(anchor, labels, which -> {
            if (which == 0) segmentMenu(anchor, candidate);
            else {
                if (!pinned && personal.getAll().size() >= 500) {
                    Toast.makeText(this, "請先刪除部分自訂詞或置頂記錄", Toast.LENGTH_SHORT).show(); return;
                }
                if (pinned) personal.edit().remove(key).apply(); else personal.edit().putString(key, candidate.text).apply();
                updateCandidates();
            }
        });
    }

    private void segmentMenu(View anchor, InputCandidate candidate) {
        List<String> labels = new ArrayList<>();
        List<Integer> indexes = new ArrayList<>();
        for (int i=0;i<candidate.segments.size();i++) if (!candidate.segments.get(i).code.isEmpty()) {
            indexes.add(i); labels.add((i+1) + " · " + candidate.segments.get(i).text);
        }
        popupChoices(anchor, labels, index -> segmentChoices(anchor, candidate, indexes.get(index)));
    }

    private void segmentChoices(View anchor, InputCandidate candidate, int index) {
        InputCandidate.Segment segment = candidate.segments.get(index);
        LinkedHashSet<String> choices = new LinkedHashSet<>(); choices.add(segment.text);
        if(segment.translated && englishChineseEngine!=null) {
            choices.add(segment.code);choices.addAll(englishChineseEngine.lookup(segment.code));
        } else if (segment.english && englishEngine != null)
            choices.addAll(englishEngine.suggest(segment.code, personalEnglish(), prefs.getBoolean("english_repair", true)));
        else if (dictionary != null) {
            List<String> values = dictionary.lookup(segment.code, quick, cangjie, false); values.remove(segment.code);
            choices.addAll(values);
        }
        List<String> labels = new ArrayList<>(choices);
        popupChoices(anchor, labels, which -> {
            InputCandidate revised = candidate.replace(index, labels.get(which));
            candidateDetails.put(revised.text, revised);
            commitDetail(revised, true);
        });
    }

    private void punctuation(View anchor) {
        List<String> values = Arrays.asList("？", "！", "、", "：", "；", "「", "」", "『", "』", "（", "）", "…", "?", "!", "\"", "'", "(", ")");
        popupChoices(anchor, values, which -> insert(values.get(which)));
    }

    private void systemTool(String name) {
        Toast.makeText(this, "請選擇 Samsung Keyboard，再使用" + name + "功能", Toast.LENGTH_LONG).show();
        picker();
    }

    private TextView tool(LinearLayout parent, String icon, String label, Runnable action, boolean selected) {
        KeyboardKey button = new KeyboardKey(this); button.icon(icon);
        button.setTextColor(selected ? accent : muted); button.setContentDescription(label);
        button.setBackground(selected ? background(dark ? 0xFF344760 : 0xFFB8CBE0) : background(bg));
        button.setOnClickListener(v -> { if (voiceListening && !icon.equals("mic")) cancelVoice(); action.run(); });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,dp(44),1);
        lp.setMargins(dp(3),dp(3),dp(3),dp(3)); parent.addView(button,lp); return button;
    }

    private void renderExpandedCandidates() {
        if (expandedScroll == null) {
            expandedScroll = new ScrollView(this);
            expandedScroll.setOnTouchListener((v,e) -> { if(e.getActionMasked()==MotionEvent.ACTION_DOWN)freezeSemantic(); return false; });
            panel.addView(expandedScroll,new LinearLayout.LayoutParams(-1,dp(210)));
        }
        expandedScroll.removeAllViews();
        LinearLayout content = new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL);
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.CENTER_VERTICAL);
        // Align the key bounds, rather than the baselines of differently sized labels.
        actions.setBaselineAligned(false);
        expandedMode = expandedAction(actions, ascii || englishIntent() ? "中文" : "英文", this::toggleLanguage);
        expandedMode.setContentDescription("指定英文段或返回自動判斷");
        if (quick && prefs.getBoolean("continuous", true) && composing.length() > 2) {
            expandedAction(actions, chooseFirst ? "返回整句候選" : "逐字選擇",
                () -> { chooseFirst = !chooseFirst; updateCandidates(); });
        }
        content.addView(actions);
        android.widget.GridLayout grid = new android.widget.GridLayout(this); grid.setColumnCount(5);
        for (String value : candidates) {
            TextView item = new TextView(this); item.setText(value); item.setTextSize(21); item.setTextColor(fg);
            item.setGravity(Gravity.CENTER); item.setPadding(dp(5),dp(10),dp(5),dp(10));
            android.widget.GridLayout.LayoutParams lp = new android.widget.GridLayout.LayoutParams();
            lp.width = 0; lp.columnSpec = android.widget.GridLayout.spec(android.widget.GridLayout.UNDEFINED,1f);
            grid.addView(item,lp); item.setOnClickListener(v -> commit(value));
            item.setOnTouchListener((v,event) -> { if(event.getActionMasked()==MotionEvent.ACTION_DOWN)freezeSemantic(); return false; });
            if (composing.length() > 0) item.setOnLongClickListener(v -> { candidateMenu(item, candidateDetails.get(value)); return true; });
        }
        content.addView(grid); expandedScroll.addView(content);
    }

    private TextView expandedAction(LinearLayout parent, String label, Runnable action) {
        TextView button = key(parent, label, 1, true, action, 44);
        button.setTextSize(16);
        button.setSingleLine(true);
        button.setGravity(Gravity.CENTER);
        return button;
    }

    private String recentEmoji() {
        return noLearning || !prefs.getBoolean("emoji_recent",false) ? "" : prefs.getString("recent_emoji","");
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
        if(!noLearning && prefs.getBoolean("emoji_recent",false))
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
        float horizontalInset = splitLayout() ? foldWidth() * .0055f : 2.5f;
        button.faceInset(horizontalInset);
        button.referenceEditingIcons(coverReferenceLayout());
        button.setBackground(new android.graphics.drawable.InsetDrawable(background(special ? functionColor : keyColor, coverReferenceLayout() ? height * .16f : 7), dp(horizontalInset), dp(4), dp(horizontalInset), dp(4))); button.setFocusable(true);
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
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(height) + dp(8), weight);
        parent.addView(button, params); return button;
    }

    private android.graphics.drawable.Drawable background(int color) {
        return background(color, 7);
    }
    private android.graphics.drawable.Drawable background(int color, float radius) {
        GradientDrawable shape = new GradientDrawable(); shape.setColor(color); shape.setCornerRadius(dp(radius));
        return new android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(dark ? 0x40FFFFFF : 0x22000000), shape, null);
    }

    private int keyHeight() {
        if (splitLayout()) {
            // Samsung Fold reference: letter face height is about 5.5% of the unfolded width.
            float preferenceScale = Integer.parseInt(prefs.getString("height", "44")) / 40f;
            return Math.round(Math.max(34, Math.min(48, foldWidth() * .055f)) * preferenceScale);
        }
        if (coverReferenceLayout()) {
            // Cover reference 133914.jpg: roughly 140-high / 110-wide letter faces.
            // Preserve all row weights, codes and positions; derive height from the ten-key row.
            float faceWidth = (foldWidth() - 8f) / 10f - 5f;
            float preferenceScale = Integer.parseInt(prefs.getString("height", "44")) / 44f;
            return Math.round(Math.max(40, Math.min(60, faceWidth * (140f / 110f))) * preferenceScale);
        }
        return getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE && !splitLayout() ? 40 : Integer.parseInt(prefs.getString("height", "44"));
    }
    private boolean coverReferenceLayout() {
        return getResources().getConfiguration().screenWidthDp < 600
            && getResources().getConfiguration().orientation == Configuration.ORIENTATION_PORTRAIT
            && prefs.getString("hand", "full").equals("full")
            && !numeric && !symbols && !emoji;
    }
    private int foldWidth() {
        return getResources().getConfiguration().screenWidthDp;
    }
    private void splitGap(LinearLayout line) {
        // 19% gap plus the two key-face insets matches the central opening in the reference.
        line.addView(new View(this), new LinearLayout.LayoutParams(dp(foldWidth() * .19f), 1));
    }
    private boolean splitLayout() {
        return prefs.getBoolean("split", true) && prefs.getString("hand", "full").equals("full")
            && getResources().getConfiguration().screenWidthDp >= 600;
    }
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
