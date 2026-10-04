import hk.kaiboard.android.*;
import java.io.*;
import java.util.*;
import java.lang.management.ManagementFactory;

/** Separate JVM per measurement, same assets and heap limits for both revisions. */
public final class LoadingBenchmark {
    private static Reader asset(String name) throws Exception {
        return new InputStreamReader(new FileInputStream("app/src/main/assets/" + name), java.nio.charset.StandardCharsets.UTF_8);
    }
    public static void main(String[] args) throws Exception {
        long start = System.nanoTime();
        DictionaryEngine dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        EnglishEngine english = new EnglishEngine(asset("english.txt"));
        double basicMs = (System.nanoTime()-start)/1e6;
        QuickDecoder decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"), asset("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(new FileInputStream("app/src/main/assets/language_model.b64")));
        double fullMs = (System.nanoTime()-start)/1e6;
        System.gc(); Thread.sleep(100);
        long heap = Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory();
        com.sun.management.ThreadMXBean bean = (com.sun.management.ThreadMXBean)ManagementFactory.getThreadMXBean();
        bean.setThreadAllocatedMemoryEnabled(true);
        long thread = Thread.currentThread().getId(), before = bean.getThreadAllocatedBytes(thread);
        for (int i=0; i<100; i++) { english.likelyEnglish("hello", Collections.emptyList()); english.suggest("hellp", Collections.emptyList(), true); }
        long allocated = bean.getThreadAllocatedBytes(thread)-before;
        String[] codes = {"ofvd", "ofonaovrmrq", "hisuvmjuisgehr", "abcdef"};
        List<String> choices = new ArrayList<>();
        for (String code : codes) {
            List<String> values = decoder.decode(code, (c,w)->0);
            if (values.isEmpty()) throw new AssertionError("Missing candidates: " + code);
            for (String value : values)
                if (dictionary.matchQuickCodes(code, value).isEmpty()) throw new AssertionError("Unreachable candidate: " + value);
            choices.add(values.toString());
        }
        System.out.printf(Locale.ROOT,"{\"basic_ms\":%.1f,\"full_ms\":%.1f,\"heap_bytes\":%d,\"english_alloc_bytes\":%d,\"candidates\":\"%s\"}%n",basicMs,fullMs,heap,allocated,String.join(" / ",choices));
    }
}
