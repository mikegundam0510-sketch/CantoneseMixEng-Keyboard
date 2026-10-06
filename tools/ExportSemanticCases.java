package hk.kaiboard.android;

import java.nio.file.*;
import java.io.*;
import java.util.*;

public class ExportSemanticCases {
    private static final Path assets = Path.of("app/src/main/assets");
    private static Reader asset(String n) throws IOException { return Files.newBufferedReader(assets.resolve(n)); }
    public static void main(String[] args) throws Exception {
        var dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
        var model = OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64")));
        var decoder = new QuickDecoder(dictionary,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),model);
        var out = Path.of(args[1]); Files.createDirectories(out);
        StringBuilder cases = new StringBuilder("["), manifest = new StringBuilder(); int i = 0;
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            if (line.isBlank() || line.startsWith("#")) continue;
            String[] f = line.split("\t",-1); String context = f[0], expected = f[1];
            String code = f.length > 2 ? f[2] : expected.codePoints().mapToObj(cp ->
                dictionary.quickCodesFor(new String(Character.toChars(cp))).get(0)).reduce("",String::concat);
            var all = decoder.decode(code, (c,w)->0, context);
            var candidates = new ArrayList<>(all.subList(0,Math.min(8,all.size())));
            if (candidates.size() < 2) throw new AssertionError("No candidates");
            for (String candidate : candidates) if (dictionary.matchQuickCodes(code,candidate).isEmpty()) throw new AssertionError("Unreachable");
            var prompt = out.resolve(String.format(Locale.ROOT,"prompt-%03d.txt",i));
            Files.writeString(prompt,SemanticPrompt.build(context,candidates));
            manifest.append(candidates.size()).append(' ').append(prompt).append('\n');
            if (i++ > 0) cases.append(',');
            cases.append("{\"context\":").append(SemanticPrompt.quote(context))
                .append(",\"expected\":").append(SemanticPrompt.quote(expected))
                .append(",\"code\":").append(SemanticPrompt.quote(code)).append(",\"candidates\":[");
            for (int n=0;n<candidates.size();n++) { if (n>0) cases.append(','); cases.append(SemanticPrompt.quote(candidates.get(n))); }
            cases.append("]}");
        }
        Files.writeString(out.resolve("cases.json"),cases.append("]\n").toString());
        Files.writeString(out.resolve("manifest.txt"),manifest.toString());
    }
}
