package hk.cantonesemixeng.keyboard;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * Adds a baseline language-score margin to public training candidate pairs.
 * Compile against the pinned baseline decoder and run with its archived assets:
 * assets-directory, five-column-pairs.tsv, six-column-pairs-with-margins.tsv.
 *
 * The margin is languageScore(context, positive) minus languageScore(context,
 * negative). It includes baseline language/phrase/grammar evidence but excludes
 * segmentation-dependent word priors and personal learning. It is therefore a
 * residual-training approximation, not the raw beam-path score difference.
 * Both candidates must match the entire typed code. The Python trainer enforces
 * the training-source whitelist, excluded splits, and manifest checksums; this
 * exporter does not decide which corpus sources belong to training.
 */
public final class ExportCandidateMargins {
    private static Reader asset(Path assets, String name) throws IOException {
        return Files.newBufferedReader(assets.resolve(name), StandardCharsets.UTF_8);
    }

    private static double score(QuickDecoder decoder, Map<String, Double> cache,
                                String context, String text) {
        return cache.computeIfAbsent(context + "\t" + text,
            key -> decoder.languageScore(context, text));
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3)
            throw new IllegalArgumentException("Expected assets, five-column pairs, output pairs");
        Path assets = Path.of(args[0]);
        Path input = Path.of(args[1]).toAbsolutePath().normalize();
        Path output = Path.of(args[2]).toAbsolutePath().normalize();
        if (input.equals(output))
            throw new IllegalArgumentException("Input and output must be different files");
        DictionaryEngine dictionary = new DictionaryEngine(asset(assets, "cangjie5.base.dict.yaml"),
            asset(assets, "english.txt"), asset(assets, "character_frequencies.tsv"));
        QuickDecoder decoder = new QuickDecoder(dictionary, asset(assets, "quick_phrases.tsv"),
            asset(assets, "hk_phrases.tsv"), asset(assets, "cantonese_phrases.tsv"),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),
            asset(assets, "hk_chat_phrases.tsv"));
        Map<String, Double> scores = new HashMap<>();
        int count = 0, number = 0;
        try (BufferedReader reader = Files.newBufferedReader(input, StandardCharsets.UTF_8);
             BufferedWriter writer = Files.newBufferedWriter(output, StandardCharsets.UTF_8)) {
            writer.write("# source\tcontext\tcode\tpositive\tnegative\tbaseline_language_margin\n");
            String line;
            while ((line = reader.readLine()) != null) {
                number++;
                if (line.isEmpty() || line.startsWith("#")) continue;
                String[] fields = line.split("\t", -1);
                if (fields.length != 5)
                    throw new IllegalArgumentException("Expected five columns at line " + number);
                String source = fields[0], context = fields[1], code = fields[2];
                String positive = fields[3], negative = fields[4];
                if (source.isEmpty() || !code.matches("[a-z]{3,48}")
                        || context.codePointCount(0, context.length()) > 12
                        || positive.equals(negative)
                        || !QuickDecoder.hanText(positive) || !QuickDecoder.hanText(negative))
                    throw new IllegalArgumentException("Invalid candidate pair at line " + number);
                if (dictionary.matchQuickCodes(code, positive).isEmpty()
                        || dictionary.matchQuickCodes(code, negative).isEmpty())
                    throw new IllegalArgumentException("Inexact complete candidate code at line " + number);
                double margin = score(decoder, scores, context, positive)
                    - score(decoder, scores, context, negative);
                if (!Double.isFinite(margin) || Math.abs(margin) > 1000)
                    throw new IllegalArgumentException("Invalid language margin at line " + number);
                writer.write(line + "\t" + Double.toString(margin) + "\n");
                count++;
            }
        }
        if (count == 0) throw new IllegalArgumentException("No candidate training pairs");
        System.out.println("pairs=" + count + " distinct_context_candidates=" + scores.size()
            + " margin=baseline_language_only output=" + output);
    }
}
