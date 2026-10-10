package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;
import java.util.function.ToIntFunction;

/** Bounded offline word-lattice decoder, including one-code Quick characters. */
public final class QuickDecoder {
    private static final int BEAM = 48;
    // Selected on separate validation conversations, before held-out evaluation.
    private static final double SENTENCE_SCORE_MARGIN = 10;
    // Productive Cantonese predicate questions, rather than memorized full sentences.
    // Particles and nouns must not receive the A-not-A grammar preference.
    private static final String QUESTION_PREDICATES = "食飲去做睇買返係得知要想試用踩搭打踢聽講問答寫讀開關拎攞畀揀改整洗煮玩行跑坐企瞓等記識明信收放賣換借還帶着著學幫肯敢好啱忙攰凍熱快慢靚貴平難易";
    // Productive request/action constructions. No complete typed sentence is stored.
    private static final String ACTIONS = "交還送借收寄傳發派覆帶留印睇試改做查問諗學聽講寫讀用打幫去返買飲食整揀拎攞";
    private static final Set<String> ACTION_WORDS = new HashSet<>(Arrays.asList(
        "繼續", "完善", "改善", "修改", "調整", "檢查", "研究", "練習", "試用", "更新",
        "確認", "提供", "處理", "解釋", "補充", "輸入", "打字", "安排", "完成", "幫手"));
    private static final String HANDOVER_ACTIONS = "交送寄還傳發拎攞寫帶留印買做";
    private static final String[] RECIPIENTS = {"我", "你", "佢", "我哋", "你哋", "佢哋",
        "老細", "同事", "老師", "同學", "朋友", "家人", "客人", "客戶", "屋企人"};
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
        return nextSuggestions(context, limit, word -> 0);
    }

    public boolean knownWord(String text) {
        int size = text.codePointCount(0, text.length());
        return size >= 2 && size <= 8 && knownPhrases.contains(text);
    }

    /** Learned counts apply only to a matching bundled word, within its prefix group. */
    public List<String> nextSuggestions(String context, int limit, ToIntFunction<String> learned) {
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
                    + languageScore(context, tail) / size
                    + personalBonus(learned.applyAsInt(phrase.text), 20, 4);
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
                    double evidence = localUsage ? 2 * (characters - 1) + (characters >= 3 ? 2 : 0)
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
            Map<Path, String> histories = new IdentityHashMap<>();
            for (Path path : paths) histories.put(path, sentenceContext(context + path.text));
            Map<String, Map<String, Double>> boundaryScores = new HashMap<>();
            for (int length = 1; length <= Math.min(16, code.length() - pos); length++) {
                String part = code.substring(pos, pos + length);
                LinkedHashMap<String, Double> options = new LinkedHashMap<>();
                List<Token> known = personalizedTokens(part, learned);
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
                    if (knownWord(choice.getKey()))
                        bonus += personalBonus(learned.applyAsInt(part, choice.getKey()), 6, 1.5);
                    List<String> codes = dictionary.matchQuickCodes(part, choice.getKey());
                    int offset = 0;
                    for (String c : codes) {
                        int cp = choice.getKey().codePointAt(offset);
                        String character = new String(Character.toChars(cp)); offset += Character.charCount(cp);
                        bonus += personalBonus(learned.applyAsInt(c, character), 2.5, .65);
                    }
                    String word = choice.getKey();
                    int boundaryLength = Math.min(12, word.codePointCount(0, word.length()));
                    String first = word.substring(0, word.offsetByCodePoints(0, boundaryLength));
                    double internalScore = languageScore("", word) - languageScore("", first);
                    for (Path prefix : paths) {
                        String history = histories.get(prefix);
                        Map<String, Double> cached = boundaryScores.computeIfAbsent(history, h -> new HashMap<>());
                        double score = cached.computeIfAbsent(first, wordStart -> languageScore(history, wordStart)) + internalScore;
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
        List<Token> wholeWords = personalizedTokens(code, learned);
        // With the trained model, complete words already participate in the lattice.
        // Give their observed frequency a bounded prior, then compare actual scores;
        // do not pin five words ahead of a better contextual sentence regardless of score.
        if (model != null) for (Token token : wholeWords)
            if (!dictionary.matchQuickCodes(code, token.text).isEmpty())
                lattice.get(code.length()).add(new Path(token.text,
                    languageScore(context, token.text) + Math.min(8, Math.log1p(token.score) * .7)
                    + personalBonus(learned.applyAsInt(code, token.text), 6, 1.5)));
        for (Token token : model == null ? wholeWords : Collections.<Token>emptyList()) {
            if (!dictionary.matchQuickCodes(code, token.text).isEmpty() && !result.contains(token.text)) result.add(token.text);
            if (result.size() == 5) break;
        }
        List<Path> completed = prune(lattice.get(code.length()));
        double bestScore = completed.isEmpty() ? Double.NEGATIVE_INFINITY : completed.get(0).score;
        for (Path path : completed) {
            // A score gap is uncertainty, not proof that unfamiliar Chinese is invalid.
            // Keep attested words and explicit character sequences; Single mode remains available.
            if (model != null && path.text.codePointCount(0, path.text.length()) > 3
                    && path.score < bestScore - SENTENCE_SCORE_MARGIN && !knownWord(path.text)
                    && !learnedSequence(code, path.text, learned)) continue;
            if (path.text.codePointCount(0, path.text.length()) > 1 && !result.contains(path.text)) result.add(path.text);
            if (result.size() == 20) break;
        }
        // Explicit repeated choices outrank statistical guesses. Zero counts preserve
        // the existing context order; only exact, bundled words can be personalized.
        result.sort(Comparator.comparingInt((String text) -> knownWord(text)
            ? learned.applyAsInt(code, text) : 0).reversed());
        return result;
    }

    private boolean learnedSequence(String code, String text, ToIntBiFunction<String, String> learned) {
        List<String> codes = dictionary.matchQuickCodes(code, text);
        if (codes.isEmpty()) return false;
        int at = 0;
        for (String part : codes) {
            String character = new String(Character.toChars(text.codePointAt(at)));
            at += character.length();
            if (learned.applyAsInt(part, character) <= 0) return false;
        }
        return true;
    }

    private static double personalBonus(int weight, double cap, double scale) {
        double value = Math.min(cap, Math.log1p(Math.abs((double) weight)) * scale);
        return weight < 0 ? -value : value;
    }

    private List<Token> personalizedTokens(String code, ToIntBiFunction<String, String> learned) {
        List<Token> original = vocabulary.getOrDefault(code, Collections.emptyList());
        // Preserve the zero-history path and avoid a per-token allocation/sort there.
        boolean hasCounts = false;
        for (Token token : original) if (knownWord(token.text) && learned.applyAsInt(code, token.text) != 0) {
            hasCounts = true; break;
        }
        if (!hasCounts) return original;
        List<Token> result = new ArrayList<>(original);
        result.sort(Comparator.comparingDouble((Token token) -> Math.log1p(token.score)
            + personalBonus(learned.applyAsInt(code, token.text), 6, 1.5)).reversed());
        return result;
    }

    public double languageScore(String prefix, String text) {
        if (model != null) return model.score(prefix, text) + phraseBonus(prefix, text) + completionBonus(prefix, text) + handoverBonus(prefix, text);
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
        return score + phraseBonus(prefix, text) + completionBonus(prefix, text) + handoverBonus(prefix, text);
    }

    private static String sentenceContext(String text) {
        int at = text.length(), count = 0;
        while (at > 0 && count < 12 && OfflineLanguageModel.han(text.codePointBefore(at))) {
            at -= Character.charCount(text.codePointBefore(at)); count++;
        }
        return text.substring(at);
    }

    private static int handoverConfidence(String history) {
        int confidence = 0;
        for (int at = 0; at < history.length(); at++) {
            char marker = history.charAt(at);
            if (marker != '畀' && marker != '俾') continue;
            int action = 0;
            for (int i = 0; i + 1 < at; i++)
                if (HANDOVER_ACTIONS.indexOf(history.charAt(i)) >= 0 && "咗返緊齊".indexOf(history.charAt(i + 1)) >= 0) {
                    action = Math.max(action, 2);
                    boolean sender = (i > 0 && "我你佢".indexOf(history.charAt(i - 1)) >= 0)
                        || (i > 1 && history.charAt(i - 1) == '哋' && "我你佢".indexOf(history.charAt(i - 2)) >= 0);
                    if (sender) action = 3;
                }
            if (action == 0) continue;
            for (String recipient : RECIPIENTS) if (history.startsWith(recipient, at + 1)) confidence = Math.max(confidence, action);
        }
        return confidence;
    }

    private static double handoverBonus(String prefix, String text) {
        String history = sentenceContext(prefix);
        int established = handoverConfidence(history);
        double bonus = 0;
        for (int cp : text.codePoints().toArray()) {
            if (!OfflineLanguageModel.han(cp)) { history = ""; established = 0; continue; }
            history = sentenceContext(history + new String(Character.toChars(cp)));
            int current = handoverConfidence(history);
            // One bounded relation bonus, including a plural recipient, across tokens.
            bonus += Math.max(0, current - established);
            established = current;
        }
        return bonus;
    }

    private static double pendingQuestion(String history) {
        if (!history.endsWith("未")) return 0;
        int at = history.lastIndexOf('咗');
        if (at <= 0 || ACTIONS.indexOf(history.codePointBefore(at)) < 0) return 0;
        return handoverConfidence(history) > 0 ? 3 : 1.5;
    }

    private static double completionBonus(String prefix, String text) {
        String history = sentenceContext(prefix);
        double pending = pendingQuestion(history), bonus = 0;
        for (int cp : text.codePoints().toArray()) {
            if (!OfflineLanguageModel.han(cp)) { history = ""; pending = 0; continue; }
            // Withdraw a tentative question bonus when Han text continues after 未,
            // e.g. 未來. The difference telescopes across lattice token boundaries.
            bonus -= pending;
            history = sentenceContext(history + new String(Character.toChars(cp)));
            pending = pendingQuestion(history);
            bonus += pending;
        }
        return bonus;
    }

    private static String clauseContext(String text) {
        int start = text.length(), count = 0;
        while (start > 0 && count < 5) {
            int cp = text.codePointBefore(start);
            if (!OfflineLanguageModel.han(cp)) break;
            start -= Character.charCount(cp); count++;
        }
        return text.substring(start);
    }

    private double phraseBonus(String prefix, String text) {
        if (phraseEvidence.isEmpty()) return 0;
        String history = clauseContext(prefix);
        double bonus = 0;
        for (int cp : text.codePoints().toArray()) {
            if (!OfflineLanguageModel.han(cp)) { history = ""; continue; }
            String previous = history;
            history += new String(Character.toChars(cp));
            int count = history.codePointCount(0, history.length());
            if (count > 5) { history = history.substring(history.offsetByCodePoints(0, count - 5)); count = 5; }
            // A frequent short word must not consume the subject/action grammar preference.
            double matched = 0, structural = 0;
            for (int length = 2; length <= count; length++) {
                String suffix = history.substring(history.offsetByCodePoints(0, count - length));
                // Completion supplies right-hand evidence for earlier ambiguous codes,
                // including when the phrase is split across lattice token boundaries.
                matched += phraseEvidence.getOrDefault(suffix, 0.0);
            }
            if (count >= 3) {
                String lastThree = history.substring(history.offsetByCodePoints(0, count - 3));
                int[] action = lastThree.codePoints().toArray();
                if ("你我佢".indexOf(action[0]) >= 0 && ACTIONS.indexOf(action[1]) >= 0 && "咗返緊".indexOf(action[2]) >= 0) structural += 1.5;
                if ("下吓".indexOf(action[2]) >= 0 && (ACTIONS.indexOf(action[1]) >= 0
                        || ACTION_WORDS.contains(new String(action, 0, 2)))) matched += 1.5;
                if (action[0] == '想' && "你我佢".indexOf(action[1]) >= 0
                        && ACTIONS.indexOf(action[2]) >= 0) matched += 2;
                if ("幫畀等".indexOf(action[0]) >= 0 && "你我佢".indexOf(action[1]) >= 0
                        && ACTIONS.indexOf(action[2]) >= 0) matched += 1.5;
            }
            if (count >= 4) {
                String lastFour = history.substring(history.offsetByCodePoints(0, count - 4));
                int[] action = lastFour.codePoints().toArray();
                if (action[0] == '想' && "你我佢".indexOf(action[1]) >= 0
                        && ACTION_WORDS.contains(new String(action, 2, 2))) matched += 2;
                if ("想幫畀等".indexOf(action[0]) >= 0 && "你我佢".indexOf(action[1]) >= 0) {
                    if (action[2] == '哋' && ACTIONS.indexOf(action[3]) >= 0) matched += action[0] == '想' ? 2 : 1.5;
                    if (action[0] != '想' && ACTION_WORDS.contains(new String(action, 2, 2))) matched += 1.5;
                }
            }
            if (count >= 5) {
                int[] action = history.substring(history.offsetByCodePoints(0, count - 5)).codePoints().toArray();
                if ("想幫畀等".indexOf(action[0]) >= 0 && "你我佢".indexOf(action[1]) >= 0 && action[2] == '哋'
                        && ACTION_WORDS.contains(new String(action, 3, 2))) matched += action[0] == '想' ? 2 : 1.5;
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
            bonus += Math.min(4, matched) + structural;
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
