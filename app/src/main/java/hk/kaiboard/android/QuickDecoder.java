package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;

/** Bounded offline word-lattice decoder, including one-code Quick characters. */
public final class QuickDecoder {
    private static final int BEAM = 48;
    // Productive Cantonese predicate questions, rather than memorized full sentences.
    // Particles and nouns must not receive the A-not-A grammar preference.
    private static final String QUESTION_PREDICATES = "食飲去做睇買返係得知要想試用踩搭打踢聽講問答寫讀開關拎攞畀揀改整洗煮玩行跑坐企瞓等記識明信收放賣換借還帶着著學幫肯敢好啱忙攰凍熱快慢靚貴平難易";
    private final DictionaryEngine dictionary;
    private final OfflineLanguageModel model;
    private final Map<String, Double> pairCounts = new HashMap<>();
    private final Map<String, Double> outgoing = new HashMap<>();
    private final Map<String, List<Token>> vocabulary = new HashMap<>();
    private final Set<String> knownPhrases = new HashSet<>();
    private final Map<Integer, List<Token>> continuations = new HashMap<>();
    private final Map<String, Double> phraseEvidence = new HashMap<>();
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
        addPredicateQuestions();
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

    private void addPredicateQuestions() {
        for (int cp : QUESTION_PREDICATES.codePoints().distinct().toArray()) {
            String predicate = new String(Character.toChars(cp));
            String question = predicate + "唔" + predicate;
            for (String left : dictionary.quickCodesFor(predicate))
                for (String middle : dictionary.quickCodesFor("唔"))
                    for (String right : dictionary.quickCodesFor(predicate)) {
                        List<Token> tokens = vocabulary.computeIfAbsent(left + middle + right, k -> new ArrayList<>());
                        if (tokens.stream().noneMatch(t -> t.text.equals(question)))
                            tokens.add(new Token(question, 30000));
                    }
        }
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
                double count = Double.parseDouble(f[2]);
                if (characters >= 2 && characters <= 4) {
                    // All bundled vocabulary supplies evidence, not just a small HK list.
                    // Corpus counts calibrate confidence; local authored priorities retain
                    // their stronger preference without pretending to be measured counts.
                    double evidence = localUsage ? .65 * (characters - 1) + (characters >= 3 ? 2 : 0)
                        : .45 * (characters - 1) * Math.min(1, Math.log1p(count) / Math.log1p(3000));
                    phraseEvidence.merge(f[1], evidence, Math::max);
                }
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
        List<List<Token>> following = new ArrayList<>();
        for (int i = 0; i <= code.length(); i++) following.add(followingWords(code, i));
        lattice.get(0).add(new Path("", 0));
        for (int pos = 0; pos < code.length(); pos++) {
            if (Thread.currentThread().isInterrupted()) return Collections.emptyList();
            List<Path> paths = prune(lattice.get(pos), context, following.get(pos));
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
                if (target.size() > 1024) lattice.set(pos + length,
                    prune(target, context, following.get(pos + length)));
            }
        }
        List<String> result = new ArrayList<>();
        // An attested complete word/phrase is safer than a sentence invented from pair statistics.
        List<Token> wholeWords = new ArrayList<>(vocabulary.getOrDefault(code, Collections.emptyList()));
        // With the trained model, complete words already participate in the lattice.
        // Give their observed frequency a bounded prior, then compare actual scores;
        // do not pin five words ahead of a better contextual sentence regardless of score.
        if (model != null) for (Token token : wholeWords)
            if (!dictionary.matchQuickCodes(code, token.text).isEmpty())
                lattice.get(code.length()).add(new Path(token.text,
                    languageScore(context, token.text) + Math.min(8, Math.log1p(token.score) * .7)));
        for (Token token : model == null ? wholeWords : Collections.<Token>emptyList()) {
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
        if (model != null) return model.score(prefix, text) + phraseBonus(prefix, text);
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
        return score + phraseBonus(prefix, text);
    }

    private double phraseBonus(String prefix, String text) {
        if (phraseEvidence.isEmpty()) return 0;
        String history = OfflineLanguageModel.contextTail(prefix);
        double bonus = 0;
        for (int cp : text.codePoints().toArray()) {
            if (!OfflineLanguageModel.han(cp)) { history = ""; continue; }
            String previous = history;
            history += new String(Character.toChars(cp));
            int count = history.codePointCount(0, history.length());
            if (count > 4) { history = history.substring(history.offsetByCodePoints(0, count - 4)); count = 4; }
            double matched = 0;
            for (int length = 2; length <= count; length++) {
                String suffix = history.substring(history.offsetByCodePoints(0, count - length));
                // Completion supplies right-hand evidence for earlier ambiguous codes,
                // including when the phrase is split across lattice token boundaries.
                matched += phraseEvidence.getOrDefault(suffix, 0.0);
            }
            if (count >= 3) {
                String ending = history.substring(history.offsetByCodePoints(0, count - 3));
                int[] pattern = ending.codePoints().toArray();
                if (pattern[0] == cp && pattern[1] == '唔' && QUESTION_PREDICATES.indexOf(cp) >= 0) {
                    matched = Math.max(matched, 3.3);
                    // Back off an unseen repeated predicate to an attested question's
                    // grammatical transition. Keep its own lexical/context likelihood
                    // and the following object's evidence; never force a whole sentence.
                    if (model != null) bonus += Math.min(12, Math.max(0,
                        model.score("食唔", "食") - model.score(previous, new String(Character.toChars(cp)))));
                }
            }
            // A bounded local preference, so Chinese codes and statistical context still determine choices.
            bonus += Math.min(4, matched);
        }
        return bonus;
    }

    // The base Cangjie dictionary also contains symbols and phonetic letters.
    // Keep them available for direct lookup, but never splice them into Chinese sentences.
    static boolean hanText(String text) {
        return !text.isEmpty() && text.codePoints().allMatch(OfflineLanguageModel::han);
    }

    /** Bounded lexical lookahead keeps an earlier ambiguity alive until later codes are scored. */
    private List<Token> followingWords(String code, int pos) {
        if (model == null) return Collections.emptyList();
        List<Token> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (int length = 2; length <= Math.min(8, code.length() - pos); length++) {
            List<Token> tokens = vocabulary.getOrDefault(code.substring(pos, pos + length), Collections.emptyList());
            for (int i = 0; i < Math.min(2, tokens.size()); i++) {
                String text = tokens.get(i).text;
                int characters = text.codePointCount(0, text.length());
                if (characters >= 2 && characters <= 4 && seen.add(text))
                    result.add(new Token(text, languageScore("", text)));
                if (result.size() == 1) return result;
            }
        }
        return result;
    }

    private List<Path> prune(List<Path> input, String context, List<Token> following) {
        if (following.isEmpty() || input.size() <= BEAM) return prune(input);
        Map<String, Double> cached = new HashMap<>();
        Map<Path, Double> scores = new IdentityHashMap<>();
        for (Path path : input) {
            String tail = OfflineLanguageModel.contextTail(context + path.text);
            double evidence = cached.computeIfAbsent(tail, key -> {
                double best = 0;
                for (Token next : following)
                    best = Math.max(best, languageScore(key, next.text) - next.score);
                return Math.min(2, best);
            });
            scores.put(path, path.score + evidence);
        }
        // The hint only protects search paths; final ordering uses the complete sentence score.
        input.sort(Comparator.comparingDouble((Path p) -> scores.get(p)).reversed());
        return distinctPaths(input);
    }

    private static List<Path> prune(List<Path> input) {
        input.sort(Comparator.comparingDouble((Path p) -> p.score).reversed());
        return distinctPaths(input);
    }

    private static List<Path> distinctPaths(List<Path> input) {
        List<Path> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (Path path : input) if (seen.add(path.text)) { result.add(path); if (result.size() == BEAM) break; }
        return result;
    }
}
