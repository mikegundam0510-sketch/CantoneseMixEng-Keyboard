package hk.kaiboard.android;

import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class QuickDecoderTest {
    private static DictionaryEngine dictionary;
    private static QuickDecoder decoder;
    private static Reader asset(String name) throws Exception { return new InputStreamReader(new FileInputStream("src/main/assets/" + name),StandardCharsets.UTF_8); }
    @BeforeClass public static void load() throws Exception {
        dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"));
        decoder = new QuickDecoder(dictionary,asset("quick_phrases.tsv"));
    }
    @Test public void usersExampleRanksCorrectPhraseFirst() {
        assertEquals("你好嗎", decoder.decode("ofvdrf", (c,w)->0).get(0));
        assertEquals(Arrays.asList("of","vd","rf"),dictionary.matchQuickCodes("ofvdrf","你好嗎"));
        assertTrue(dictionary.quickCandidates("rf").contains("喺"));
    }
    @Test public void commonPhrasesAreNotLimitedToExample() {
        assertEquals("你好",decoder.decode("ofvd",(c,w)->0).get(0));
        assertTrue(decoder.decode("haeu",(c,w)->0).contains("香港"));
        assertTrue(decoder.decode("rryo",(c,w)->0).contains("唔該"));
    }
    @Test public void oneCodeCharactersAndUnknownCombinationsRemainPossible() {
        assertEquals(Arrays.asList("a","b"),dictionary.matchQuickCodes("ab","日月"));
        assertFalse(decoder.decode("avdof",(c,w)->0).isEmpty());
        assertTrue(dictionary.matchQuickCodes("ofvd","你嗎").isEmpty());
    }
    @Test public void everyReturnedSentenceExactlyMatchesAllTypedCodes() {
        for (String code : Arrays.asList("ofvdrf","ofvd","haeu","rryo","abcdef","ofvdrfofvd","avdof"))
            for (String candidate : decoder.decode(code,(c,w)->0)) assertFalse(code+" / "+candidate, dictionary.matchQuickCodes(code,candidate).isEmpty());
    }
    @Test public void invalidAndShortInputDoesNotInventSentences() {
        assertTrue(decoder.decode("",(c,w)->0).isEmpty());
        assertTrue(decoder.decode("of",(c,w)->0).isEmpty());
        assertTrue(decoder.decode("of1",(c,w)->0).isEmpty());
        assertTrue(decoder.decode("z".repeat(49),(c,w)->0).isEmpty());
    }
    @Test public void alternativesAreDistinctAndBounded() {
        List<String> words = decoder.decode("ofvdrf",(c,w)->0);
        assertEquals(new HashSet<>(words).size(),words.size()); assertTrue(words.size()<=20);
    }
    @Test public void phraseLookupLatencyIsBounded() {
        long start = System.nanoTime();
        for(int i=0;i<10;i++) decoder.decode("ofvdrfofvdrfofvdrf",(c,w)->0);
        assertTrue("Unexpectedly expensive sentence search",(System.nanoTime()-start)/1000000 < 5000);
    }
}
