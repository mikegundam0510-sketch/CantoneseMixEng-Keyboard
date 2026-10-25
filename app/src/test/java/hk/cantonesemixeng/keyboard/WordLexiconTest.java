package hk.cantonesemixeng.keyboard;

import org.junit.*;
import java.io.*;
import java.util.*;
import static org.junit.Assert.*;

public class WordLexiconTest {
    private static DictionaryEngine dictionary;
    private static WordLexicon words;
    @BeforeClass public static void load() throws Exception {
        dictionary=new DictionaryEngine(new FileReader("src/main/assets/cangjie5.base.dict.yaml"),
            new StringReader("hello\noffice\n"),new FileReader("src/main/assets/character_frequencies.tsv"));
        words=new WordLexicon(dictionary,new StringReader("你好\t30000\n人類\t3000\n無錯\t25000\n中國\t30000\n返工\t100\n食飯\t30000\n香港\t40000\n"));
    }
    private List<InputCandidate> lookup(String code) {
        return words.candidates(code,true,true,true,false,(c,w)->0);
    }
    private InputCandidate find(String code,String text) {
        return lookup(code).stream().filter(c->c.text.equals(text)).findFirst().orElseThrow(()->new AssertionError(code+" / "+text));
    }
    @Test public void nativeOneAndTwoKeySpellingsBothReachAttestedWords() {
        assertEquals("ofc",find("ofc","人類").source);
        assertEquals("lwm",find("lwm","中國").source);
        assertEquals("ovoe",find("ovoe","食飯").source);
        assertEquals("ovxe",find("ovxe","食飯").source);
        assertEquals(Arrays.asList("ov","xe"),dictionary.matchQuickCodes("ovxe",find("ovxe","食飯").text));
    }
    @Test public void prefixSelectionRetainsUnconsumedKeysAndDoesNotInventSentence() {
        assertEquals("ofvd",find("ofvdovoe","你好").source);
        assertFalse(lookup("ofvdovoe").stream().anyMatch(c->c.text.equals("你好食飯")));
        assertTrue(lookup("ofvdovoe").stream().anyMatch(c->c.source.equals("of")&&c.text.equals("你")));
        assertTrue(words.candidates("ofvd",true,true,true,true,(c,w)->0).stream()
            .allMatch(c->c.text.codePointCount(0,c.text.length())==1&&c.source.length()<=2));
    }
    @Test public void usageReordersSameCodeWithoutLosingOtherCharacters() {
        List<InputCandidate> base=words.candidates("of",true,false,false,false,(c,w)->0);
        List<InputCandidate> learned=words.candidates("of",true,false,false,false,(c,w)->w.equals("係")?40:0);
        assertEquals("係",learned.get(0).text);
        assertEquals(new HashSet<>(base.stream().map(c->c.text).toList()),new HashSet<>(learned.stream().map(c->c.text).toList()));
    }
    @Test public void completeAndHotWordPrefixesHoldButUnrelatedKeysDoNot() {
        assertTrue(words.captures("ofc",(c,w)->0));
        assertTrue(words.captures("lwm",(c,w)->0));
        assertTrue(words.captures("ofv",(c,w)->0));
        assertFalse(words.captures("ofz",(c,w)->0));
        assertFalse(words.captures("yem",(c,w)->0));
        assertTrue(words.captures("yemm",(c,w)->w.equals("返工")?4:0));
    }
    @Test public void automaticChoicesUseUsageButEnglishAndKnownPrefixesArePreserved() throws Exception {
        assertEquals("係",WordTopOut.choices(dictionary,words,"of",'z',(c,w)->w.equals("係")?40:0,s->false).get(0).text);
        assertTrue(WordTopOut.choices(dictionary,words,"of",'c',(c,w)->0,s->false).isEmpty());
        EnglishEngine english=new EnglishEngine(new StringReader("hello\n"));
        assertTrue(WordTopOut.choices(dictionary,words,"he",'l',(c,w)->0,s->english.hasWordPrefix(s,Collections.emptyList())).isEmpty());
        assertTrue(WordTopOut.choices(dictionary,words,"OF",'z',(c,w)->0,s->false).isEmpty());
        assertTrue(WordTopOut.choices(dictionary,words,"of",'Z',(c,w)->0,s->false).isEmpty());
    }
    @Test public void associationsCompleteOnlyAttestedWordsAndCangjieStillWorks() {
        assertTrue(words.nextSuggestions("你",12,w->0).contains("好"));
        assertTrue(words.nextSuggestions("食",12,w->0).contains("飯"));
        assertTrue(words.nextSuggestions("你好",12,w->0).isEmpty());
        assertTrue(words.candidates("onf",false,true,false,false,(c,w)->0).stream().anyMatch(c->c.text.equals("你")));
        assertTrue(words.candidates("of:vd",true,true,true,false,(c,w)->0).isEmpty());
    }
}
