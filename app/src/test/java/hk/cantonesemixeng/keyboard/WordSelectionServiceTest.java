package hk.cantonesemixeng.keyboard;

import android.content.SharedPreferences;
import android.view.inputmethod.*;
import org.junit.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import static org.junit.Assert.*;

/** Actual service commit/reselection path with an editor protocol and isolated in-memory preferences. */
public class WordSelectionServiceTest {
    private static DictionaryEngine dictionary;
    private static WordLexicon words;
    private Service service;
    private Editor editor;
    private Map<String,Object> settings,counts,recent,rejected;
    private static class Service extends CantoneseMixEngKeyboardService {
        InputConnection editor;
        @Override public InputConnection getCurrentInputConnection(){return editor;}
    }
    @BeforeClass public static void dictionary() throws Exception {
        dictionary=new DictionaryEngine(new FileReader("src/main/assets/cangjie5.base.dict.yaml"),new StringReader("hello\n"));
        words=new WordLexicon(dictionary,new StringReader("你好\t30000\n人類\t3000\n"));
    }
    @Before public void setup() throws Exception {
        service=new Service();editor=new Editor();service.editor=editor.connection;
        settings=new HashMap<>();settings.put("learning",true);
        counts=new HashMap<>();recent=new HashMap<>();rejected=new HashMap<>();
        put("prefs",preferences(settings));put("learned",preferences(counts));put("recentLearned",preferences(recent));
        put("rejectedLearned",preferences(rejected));put("personal",preferences(new HashMap<>()));
        put("englishLearned",preferences(new HashMap<>()));put("dictionary",dictionary);put("wordLexicon",words);
        put("candidateGlyphs",new CandidateGlyphFilter(cp->true));put("quick",true);put("cangjie",true);
    }
    private void put(String name,Object value)throws Exception {Field f=CantoneseMixEngKeyboardService.class.getDeclaredField(name);f.setAccessible(true);f.set(service,value);}
    private Object get(String name)throws Exception {Field f=CantoneseMixEngKeyboardService.class.getDeclaredField(name);f.setAccessible(true);return f.get(service);}
    private void call(String name,Class<?>[] types,Object...args)throws Exception {
        Method m=CantoneseMixEngKeyboardService.class.getDeclaredMethod(name,types);m.setAccessible(true);
        try{m.invoke(service,args);}catch(InvocationTargetException e){throw new AssertionError(e.getCause());}
    }
    private void compose(String code)throws Exception {
        StringBuilder composing=(StringBuilder)get("composing");composing.setLength(0);composing.append(code);
        editor.connection.setComposingText(code,1);
    }
    private void commit(String code,String text,boolean learn)throws Exception {
        call("commitDetail",new Class<?>[]{InputCandidate.class,boolean.class},InputCandidate.chinese(dictionary,code,text),learn);
    }
    @Test public void explicitWordLearnsWholeCodeOnceAndImmediateDeleteWithdrawsIt() throws Exception {
        compose("ofvd");commit("ofvd","你好",true);
        assertEquals("你好",editor.text);assertEquals(1,counts.get("U:QC:ofvd:你好"));assertEquals(1,counts.get("W:你好"));
        assertFalse(counts.containsKey("QC:of:你"));
        call("delete",new Class<?>[]{});
        assertEquals("你",editor.text);assertTrue(counts.isEmpty());assertTrue(recent.isEmpty());
    }
    @Test public void rejectedEditorCommitNeverLearnsOrConsumesCode() throws Exception {
        compose("ofvd");editor.accept=false;commit("ofvd","你好",true);
        assertEquals("ofvd",editor.text);assertEquals("ofvd",get("composing").toString());assertTrue(counts.isEmpty());
    }
    @Test public void stickySingleSelectionsDoNotLearnTheReconstructedWord() throws Exception {
        put("chooseFirst",true);compose("ofvd");commit("of","你",true);commit("vd","好",true);
        assertEquals("你好",editor.text);assertEquals(true,get("chooseFirst"));
        assertEquals(new HashSet<>(Arrays.asList("QC:of:你","QC:vd:好")),counts.keySet());
    }
    @Test public void reselectionWithdrawsOldUsageAndRecordsOnlyReplacement() throws Exception {
        compose("of");commit("of","你",true);call("reselect",new Class<?>[]{});
        assertTrue(counts.isEmpty());assertEquals("of",editor.text);
        commit("of","係",true);
        assertFalse(counts.containsKey("QC:of:你"));assertEquals(1,counts.get("QC:of:係"));assertTrue(rejected.containsKey("QC:of:你"));
    }
    @Test public void protectedAndDisabledLearningDoNotReadOrWriteUsage() throws Exception {
        counts.put("QC:of:係",7);put("noLearning",true);compose("of");commit("of","你",true);
        assertEquals(Collections.singletonMap("QC:of:係",7),counts);assertTrue(recent.isEmpty());
        put("noLearning",false);settings.put("learning",false);compose("of");commit("of","你",true);
        assertEquals(Collections.singletonMap("QC:of:係",7),counts);
    }
    @Test public void topOutIsOnByDefaultUsesPersonalOrderAndDoesNotTrainItself() throws Exception {
        counts.put("QC:of:係",7);compose("of");call("maybeTopOut",new Class<?>[]{char.class},'z');
        assertEquals("係",editor.text);assertEquals("",get("composing").toString());
        assertEquals(Collections.singletonMap("QC:of:係",7),counts);assertTrue(recent.isEmpty());
    }
    @Test public void switchOffSingleModeAndHotPrefixPreventTopOut() throws Exception {
        compose("of");settings.put("quick_top_out",false);call("maybeTopOut",new Class<?>[]{char.class},'z');assertEquals("of",editor.text);
        settings.put("quick_top_out",true);put("chooseFirst",true);call("maybeTopOut",new Class<?>[]{char.class},'z');assertEquals("of",editor.text);
        put("chooseFirst",false);call("maybeTopOut",new Class<?>[]{char.class},'c');assertEquals("of",editor.text);
    }
    @Test public void lowFrequencyLearnedSpellingHoldsItsIncompletePrefix() throws Exception {
        put("wordLexicon",new WordLexicon(dictionary,new StringReader("返工\t100\n")));
        counts.put("U:QC:yemm:返工",1);compose("ye");call("maybeTopOut",new Class<?>[]{char.class},'m');assertEquals("ye",editor.text);
        counts.clear();call("maybeTopOut",new Class<?>[]{char.class},'m');assertNotEquals("ye",editor.text);
    }
    @Test public void englishPrefixAndCangjieOnlyAreNotCutByQuickTopOut() throws Exception {
        put("englishEngine",new EnglishEngine(new StringReader("hello\n")));compose("he");call("maybeTopOut",new Class<?>[]{char.class},'l');assertEquals("he",editor.text);
        put("quick",false);compose("on");call("maybeTopOut",new Class<?>[]{char.class},'f');assertEquals("on",editor.text);
    }
    private List<String> candidates() throws Exception {
        Class<?> type=Arrays.stream(CantoneseMixEngKeyboardService.class.getDeclaredClasses())
            .filter(c->c.getSimpleName().equals("CandidateRequest")).findFirst().orElseThrow();
        Constructor<?> constructor=type.getDeclaredConstructor(CantoneseMixEngKeyboardService.class);constructor.setAccessible(true);
        Object request=constructor.newInstance(service);
        call("computeCandidates",new Class<?>[]{type},request);
        Field values=type.getDeclaredField("values");values.setAccessible(true);
        @SuppressWarnings("unchecked") List<String> result=(List<String>)values.get(request);return result;
    }
    @Test public void defaultCandidatesUseScopedUsageAndKeepAllSameCodeChoices() throws Exception {
        editor.connection.commitText("上文",1);compose("of");List<String> original=candidates();
        counts.put("QC:of:係",7);assertEquals("係",candidates().get(0));
        assertTrue(candidates().containsAll(original));
        counts.clear();counts.put(ContextLearning.key("of","上文","係"),1000);
        assertEquals(original,candidates());
    }
    @Test public void legacyGlobalWordCountsDoNotBecomeNewSpellingUsage() throws Exception {
        compose("ofvd");List<String> original=candidates();counts.put("W:你好",9999);
        assertEquals(original,candidates());
        settings.put("learning",false);counts.put("QC:of:係",9999);compose("of");
        List<String> disabled=candidates();counts.clear();assertEquals(disabled,candidates());
    }
    @Test public void failedDeletionDoesNotWithdrawConfirmedLearning() throws Exception {
        compose("of");commit("of","你",true);editor.accept=false;call("delete",new Class<?>[]{});
        assertEquals(1,counts.get("QC:of:你"));assertEquals("你",editor.text);
    }
    private void topOutWithFollowingKey() throws Exception {
        counts.put("QC:of:係",7);compose("of");call("typeLetter",new Class<?>[]{char.class},'z');
        assertEquals("係z",editor.text);
    }
    @Test public void backspaceRestoresTopOutAndRetainsTheNextKeyWithoutLearning() throws Exception {
        topOutWithFollowingKey();call("delete",new Class<?>[]{});
        assertEquals("ofz",editor.text);assertEquals("ofz",get("composing").toString());
        assertEquals(Collections.singletonMap("QC:of:係",7),counts);assertTrue(recent.isEmpty());assertTrue(rejected.isEmpty());
        call("typeLetter",new Class<?>[]{char.class},'x');assertEquals("ofzx",editor.text);
        call("delete",new Class<?>[]{});assertEquals("ofz",editor.text);
    }
    @Test public void reselectAlsoRestoresTheAutomaticCommitWhileRawKeysRemain() throws Exception {
        topOutWithFollowingKey();call("reselect",new Class<?>[]{});assertEquals("ofz",editor.text);
        assertFalse((Boolean)get("chooseFirst"));
    }
    @Test public void multipleAutomaticPairsAndOddTrailingKeysAreRestoredTogether() throws Exception {
        put("wordLexicon",new WordLexicon(dictionary,new StringReader("")));
        compose("ofvdv");call("typeLetter",new Class<?>[]{char.class},'z');
        assertTrue(editor.text.endsWith("vz"));assertEquals("vz",get("composing").toString());
        call("delete",new Class<?>[]{});assertEquals("ofvdvz",editor.text);assertTrue(counts.isEmpty());
    }
    @Test public void supplementaryCharacterUsesUtf16EditorOffsetsWhenRestored() throws Exception {
        put("wordLexicon",new WordLexicon(dictionary,new StringReader("")));
        counts.put("QC:rn:𠮩",8);compose("rn");call("typeLetter",new Class<?>[]{char.class},'z');
        assertEquals("𠮩z",editor.text);call("delete",new Class<?>[]{});assertEquals("rnz",editor.text);
        assertEquals(Collections.singletonMap("QC:rn:𠮩",8),counts);
    }
    @Test public void movedCursorOrEditedSuffixCannotRestoreUnrelatedText() throws Exception {
        topOutWithFollowingKey();editor.connection.setSelection(0,0);call("reselect",new Class<?>[]{});assertEquals("係z",editor.text);
        compose("of");call("typeLetter",new Class<?>[]{char.class},'z');
        editor.text=editor.text.replace("係","你");String unchanged=editor.text;
        call("reselect",new Class<?>[]{});assertEquals(unchanged,editor.text);
    }
    @Test public void refusingComposingRegionDoesNotFallThroughToDestructiveDelete() throws Exception {
        topOutWithFollowingKey();editor.acceptRegion=false;call("delete",new Class<?>[]{});
        assertEquals("係z",editor.text);assertEquals("z",get("composing").toString());
        editor.acceptRegion=true;call("delete",new Class<?>[]{});assertEquals("係",editor.text);
    }
    @Test public void refusingReplacementRestoresOriginalCompositionAndLeavesTextUntouched() throws Exception {
        topOutWithFollowingKey();editor.accept=false;call("delete",new Class<?>[]{});
        assertEquals("係z",editor.text);assertEquals(1,editor.start);assertEquals(2,editor.end);
        editor.accept=true;call("delete",new Class<?>[]{});assertEquals("係",editor.text);
    }
    @Test public void explicitSelectionEndsAutomaticUndoAndNewTextLearnsNormally() throws Exception {
        topOutWithFollowingKey();commit("z","重",true);
        assertEquals("係重",editor.text);assertEquals(1,counts.get("QC:z:重"));
        call("delete",new Class<?>[]{});assertEquals("係",editor.text);assertFalse(counts.containsKey("QC:z:重"));
    }
    @Test public void restoreWorksWithLearningOffAndLongEditorContext() throws Exception {
        settings.put("learning",false);editor.connection.commitText("香港".repeat(180),1);
        compose("of");call("typeLetter",new Class<?>[]{char.class},'z');call("delete",new Class<?>[]{});
        assertEquals("香港".repeat(180)+"ofz",editor.text);assertTrue(counts.isEmpty());assertTrue(recent.isEmpty());
    }
    @Test public void latestAutomaticChunkIsRestoredWithoutUndoingAnEarlierChunk() throws Exception {
        put("wordLexicon",new WordLexicon(dictionary,new StringReader("")));
        topOutWithFollowingKey();compose("vd");call("typeLetter",new Class<?>[]{char.class},'z');
        call("delete",new Class<?>[]{});assertEquals("係vdz",editor.text);
    }
    private static SharedPreferences preferences(Map<String,Object> values) {
        SharedPreferences.Editor edit=(SharedPreferences.Editor)Proxy.newProxyInstance(SharedPreferences.Editor.class.getClassLoader(),new Class<?>[]{SharedPreferences.Editor.class},(p,m,a)->{
            switch(m.getName()) {
                case "putInt":case "putString":case "putBoolean":values.put((String)a[0],a[1]);return p;
                case "remove":values.remove(a[0]);return p;case "clear":values.clear();return p;case "apply":return null;case "commit":return true;
                default:throw new AssertionError(m.getName());
            }
        });
        return (SharedPreferences)Proxy.newProxyInstance(SharedPreferences.class.getClassLoader(),new Class<?>[]{SharedPreferences.class},(p,m,a)->{
            switch(m.getName()) {
                case "getAll":return new HashMap<>(values);case "contains":return values.containsKey(a[0]);case "edit":return edit;
                case "getInt":case "getString":case "getBoolean":return values.getOrDefault(a[0],a[1]);default:throw new AssertionError(m.getName());
            }
        });
    }
    private static class Editor {
        String text="";int cursor=0,selected=0,start=-1,end=-1;boolean accept=true,acceptRegion=true;
        final InputConnection connection=(InputConnection)Proxy.newProxyInstance(InputConnection.class.getClassLoader(),new Class<?>[]{InputConnection.class},(p,m,a)->{
            switch(m.getName()) {
                case "beginBatchEdit":case "endBatchEdit":return true;
                case "getTextBeforeCursor":return text.substring(Math.max(0,Math.min(selected,cursor)-(int)a[0]),Math.min(selected,cursor));
                case "getSelectedText":return text.substring(Math.min(selected,cursor),Math.max(selected,cursor));
                case "getExtractedText":ExtractedText e=new ExtractedText();e.text=text;e.selectionStart=selected;e.selectionEnd=cursor;return e;
                case "setSelection":selected=(int)a[0];cursor=(int)a[1];return true;
                case "finishComposingText":start=end=-1;return true;
                case "setComposingRegion":if(!acceptRegion)return false;start=(int)a[0];end=(int)a[1];return true;
                case "setComposingText":case "commitText":
                    if(!accept)return false;
                    int from=start>=0?start:Math.min(selected,cursor),to=end>=0?end:Math.max(selected,cursor);
                    String value=a[0].toString();text=text.substring(0,from)+value+text.substring(to);selected=cursor=from+value.length();
                    if(m.getName().equals("setComposingText")){start=from;end=cursor;}else start=end=-1;
                    return true;
                case "deleteSurroundingTextInCodePoints":case "deleteSurroundingText":
                    if(!accept)return false;
                    int before=(int)a[0];text=text.substring(0,Math.max(0,cursor-before))+text.substring(cursor);cursor=selected=Math.max(0,cursor-before);return true;
                case "sendKeyEvent":return false;
                default:throw new AssertionError(m.getName());
            }
        });
    }
}
