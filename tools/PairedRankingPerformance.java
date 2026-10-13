import java.io.*;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.ToIntBiFunction;

/** Isolated historical/current classes in one JVM; alternate order to expose host timing drift. */
public final class PairedRankingPerformance {
    private static final class Engine implements AutoCloseable {
        final URLClassLoader classes;
        final Object dictionary, decoder;
        final Method decode, match;
        private Reader reader(Path assets, String name) throws IOException {
            return Files.newBufferedReader(assets.resolve(name));
        }
        Engine(Path compiled, Path assets) throws Exception {
            classes = new URLClassLoader(new URL[]{compiled.toUri().toURL()}, ClassLoader.getPlatformClassLoader());
            String pkg = "hk.cantonesemixeng.keyboard.";
            Class<?> dictionaryClass = classes.loadClass(pkg + "DictionaryEngine");
            Class<?> modelClass = classes.loadClass(pkg + "OfflineLanguageModel");
            Class<?> phraseClass = classes.loadClass(pkg + "PhraseLanguageModel");
            Class<?> rankerClass = classes.loadClass(pkg + "CandidateRanker");
            Class<?> decoderClass = classes.loadClass(pkg + "QuickDecoder");
            dictionary = dictionaryClass.getConstructor(Reader.class, Reader.class, Reader.class).newInstance(
                reader(assets, "cangjie5.base.dict.yaml"), reader(assets, "english.txt"), reader(assets, "character_frequencies.tsv"));
            List<Class<?>> types = new ArrayList<>(Arrays.asList(dictionaryClass, Reader.class, Reader.class, Reader.class,
                modelClass, phraseClass, Reader.class, rankerClass));
            List<Object> values = new ArrayList<>(Arrays.asList(dictionary, reader(assets, "quick_phrases.tsv"),
                reader(assets, "hk_phrases.tsv"), reader(assets, "cantonese_phrases.tsv"),
                modelClass.getMethod("load", InputStream.class).invoke(null, Files.newInputStream(assets.resolve("language_model.b64"))),
                phraseClass.getMethod("load", InputStream.class).invoke(null, Files.newInputStream(assets.resolve("phrase_model.b64"))),
                reader(assets, "hk_chat_phrases.tsv"),
                rankerClass.getMethod("load", InputStream.class).invoke(null, Files.newInputStream(assets.resolve("candidate_ranker.b64")))));
            if (Files.exists(assets.resolve("word_ranker.b64"))) {
                types.add(rankerClass);
                values.add(rankerClass.getMethod("loadWords", InputStream.class)
                    .invoke(null, Files.newInputStream(assets.resolve("word_ranker.b64"))));
            }
            if (Files.exists(assets.resolve("sentence_ranker.b64"))) {
                Class<?> sentenceClass = classes.loadClass(pkg + "SentenceRanker");
                types.add(sentenceClass);
                values.add(sentenceClass.getMethod("load", InputStream.class)
                    .invoke(null, Files.newInputStream(assets.resolve("sentence_ranker.b64"))));
            }
            if(Files.exists(assets.resolve("prefix_ranker.b64"))) {
                Class<?> prefixClass=classes.loadClass(pkg+"PrefixRanker");
                types.add(prefixClass);
                values.add(prefixClass.getMethod("load",InputStream.class)
                    .invoke(null,Files.newInputStream(assets.resolve("prefix_ranker.b64"))));
            }
            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());
            decode = decoderClass.getMethod("decode", String.class, ToIntBiFunction.class);
            match = dictionaryClass.getMethod("matchQuickCodes", String.class, String.class);
        }
        @SuppressWarnings("unchecked") List<String> run(String code) throws Exception {
            return (List<String>)decode.invoke(decoder, code, (ToIntBiFunction<String, String>)(c, w) -> 0);
        }
        void check(String code, List<String> results) throws Exception {
            if (results.size() > 20 || new HashSet<>(results).size() != results.size()) throw new AssertionError(code);
            for (String text : results)
                if (((List<?>)match.invoke(dictionary, code, text)).isEmpty()) throw new AssertionError(text);
        }
        public void close() throws IOException { classes.close(); }
    }
    public static void main(String[] args) throws Exception {
        int warmup = args.length > 4 ? Integer.parseInt(args[4]) : 3;
        int samples = args.length > 5 ? Integer.parseInt(args[5]) : 9;
        if (warmup < 3 || warmup > 50 || samples < 3 || samples > 101 || samples % 2 == 0)
            throw new IllegalArgumentException("Invalid warmup/sample count");
        String[] codes = {"ofonaovrmrq", "hmerrrysmlrp", "dpofvivcjutrmyyjvcqnjd", "ofykrmmsydwljpvwjd",
            "vkmmnkmrvordrjjj", "hi".repeat(24)};
        ThreadMXBean cpu = ManagementFactory.getThreadMXBean();
        if (!cpu.isCurrentThreadCpuTimeSupported()) throw new IllegalStateException("Thread CPU time unavailable");
        cpu.setThreadCpuTimeEnabled(true);
        try (Engine before = new Engine(Path.of(args[0]), Path.of(args[1]));
             Engine after = new Engine(Path.of(args[2]), Path.of(args[3]))) {
            Engine[] engines = {before, after};
            for (int pass = 0; pass < warmup; pass++) for (String code : codes)
                for (int order = 0; order < 2; order++) engines[(pass + order) % 2].run(code);
            System.out.printf("# warmup=%d samples=%d%n", warmup, samples);
            System.out.println("# code\tletters\tbefore_wall_median_ms\tafter_wall_median_ms\tbefore_cpu_median_ms\tafter_cpu_median_ms");
            for (String code : codes) {
                double[][] walls = new double[2][samples], cpus = new double[2][samples];
                for (int pass = 0; pass < samples; pass++) for (int order = 0; order < 2; order++) {
                    int index = (pass + order) % 2;
                    long start = System.nanoTime(), cpuStart = cpu.getCurrentThreadCpuTime();
                    List<String> results = engines[index].run(code);
                    cpus[index][pass] = (cpu.getCurrentThreadCpuTime() - cpuStart) / 1e6;
                    walls[index][pass] = (System.nanoTime() - start) / 1e6;
                    engines[index].check(code, results);
                }
                for (double[] values : walls) Arrays.sort(values);
                for (double[] values : cpus) Arrays.sort(values);
                System.out.printf(Locale.ROOT, "%s\t%d\t%.3f\t%.3f\t%.3f\t%.3f%n",
                    code, code.length(), walls[0][samples / 2], walls[1][samples / 2], cpus[0][samples / 2], cpus[1][samples / 2]);
            }
        }
    }
}
