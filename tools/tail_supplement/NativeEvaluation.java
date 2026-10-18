package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.ToDoubleFunction;

/** Target-free ordinary prediction; inputs contain only context, code and lists. */
public final class NativeEvaluation {
    private static Path assets;
    private static Reader a(String name) throws IOException {
        return Files.newBufferedReader(assets.resolve(name));
    }
    private static List<String> values(String text) {
        return text.isEmpty() ? Collections.emptyList() : Arrays.asList(text.split("\\|"));
    }
    public static void main(String[] args) throws Exception {
        assets = Path.of(args[0]);
        DictionaryEngine dictionary = new DictionaryEngine(a("cangjie5.base.dict.yaml"),
            a("english.txt"), a("character_frequencies.tsv"));
        SentenceRanker sentence = SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64")));
        PhraseRelationRanker relation = PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64")));
        QuickDecoder decoder = new QuickDecoder(dictionary, a("quick_phrases.tsv"), a("hk_phrases.tsv"),
            a("cantonese_phrases.tsv"), OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))), a("hk_chat_phrases.tsv"),
            CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))), sentence,
            PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))), relation,
            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));
        if (!relation.aligned()) throw new IllegalStateException("Expected the deployed aligned relation model");
        int count = 0, changed = 0, additions = 0;
        try (BufferedReader in = Files.newBufferedReader(Path.of(args[1]));
             BufferedWriter out = Files.newBufferedWriter(Path.of(args[2]));
             BufferedWriter audit = Files.newBufferedWriter(Path.of(args[3]))) {
            String line;
            while ((line = in.readLine()) != null) {
                String[] f = line.split("\t", -1);
                if (f.length != 5) throw new IllegalArgumentException("Target-free five-column inputs required");
                String context = f[1], code = f[2];
                List<String> parent = values(f[3]), proposals = values(f[4]);
                Map<String,Double> scores = new LinkedHashMap<>();
                double reference = parent.isEmpty() ? 0 : relation.rawScore(context, parent.get(0));
                // Same bundled scorers on every compared string. This is the public
                // whole-text language score + sentence residual + aligned relation
                // correction. It excludes lattice token priors/personal weights.
                ToDoubleFunction<String> score = text -> scores.computeIfAbsent(text,
                    value -> decoder.languageScore(context, value) + sentence.score(context, value)
                        + relation.alignedCorrection(relation.rawScore(context, value), reference));
                List<String> result = TailSupplement.apply(parent, proposals,
                    text -> !dictionary.matchQuickCodes(code, text).isEmpty(), score, false);
                int pinned = Math.min(18, parent.size());
                if (!result.subList(0, pinned).equals(parent.subList(0, pinned)))
                    throw new AssertionError("Pinned prefix changed");
                if (result.size() > 20 || new HashSet<>(result).size() != result.size())
                    throw new AssertionError("Invalid display");
                List<String> oldSurvivors = new ArrayList<>(), newSurvivors = new ArrayList<>();
                for (String text : parent) if (result.contains(text)) oldSurvivors.add(text);
                for (String text : result) {
                    if (dictionary.matchQuickCodes(code, text).isEmpty()) throw new AssertionError("Inexact candidate");
                    if (parent.contains(text)) newSurvivors.add(text);
                }
                if (!oldSurvivors.equals(newSurvivors)) throw new AssertionError("Native relative order changed");
                int added = result.size() - newSurvivors.size();
                if (added > 2) throw new AssertionError("Too many proposals");
                out.write(f[0] + "\t" + context + "\t" + code + "\t" + String.join("|", result) + "\n");
                for (Map.Entry<String,Double> entry : scores.entrySet())
                    audit.write(count + "\t" + entry.getKey() + "\t" + entry.getValue() + "\t"
                        + parent.contains(entry.getKey()) + "\t" + result.contains(entry.getKey()) + "\n");
                changed += result.equals(parent) ? 0 : 1; additions += added;
                if (++count % 100 == 0) System.out.println("predicted=" + count);
            }
        }
        System.out.println("cases=" + count + " changed=" + changed + " added=" + additions
            + " pinned18=true exact=true max20=true");
    }
}
