package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;

/** Bounded offline word-lattice decoder, including one-code Quick characters. */
public final class QuickDecoder {
    private static final int BEAM = 48;
    private final DictionaryEngine dictionary;
    private final OfflineLanguageModel model;
    private final Map<String, Double> pairCounts = new HashMap<>();
    private final Map<String, Double> outgoing = new HashMap<>();
    private final Map<String, List<Token>> vocabulary = new HashMap<>();
    private final Set<String> knownPhrases = new HashSet<>();
    private final Map<Integer, List<Token>> continuations = new HashMap<>();
    private final Set<String> hkUsage = new HashSet<>();
    private static final class Token {
        final String text; final double score;
        Token(String text, double score) { this.text = text; this.score = score; }
    }
    private static final class Path {
        final String text; final double score;
        Path(String text, double score) { this.text = text; this.score = score; }
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input) throws IOException {
        this(dictionary, input, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput) throws IOException {
        this(dictionary, input, hkInput, null, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model) throws IOException {
        this.dictionary = dictionary; this.model = model;
        // The trained model replaces fallback pair statistics entirely.
        Map<String, Double> wordCounts = model == null ? new HashMap<>() : null;
        readVocabulary(input, wordCounts, false);
        if (hkInput != null) readVocabulary(hkInput, wordCounts, true);
        if (cantoneseInput != null) readVocabulary(cantoneseInput, wordCounts, false);
        if (wordCounts != null) for (Map.Entry<String, Double> entry : wordCounts.entrySet()) {
            String previous = null;
            for (int cp : entry.getKey().codePoints().toArray()) {
                String current = new String(Character.toChars(cp));
                if (previous != null) {
                    pairCounts.merge(previous + current, entry.getValue(), Double::sum);
                    outgoing.merge(previous, entry.getValue(), Double::sum);
                }
                previous = current;
            }
        }
        for (List<Token> tokens : vocabulary.values()) tokens.sort(Comparator.comparingDouble((Token t) -> t.score).reversed());
    }

    /** Only attested phrase tails are offered; no editor text is stored. */
    public List<String> nextSuggestions(String context, int limit) {
        if (context == null || context.isEmpty() || limit <= 0) return Collections.emptyList();
        int last = context.codePointBefore(context.length());
        if (!hanText(new String(Character.toChars(last)))) return Collections.emptyList();
        int[] history = context.codePoints().toArray();
        Map<String, Double> scores = new HashMap<>();
        for (int length = Math.min(8, history.length); length >= 1; length--) {
            String prefix = new String(history, history.length - length, length);
            if (!hanText(prefix)) continue;
            for (Token phrase : continuations.getOrDefault(prefix.codePointAt(0), Collections.emptyList())) {
                if (!phrase.text.startsWith(prefix) || phrase.text.length() == prefix.length()) continue;
                String tail = phrase.text.substring(prefix.length());
                int size = tail.codePointCount(0, tail.length());
                double score = length * 100 + Math.log1p(phrase.score)
                    + languageScore(context, tail) / size;
                if (Double.isFinite(score)) scores.merge(tail, score, Math::max);
            }
        }
        List<String> result = new ArrayList<>(scores.keySet());
        result.sort(Comparator.comparingDouble((String text) -> scores.get(text)).reversed().thenComparing(text -> text));
        return new ArrayList<>(result.subList(0, Math.min(limit, result.size())));
    }

    public boolean supportsCorrection(String context, String text) {
        int[] before = context.codePoints().toArray(), after = text.codePoints().toArray();
        // Require a real vocabulary phrase crossing the editor context / corrected text boundary.
        for (int left=1; left<=Math.min(3,before.length); left++)
            for (int right=1; right<=Math.min(3,after.length); right++)
                if (knownPhrases.contains(new String(before,before.length-left,left) + new String(after,0,right))) return true;
        return false;
    }

    private void readVocabulary(Reader input, Map<String, Double> wordCounts, boolean localUsage) throws IOException {
        try (BufferedReader reader = new BufferedReader(input)) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("#")) continue;
                String[] f = line.split("\\t");
                if (f.length != 3) continue;
                if (!hanText(f[1])) continue;
                boolean newPhrase = knownPhrases.add(f[1]);
                int characters = f[1].codePointCount(0, f[1].length());
                if (localUsage && characters >= 2 && characters <= 4) hkUsage.add(f[1]);
                double count = Double.parseDouble(f[2]);
                if (newPhrase) continuations.computeIfAbsent(f[1].codePointAt(0), k -> new ArrayList<>()).add(new Token(f[1], count));
                if (wordCounts != null) wordCounts.merge(f[1], count, Math::max);
                List<Token> tokens = vocabulary.computeIfAbsent(f[0], k -> new ArrayList<>());
                Token existing = null;
                for (Token token : tokens) if (token.text.equals(f[1])) { existing = token; break; }
                if (existing != null && existing.score >= count) continue;
                if (existing != null) tokens.remove(existing);
                tokens.add(new Token(f[1], count));
            }
        }
    }

    public List<String> decode(String input, ToIntBiFunction<String, String> learned) {
        return decode(input, learned, "");
    }

    public List<String> decode(String input, ToIntBiFunction<String, String> learned, String context) {
        String code = input.toLowerCase(Locale.ROOT);
        if (code.length() < 3 || code.length() > 48 || !code.matches("[a-z]+")) return Collections.emptyList();
        List<List<Path>> lattice = new ArrayList<>();
        for (int i = 0; i <= code.length(); i++) lattice.add(new ArrayList<>());
        lattice.get(0).add(new Path("", 0));
        for (int pos = 0; pos < code.length(); pos++) {
            if (Thread.currentThread().isInterrupted()) return Collections.emptyList();
            List<Path> paths = prune(lattice.get(pos));
            if (paths.isEmpty()) continue;
            for (int length = 1; length <= Math.min(16, code.length() - pos); length++) {
                String part = code.substring(pos, pos + length);
                LinkedHashMap<String, Double> options = new LinkedHashMap<>();
                List<Token> known = vocabulary.getOrDefault(part, Collections.emptyList());
                for (int j = 0; j < Math.min(24, known.size()); j++) options.put(known.get(j).text, known.get(j).score);
                if (length <= 2) {
                    List<String> letters = new ArrayList<>();
                    for (String word : dictionary.quickCandidates(part)) if (hanText(word)) letters.add(word);
                    letters.sort(Comparator.comparingInt((String w) -> learned.applyAsInt(part, w)).reversed());
                    for (int j = 0; j < Math.min(24, letters.size()); j++) {
                        String word = letters.get(j);
                        options.putIfAbsent(word, (double) dictionary.frequency(word));
                    }
                }
                if (options.isEmpty()) continue;
                List<Path> target = lattice.get(pos + length);
                for (Map.Entry<String, Double> choice : options.entrySet()) {
                    double bonus = 0;
                    List<String> codes = dictionary.matchQuickCodes(part, choice.getKey());
                    int offset = 0;
                    for (String c : codes) {
                        int cp = choice.getKey().codePointAt(offset);
                        String character = new String(Character.toChars(cp)); offset += Character.charCount(cp);
                        bonus += Math.min(2.5, Math.log1p(learned.applyAsInt(c, character)) * .65);
                    }
                    String word = choice.getKey();
                    int boundaryLength = Math.min(model == null ? 1 : 4, word.codePointCount(0, word.length()));
                    String first = word.substring(0, word.offsetByCodePoints(0, boundaryLength));
                    double internalScore = languageScore("", word) - languageScore("", first);
                    for (Path prefix : paths) {
                        double score = languageScore(context + prefix.text, first) + internalScore;
                        int characters = choice.getKey().codePointCount(0, choice.getKey().length());
                        // A modest word bonus, with character likelihood applied across token boundaries.
                        double wordBonus = characters > 1 ? Math.min(1.5, Math.log1p(choice.getValue()) / 10) * (characters - 1) : 0;
                        target.add(new Path(prefix.text + choice.getKey(), prefix.score + score + wordBonus + bonus));
                    }
                }
                if (target.size() > 1024) lattice.set(pos + length, prune(target));
            }
        }
        List<String> result = new ArrayList<>();
        // An attested complete word/phrase is safer than a sentence invented from pair statistics.
        List<Token> wholeWords = new ArrayList<>(vocabulary.getOrDefault(code, Collections.emptyList()));
        if (model != null) wholeWords.sort(Comparator.comparingDouble((Token t) ->
            languageScore(context, t.text) + Math.min(8, Math.log1p(t.score) * .7)).reversed());
        for (Token token : wholeWords) {
            if (!dictionary.matchQuickCodes(code, token.text).isEmpty() && !result.contains(token.text)) result.add(token.text);
            if (result.size() == 5) break;
        }
        for (Path path : prune(lattice.get(code.length()))) {
            if (path.text.codePointCount(0, path.text.length()) > 1 && !result.contains(path.text)) result.add(path.text);
            if (result.size() == 20) break;
        }
        return result;
    }

    public double languageScore(String prefix, String text) {
        if (model != null) return model.score(prefix, text) + hongKongBonus(prefix, text);
        String previous = prefix.isEmpty() ? null : new String(Character.toChars(prefix.codePointBefore(prefix.length())));
        double score = 0;
        for (int cp : text.codePoints().toArray()) {
            String current = new String(Character.toChars(cp));
            double unigram = Math.min(.2, dictionary.frequency(current) / 10000000.0);
            double probability = unigram;
            if (previous != null) {
                double total = outgoing.getOrDefault(previous, 0.0);
                double conditional = total == 0 ? unigram : pairCounts.getOrDefault(previous + current, 0.0) / total;
                probability = .98 * conditional + .02 * unigram;
            }
            score += Math.log(Math.max(1e-9, probability));
            previous = current;
        }
        return score + hongKongBonus(prefix, text);
    }

    private double hongKongBonus(String prefix, String text) {
        if (hkUsage.isEmpty()) return 0;
        String history = OfflineLanguageModel.contextTail(prefix);
        double bonus = 0;
        for (int cp : text.codePoints().toArray()) {
            if (Character.UnicodeScript.of(cp) != Character.UnicodeScript.HAN) { history = ""; continue; }
            history += new String(Character.toChars(cp));
            int count = history.codePointCount(0, history.length());
            if (count > 4) { history = history.substring(history.offsetByCodePoints(0, count - 4)); count = 4; }
            double matched = 0;
            for (int length = 2; length <= count; length++) {
                String suffix = history.substring(history.offsetByCodePoints(0, count - length));
                if (hkUsage.contains(suffix)) matched += .65 * (length - 1);
            }
            // A bounded local preference, so Chinese codes and statistical context still determine choices.
            bonus += Math.min(2, matched);
        }
        return bonus;
    }

    // The base Cangjie dictionary also contains symbols and phonetic letters.
    // Keep them available for direct lookup, but never splice them into Chinese sentences.
    static boolean hanText(String text) {
        return !text.isEmpty() && text.codePoints().allMatch(cp ->
            Character.UnicodeScript.of(cp) == Character.UnicodeScript.HAN);
    }

    private static List<Path> prune(List<Path> input) {
        input.sort(Comparator.comparingDouble((Path p) -> p.score).reversed());
        List<Path> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (Path path : input) if (seen.add(path.text)) { result.add(path); if (result.size() == BEAM) break; }
        return result;
    }
}

