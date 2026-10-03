package hk.kaiboard.android;

import android.text.*;
import android.view.View;
import android.view.inputmethod.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.util.ReflectionHelpers;
import org.robolectric.util.ReflectionHelpers.ClassParameter;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.Assert.*;

/** Executes the IME's real composition/commit path against an in-memory Android editor. */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28)
public class KeyboardFlowTest {
    private KaiboardService service;
    private SpannableStringBuilder text;
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(reader("cangjie5.base.dict.yaml"), reader("english.txt"));
        decoder = new QuickDecoder(dictionary, reader("quick_phrases.tsv"));
    }
    private static Reader reader(String name) throws Exception {
        return new InputStreamReader(new FileInputStream("src/main/assets/" + name), StandardCharsets.UTF_8);
    }
    @Before public void setup() {
        service = Robolectric.buildService(KaiboardService.class).create().get();
        Prefs.get(service).edit().clear().commit();
        service.getSharedPreferences("learned", 0).edit().clear().commit();
        text = new SpannableStringBuilder(); Selection.setSelection(text, 0);
        InputConnection editor = new BaseInputConnection(new View(service), true) {
            @Override public Editable getEditable() { return text; }
        };
        ReflectionHelpers.setField(service, "mStartedInputConnection", editor);
        ReflectionHelpers.setField(service, "dictionary", dictionary);
        ReflectionHelpers.setField(service, "decoder", decoder);
        start(InputType.TYPE_CLASS_TEXT, 0);
    }
    private void start(int type, int options) {
        EditorInfo info = new EditorInfo(); info.inputType = type; info.imeOptions = options;
        ReflectionHelpers.setField(service, "mInputEditorInfo", info);
        service.onStartInput(info, false); service.onCreateInputView();
    }
    @After public void cleanup() { service.onDestroy(); }
    private void type(String value) {
        for (char c : value.toCharArray()) ReflectionHelpers.callInstanceMethod(service, "typeLetter", ClassParameter.from(char.class, c));
    }
    private void action(String name) { ReflectionHelpers.callInstanceMethod(service, name); }
    private void commit(String value) { ReflectionHelpers.callInstanceMethod(service, "commit", ClassParameter.from(String.class, value)); }
    private List<String> candidates() { return ReflectionHelpers.getField(service, "candidates"); }
    @Test public void continuousQuickCommitsSentenceOnceAndLearnsOnlyCharacters() {
        type("ofvdrf"); assertEquals("你好嗎", candidates().get(0));
        action("space"); assertEquals("你好嗎", text.toString());
        assertEquals("", ReflectionHelpers.<StringBuilder>getField(service, "composing").toString());
        Map<String, ?> learned = service.getSharedPreferences("learned", 0).getAll();
        assertEquals(3, learned.size());
        for (String key : learned.keySet()) assertFalse(key.contains("你好嗎"));
    }
    @Test public void choosingFirstCharacterRetainsRemainingComposition() {
        type("ofvdrf"); ReflectionHelpers.setField(service, "chooseFirst", true); action("updateCandidates");
        commit("你"); assertEquals("你vdrf", text.toString());
        assertEquals("vdrf", ReflectionHelpers.<StringBuilder>getField(service, "composing").toString());
        assertTrue(candidates().contains("好嗎")); action("space"); assertEquals("你好嗎", text.toString());
    }
    @Test public void englishModeSuggestsButSpacePreservesTypedSpelling() {
        ReflectionHelpers.setField(service, "ascii", true);
        type("teh"); assertTrue(candidates().contains("the"));
        action("space"); assertEquals("teh ", text.toString());
        type("hel"); assertTrue(candidates().contains("hello")); commit("hello");
        assertEquals("teh hello", text.toString());
    }
    @Test public void customShortcutIsExplicitAndSuppressedInPrivateEditors() {
        Prefs.get(service).edit().putString("custom_phrases", "hk\t香港 🇭🇰").commit();
        type("hk"); assertEquals("香港 🇭🇰", candidates().get(0)); commit("香港 🇭🇰");
        assertEquals("香港 🇭🇰", text.toString());
        assertTrue(service.getSharedPreferences("learned", 0).getAll().isEmpty());
        start(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
        type("hk"); assertFalse(candidates().contains("香港 🇭🇰"));
        action("finishLiteral"); assertTrue(service.getSharedPreferences("learned", 0).getAll().isEmpty());
    }
    @Test public void passwordTypesLiterallyWithoutCandidatesAndCompositionDeleteIsSafe() {
        start(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD, 0);
        type("of"); assertEquals("of", text.toString()); assertTrue(candidates().isEmpty());
        assertTrue(service.getSharedPreferences("learned", 0).getAll().isEmpty());
        start(InputType.TYPE_CLASS_TEXT, 0); type("vd"); action("delete");
        assertEquals("ofv", text.toString()); action("delete"); assertEquals("of", text.toString());
    }
    @Test public void expandedGridIncludesCandidatesBeyondFirstPageAndCommitsOnce() {
        type("mm"); assertTrue(candidates().size() > 30);
        ReflectionHelpers.setField(service, "expandedCandidates", true); action("render");
        android.widget.GridView grid = ReflectionHelpers.getField(service, "candidateGrid");
        assertNotNull(grid); assertEquals(candidates().size(), grid.getAdapter().getCount());
        String chosen = (String) grid.getAdapter().getItem(31);
        grid.performItemClick(grid.getAdapter().getView(31, null, grid), 31, 31);
        assertEquals(chosen, text.toString());
        assertFalse(ReflectionHelpers.<Boolean>getField(service, "expandedCandidates"));
    }
    @Test public void associationsAppendSuffixAndNeverRepeatPrefixOrAutoCommitOnSpace() {
        type("of"); commit("你"); assertTrue(candidates().contains("好嗎"));
        commit("好嗎"); assertEquals("你好嗎", text.toString());
        action("space"); assertEquals("你好嗎 ", text.toString()); assertTrue(candidates().isEmpty());
        assertEquals(1, service.getSharedPreferences("learned", 0).getAll().size());
    }
    @Test public void associationCanBeDisabledAndPrivateFieldsNeverShowIt() {
        Prefs.get(service).edit().putBoolean("association", false).commit();
        type("of"); commit("你"); assertTrue(candidates().isEmpty());
        Prefs.get(service).edit().putBoolean("association", true).commit();
        start(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
        type("of"); commit("你"); assertTrue(candidates().isEmpty());
        assertEquals("", ReflectionHelpers.<String>getField(service, "predictionContext"));
    }
    @Test public void hidingKeyboardClearsTransientAssociationContext() {
        type("of"); commit("你"); assertFalse(candidates().isEmpty());
        service.onFinishInputView(false);
        assertTrue(candidates().isEmpty());
        assertEquals("", ReflectionHelpers.<String>getField(service, "predictionContext"));
    }
}
