package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;
import java.util.function.ToIntFunction;

/** Bounded offline word-lattice decoder, including one-code Quick characters. */
public final class QuickDecoder {
    private static final int BEAM = 48;
    // Only the completed boundary receives this wider pool; ordinary beam
    // widths and the confidence margin remain bounded as before.
    private static final int FINAL_POOL = 96;
    private static final int LOOKAHEAD_WORDS = 4, EXTRA_LOOKAHEAD_WORDS = 2, PATH_RESERVE = 8;
    // Selected on separate validation conversations, before held-out evaluation.
    private static final double SENTENCE_SCORE_MARGIN = 10;
    // Frozen on clause/public validation sets before post-selection guard decoding.
    static final double CLAUSE_START_STRENGTH = 1.5;
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
    private final PhraseLanguageModel phraseModel;
    private final CandidateRanker candidateRanker;
    private final CandidateRanker wordRanker;
    private final SentenceRanker sentenceRanker;
    private final double clauseStartStrength;
    // Common HK particles can have low character-only corpus counts. Admit
    // these into the same bounded contextual reserve, rather than promoting
    // every historical transcript variant beyond the frequency cutoff.
    private static final String HK_PARTICLES = "嘅咗喺啲哋嚟冇㗎喎嗰咁吖囉啦喇咩咋噃啩嘞咧嗱";
    private final Map<String, Double> pairCounts = new HashMap<>();
    private final Map<String, Double> outgoing = new HashMap<>();
    private final Map<String, List<Token>> vocabulary = new HashMap<>();
    private final Set<String> knownPhrases = new HashSet<>();
    private final Map<Integer, List<Token>> continuations = new HashMap<>();
    private final Map<String, Double> phraseEvidence = new HashMap<>();
    private final Map<String, Double> corpusEvidence = new HashMap<>();
    private final Map<String, Double> predicateBackoff = new HashMap<>();
    private static final class Token {
        final String text; final double score;
        Token(String text, double score) { this.text = text; this.score = score; }
    }
    private static final class Path {
        final String text; final double score;
        Path(String text, double score) { this.text = text; this.score = score; }
    }
    /** Per-decode caches with each scorer's own context bound, never personal weights. */
    private final class ModelScoreCache {
        private final Map<String, Double> transitions = new HashMap<>();
        private final Map<String, Map<String, Double>> phrases = new HashMap<>();
        double score(String prefix, String text) {
            return model.score(prefix, text, transitions);
        }
        double phraseScore(String prefix, String text) {
            String history = clauseContext(prefix);
            Map<String, Double> words = phrases.get(history);
            if (words == null) {
                if (phrases.size() >= 256) phrases.clear();
                words = new HashMap<>(); phrases.put(history, words);
            }
            Double score = words.get(text);
            if (score == null) {
                if (words.size() >= 256) words.clear();
                score = phraseBonus(history, text); words.put(text, score);
            }
            return score;
        }
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input) throws IOException {
        this(dictionary, input, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput) throws IOException {
        this(dictionary, input, hkInput, null, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model) throws IOException {
        this(dictionary, input, hkInput, cantoneseInput, model, null, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput) throws IOException {
        this(dictionary, input, hkInput, cantoneseInput, model, phraseModel, chatInput, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker) throws IOException {
        this(dictionary, input, hkInput, cantoneseInput, model, phraseModel, chatInput, candidateRanker, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker) throws IOException {
        this(dictionary, input, hkInput, cantoneseInput, model, phraseModel, chatInput, candidateRanker, wordRanker, CLAUSE_START_STRENGTH);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength) throws IOException {
        this(dictionary, input, hkInput, cantoneseInput, model, phraseModel, chatInput, candidateRanker,
            wordRanker, clauseStartStrength, null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, SentenceRanker sentenceRanker) throws IOException {
        this(dictionary, input, hkInput, cantoneseInput, model, phraseModel, chatInput, candidateRanker,
            wordRanker, CLAUSE_START_STRENGTH, sentenceRanker);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength,
                        SentenceRanker sentenceRanker) throws IOException {
        if (!Double.isFinite(clauseStartStrength) || clauseStartStrength < 0 || clauseStartStrength > 2)
            throw new IllegalArgumentException("Invalid clause-start strength");
        this.dictionary = dictionary; this.model = model; this.phraseModel = phraseModel;
        this.candidateRanker = candidateRanker;
        this.wordRanker = wordRanker;
        this.sentenceRanker = sentenceRanker;
        this.clauseStartStrength = clauseStartStrength;
        // Merge duplicate code variants and sources before creating prediction tails.
        // The trained model still replaces fallback pair statistics entirely.
        Map<String, Double> wordCounts = new HashMap<>();
        readVocabulary(input, wordCounts, false);
        if (hkInput != null) readVocabulary(hkInput, wordCounts, true);
        if (cantoneseInput != null) readVocabulary(cantoneseInput, wordCounts, false);
        if (chatInput != null) readVocabulary(chatInput, wordCounts, false);
        addPredicateQuestions();
        if (model != null) for (int subject : "我你佢".codePoints().toArray())
            for (int verb : ACTIONS.codePoints().toArray())
                for (int status : "咗返緊齊".codePoints().toArray()) {
                    String predicate = new String(new int[]{verb, status}, 0, 2);
                    if (phraseEvidence.getOrDefault(predicate, 0.0) < 2) continue;
                    String sender = new String(Character.toChars(subject));
                    double evidence = Math.min(6, Math.max(0,
                        model.score(sender, "做" + new String(Character.toChars(status))) - model.score(sender, predicate)));
                    predicateBackoff.put(sender + predicate, evidence);
                }
        for (Map.Entry<String, Double> entry : wordCounts.entrySet()) {
            continuations.computeIfAbsent(entry.getKey().codePointAt(0), k -> new ArrayList<>())
                .add(new Token(entry.getKey(), entry.getValue()));
            if (model != null) continue;
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
                if (f.length != 3 && f.length != 4) continue;
                if (!hanText(f[1])) continue;
                knownPhrases.add(f[1]);
                int characters = f[1].codePointCount(0, f[1].length());
                double count = Double.parseDouble(f[2]);
                if (f.length == 4 && characters >= 2 && characters <= 4) {
                    double observed = Double.parseDouble(f[3]);
                    if (observed > 0) corpusEvidence.merge(f[1],
                        .75 * (characters - 1) * Math.min(1, Math.log1p(observed) / Math.log1p(300)), Math::max);
                }
                if (characters >= 2 && characters <= 4) {
                    // All bundled vocabulary supplies evidence, not just a small HK list.
                    // Corpus counts calibrate confidence; local authored priorities retain
                    // their stronger preference without pretending to be measured counts.
                    double evidence = localUsage ? 2 * (characters - 1) + (characters >= 3 ? 2 : 0)
                        : .45 * (characters - 1) * Math.min(1, Math.log1p(count) / Math.log1p(3000));
                    phraseEvidence.merge(f[1], evidence, Math::max);
                }
                wordCounts.merge(f[1], count, Math::max);
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
        return decode(input,learned,context,null);
    }

    public List<String> decode(String input, ToIntBiFunction<String, String> learned, String context,
            ContextLearning.Preferences contextual) {
        String code = input.toLowerCase(Locale.ROOT);
        if (code.length() < 3 || code.length() > 48 || !code.matches("[a-z]+")) return Collections.emptyList();
        List<List<Path>> lattice = new ArrayList<>();
        for (int i = 0; i <= code.length(); i++) lattice.add(new ArrayList<>());
        // Independent word scores are immutable within this decode. Repeated
        // suffix codes must not run every scorer again for the same word.
        Map<String, Double> independentScores = new HashMap<>();
        ModelScoreCache modelScores = model == null ? null : new ModelScoreCache();
        List<List<Token>> following = new ArrayList<>();
        for (int i = 0; i <= code.length(); i++) following.add(followingWords(code, i, independentScores, modelScores));
        lattice.get(0).add(new Path("", 0));
        for (int pos = 0; pos < code.length(); pos++) {
            if (Thread.currentThread().isInterrupted()) return Collections.emptyList();
            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);
            if (paths.isEmpty()) continue;
            Map<Path, String> histories = new IdentityHashMap<>();
            for (Path path : paths) histories.put(path, sentenceContext(context + path.text));
            Map<String, Map<String, Double>> boundaryScores = new HashMap<>();
            boundaryScores.put("", independentScores);
            for (int length = 1; length <= Math.min(16, code.length() - pos); length++) {
                String part = code.substring(pos, pos + length);
                LinkedHashMap<String, Double> options = new LinkedHashMap<>();
                List<Token> known = personalizedTokens(part, learned);
                for (int j = 0; j < Math.min(24, known.size()); j++) options.put(known.get(j).text, known.get(j).score);
                for (Token token : contextWords(known, paths, histories, boundaryScores, independentScores, modelScores))
                    options.putIfAbsent(token.text, token.score);
                if (length <= 2) {
                    List<String> letters = new ArrayList<>();
                    for (String word : dictionary.quickCandidates(part)) if (hanText(word)) letters.add(word);
                    letters.sort(Comparator.comparingInt((String w) -> learned.applyAsInt(part, w)).reversed());
                    for (int j = 0; j < Math.min(24, letters.size()); j++) {
                        String word = letters.get(j);
                        options.putIfAbsent(word, (double) dictionary.frequency(word));
                    }
                    for (String character : contextCharacters(letters, paths, histories, boundaryScores, modelScores))
                        options.putIfAbsent(character, (double) dictionary.frequency(character));
                    if(contextual!=null) {
                        Map<String,Integer> favored=new LinkedHashMap<>();
                        for(String history:new LinkedHashSet<>(histories.values()))
                            for(String character:contextual.favored(history,part))
                                if(letters.contains(character)) favored.merge(character,contextual.weight(history,part,character),Math::max);
                        List<String> protectedChoices=new ArrayList<>(favored.keySet());
                        protectedChoices.sort(Comparator.comparingInt((String w)->favored.get(w)).reversed());
                        for(int j=0;j<Math.min(4,protectedChoices.size());j++) {
                            String character=protectedChoices.get(j);
                            options.putIfAbsent(character,(double)dictionary.frequency(character));
                        }
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
                    int characters = word.codePointCount(0, word.length());
                    int boundaryLength = Math.min(12, characters);
                    String first = boundaryLength == characters ? word
                        : word.substring(0, word.offsetByCodePoints(0, boundaryLength));
                    // The common <=12-character case subtracts a score from
                    // itself. Its exact result is zero; avoid both full calls.
                    double internalScore = boundaryLength == characters ? 0
                        : independentScores.computeIfAbsent(word, text -> languageScore("", text, modelScores))
                            - independentScores.computeIfAbsent(first, text -> languageScore("", text, modelScores));
                    for (Path prefix : paths) {
                        String history = histories.get(prefix);
                        Map<String, Double> cached = boundaryScores.computeIfAbsent(history, h -> new HashMap<>());
                        double score = cached.computeIfAbsent(first, wordStart -> languageScore(history, wordStart, modelScores)) + internalScore;
                        if(contextual!=null) score+=contextualScore(history,word,codes,contextual);
                        // A modest word bonus, with character likelihood applied across token boundaries.
                        double wordBonus = characters > 1 ? Math.min(1.5, Math.log1p(choice.getValue()) / 10) * (characters - 1) : 0;
                        target.add(new Path(prefix.text + choice.getKey(), prefix.score + score + wordBonus + bonus));
                    }
                }
                if (target.size() > 1024) lattice.set(pos + length,
                    pos + length == code.length() && sentenceRanker != null
                        ? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));
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
                    languageScore(context, token.text, modelScores) + Math.min(8, Math.log1p(token.score) * .7)
                    + (contextual==null ? 0 : contextualScore(context,token.text,dictionary.matchQuickCodes(code,token.text),contextual))
                    + personalBonus(learned.applyAsInt(code, token.text), 6, 1.5)));
        for (Token token : model == null ? wholeWords : Collections.<Token>emptyList()) {
            if (!dictionary.matchQuickCodes(code, token.text).isEmpty() && !result.contains(token.text)) result.add(token.text);
            if (result.size() == 5) break;
        }
        List<Path> completed = pruneFinal(lattice.get(code.length()));
        double bestScore = completed.isEmpty() ? Double.NEGATIVE_INFINITY : completed.get(0).score;
        for (Path path : completed) {
            // A score gap is uncertainty, not proof that unfamiliar Chinese is invalid.
            // Keep attested words and explicit character sequences; Single mode remains available.
            if (model != null && path.text.codePointCount(0, path.text.length()) > 3
                    && path.score < bestScore - SENTENCE_SCORE_MARGIN && !knownWord(path.text)
                    && !learnedSequence(code, path.text, learned)
                    && (contextual==null || !ContextLearning.supports(context,InputCandidate.chinese(dictionary,code,path.text),contextual))) continue;
            if (path.text.codePointCount(0, path.text.length()) > 1 && !result.contains(path.text)) result.add(path.text);
            if (result.size() == (sentenceRanker == null ? 20 : FINAL_POOL)) break;
        }
        // Correct the bounded, confidence-eligible final pool before its display
        // cutoff. Exact-code checks and original personal path bonuses still apply.
        if (model != null && sentenceRanker != null && result.size() > 1) {
            Map<String, Double> scores = new HashMap<>();
            for (Path path : completed) if (result.contains(path.text))
                scores.put(path.text, path.score + sentenceRanker.score(context, path.text));
            String original = result.get(0);
            double support = structuralSupport(context, original);
            Comparator<String> order = Comparator.comparingDouble((String text) -> scores.get(text)).reversed();
            // Protect the established winner while preserving the residual
            // model's full relative order for every remaining candidate.
            if (support > 0) order = Comparator.comparingInt((String text) -> text.equals(original) ? 0 : 1).thenComparing(order);
            result.sort(order);
        }
        // Explicit repeated choices outrank statistical guesses. Zero counts preserve
        // the existing context order; only exact, bundled words can be personalized.
        result.sort(Comparator.comparingInt((String text) -> knownWord(text)
            ? learned.applyAsInt(code, text) : 0).reversed());
        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));
        return result;
    }

    /** Existing positive sentence relations outrank a less-supported statistical replacement. */
    private double structuralSupport(String prefix, String text) {
        return Math.max(0, completionBonus(prefix, text) + handoverBonus(prefix, text)
            + ClauseRelations.score(prefix, text) + clauseStartStrength * ClauseStartRelations.score(prefix, text));
    }

    private static double contextualScore(String context,String word,List<String> codes,ContextLearning.Preferences preferences) {
        String history=ContextLearning.tail(context);int at=0;double score=0;
        for(String code:codes) {
            String character=new String(Character.toChars(word.codePointAt(at)));at+=character.length();
            score+=personalBonus(preferences.weight(history,code,character),4,1.25);
            history=ContextLearning.tail(history+character);
        }
        return score;
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

    /** Protect a few attested words excluded by frequency, only with actual left-context support. */
    private List<Token> contextWords(List<Token> known, List<Path> paths, Map<Path, String> histories,
            Map<String, Map<String, Double>> boundaryScores, Map<String, Double> independentScores,
            ModelScoreCache modelScores) {
        if (model == null || known.size() <= 24) return Collections.emptyList();
        Set<String> contexts = new LinkedHashSet<>();
        for (Path path : paths) {
            contexts.add(histories.get(path));
            if (contexts.size() == 4) break;
        }
        contexts.remove("");
        if (contexts.isEmpty()) return Collections.emptyList();
        Map<Token, Double> scores = new IdentityHashMap<>();
        for (int i = 24; i < Math.min(64, known.size()); i++) {
            Token token = known.get(i);
            int size = token.text.codePointCount(0, token.text.length());
            if (size < 2 || size > 8) continue;
            double independent = independentScores.computeIfAbsent(token.text, text -> languageScore("", text, modelScores));
            for (String context : contexts) {
                if (context.isEmpty()) continue;
                double conditional = boundaryScores.computeIfAbsent(context, key -> new HashMap<>())
                    .computeIfAbsent(token.text, text -> languageScore(context, text, modelScores));
                double lift = conditional - independent;
                if (lift > .25) scores.merge(token, lift + Math.min(2, Math.log1p(token.score) / 10), Math::max);
            }
        }
        List<Token> result = new ArrayList<>(scores.keySet());
        result.sort(Comparator.comparingDouble((Token token) -> scores.get(token)).reversed()
            .thenComparing(token -> token.text));
        return result.subList(0, Math.min(4, result.size()));
    }

    /** A frequency cutoff must not hide a character that fits an active context. */
    private List<String> contextCharacters(List<String> letters, List<Path> paths, Map<Path, String> histories,
            Map<String, Map<String, Double>> boundaryScores, ModelScoreCache modelScores) {
        if (model == null || letters.size() <= 24) return Collections.emptyList();
        Set<String> contexts = new LinkedHashSet<>();
        for (Path path : paths) {
            contexts.add(histories.get(path));
            if (contexts.size() == 4) break;
        }
        Map<String, Double> scores = new HashMap<>();
        for (String context : contexts) {
            Map<String, Double> conditional = boundaryScores.computeIfAbsent(context, key -> new HashMap<>());
            double floor = Double.POSITIVE_INFINITY;
            for (int i = 0; i < 24; i++) floor = Math.min(floor,
                conditional.computeIfAbsent(letters.get(i), text -> languageScore(context, text, modelScores)));
            for (int i = 24; i < letters.size(); i++) {
                String character = letters.get(i);
                if (i >= 64 && !HK_PARTICLES.contains(character)) continue;
                double score = conditional.computeIfAbsent(character, text -> languageScore(context, text, modelScores));
                if (score > floor) scores.merge(character, score, Math::max);
            }
        }
        List<String> result = new ArrayList<>(scores.keySet());
        result.sort(Comparator.comparingDouble((String text) -> scores.get(text)).reversed().thenComparing(text -> text));
        return result.subList(0, Math.min(4, result.size()));
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
        return languageScore(prefix, text, null);
    }

    private double languageScore(String prefix, String text, ModelScoreCache modelScores) {
        if (model != null) return (modelScores == null ? model.score(prefix, text) : modelScores.score(prefix, text))
            + (modelScores == null ? phraseBonus(prefix, text) : modelScores.phraseScore(prefix, text))
            + completionBonus(prefix, text)
            + handoverBonus(prefix, text) + ClauseRelations.score(prefix, text)
            + (phraseModel == null ? 0 : phraseModel.score(prefix, text))
            + (candidateRanker == null ? 0 : candidateRanker.score(prefix, text))
            + (wordRanker == null ? 0 : wordRanker.score(prefix, text))
            + (clauseStartStrength == 0 ? 0 : clauseStartStrength * ClauseStartRelations.score(prefix, text));
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

    private static int actionConfidence(String history, int at) {
        boolean sender = (at > 0 && "我你佢".indexOf(history.charAt(at - 1)) >= 0)
            || (at > 1 && history.charAt(at - 1) == '哋' && "我你佢".indexOf(history.charAt(at - 2)) >= 0);
        return sender ? 3 : 2;
    }

    private static int handoverConfidence(String history) {
        int confidence = 0;
        // A reply takes a person directly, unlike a handover's 畀/俾 marker.
        for (int i = 0; i + 2 < history.length(); i++)
            if (history.charAt(i) == '覆' && "咗返緊".indexOf(history.charAt(i + 1)) >= 0)
                for (String recipient : RECIPIENTS)
                    if (history.startsWith(recipient, i + 2)) confidence = Math.max(confidence, actionConfidence(history, i));
        for (int at = 0; at < history.length(); at++) {
            char marker = history.charAt(at);
            if (marker != '畀' && marker != '俾') continue;
            int action = 0;
            for (int i = 0; i + 1 < at; i++)
                if (HANDOVER_ACTIONS.indexOf(history.charAt(i)) >= 0 && "咗返緊齊".indexOf(history.charAt(i + 1)) >= 0) {
                    action = Math.max(action, actionConfidence(history, i));
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
                // These corpora can overlap. Treat observed counts as another
                // source of word evidence, not independent evidence to sum.
                // Stronger authored HK usage priors remain effective.
                matched += Math.max(phraseEvidence.getOrDefault(suffix, 0.0),
                    corpusEvidence.getOrDefault(suffix, 0.0));
            }
            if (count >= 3) {
                String lastThree = history.substring(history.offsetByCodePoints(0, count - 3));
                int[] action = lastThree.codePoints().toArray();
                if ("你我佢".indexOf(action[0]) >= 0 && ACTIONS.indexOf(action[1]) >= 0 && "咗返緊齊".indexOf(action[2]) >= 0) {
                    structural += 1.5;
                    // Modern authored action/status phrases can be sparse in the older corpus.
                    // Back off only their productive subject/predicate transition, with a cap;
                    // keep the actual object's likelihood and all typed-code constraints.
                    structural += predicateBackoff.getOrDefault(lastThree, 0.0);
                }
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
    private List<Token> followingWords(String code, int pos, Map<String, Double> independentScores, ModelScoreCache modelScores) {
        if (model == null) return Collections.emptyList();
        List<Token> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        List<Token> alternatives = new ArrayList<>();
        for (int length = 2; length <= Math.min(16, code.length() - pos); length++) {
            List<Token> tokens = vocabulary.getOrDefault(code.substring(pos, pos + length), Collections.emptyList());
            for (int i = 0; i < Math.min(2, tokens.size()); i++) {
                String text = tokens.get(i).text;
                int characters = text.codePointCount(0, text.length());
                if (characters < 2 || characters > 8 || !seen.add(text)) continue;
                if (length <= 8 && characters <= 4 && result.size() < LOOKAHEAD_WORDS)
                    result.add(new Token(text, independentScores.computeIfAbsent(text, word -> languageScore("", word, modelScores))));
                else alternatives.add(tokens.get(i));
            }
        }
        alternatives.sort(Comparator.comparingDouble((Token token) ->
            (token.text.codePointCount(0, token.text.length()) - 1)
                * Math.min(1, Math.log1p(token.score) / Math.log1p(3000))).reversed()
            .thenComparing(token -> token.text));
        for (int i = 0; i < Math.min(EXTRA_LOOKAHEAD_WORDS, alternatives.size()); i++) {
            Token token = alternatives.get(i);
            result.add(new Token(token.text, independentScores.computeIfAbsent(token.text, word -> languageScore("", word, modelScores))));
        }
        return result;
    }

    private List<Path> prune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {
        if (following.isEmpty() || input.size() <= BEAM) return prune(input);
        Map<String, double[]> cached = new HashMap<>();
        Map<Path, Double> scores = new IdentityHashMap<>();
        Map<Path, Double> alternatives = new IdentityHashMap<>();
        for (Path path : input) {
            String tail = lookaheadContext(context + path.text);
            double[] evidence = cached.computeIfAbsent(tail, key -> {
                double first = Math.max(0, lookaheadScore(key, following.get(0).text, modelScores) - following.get(0).score);
                return new double[]{Math.min(2, first), Double.NaN};
            });
            scores.put(path, path.score + evidence[0]);
        }
        // Keep the original 48 paths. A bounded reserve protects alternative
        // histories supported by other matching words in the remaining codes.
        // Hints affect survival only; completed sentences retain their real scores.
        input.sort(Comparator.comparingDouble((Path p) -> scores.get(p)).reversed());
        List<Path> result = distinctPaths(input);
        Set<String> seen = new HashSet<>();
        for (Path path : result) seen.add(path.text);
        double floor = result.get(result.size() - 1).score - 4;
        // Only paths outside the original beam and close enough to its raw
        // score floor can enter the reserve. Defer extra model scores until
        // eligibility is known, without changing the surviving paths.
        for (Path path : input) {
            if (path.score < floor || seen.contains(path.text)) continue;
            String tail = lookaheadContext(context + path.text);
            double[] evidence = cached.get(tail);
            if (Double.isNaN(evidence[1])) {
                double best = evidence[0];
                for (int i = 1; best < 2 && i < following.size(); i++) {
                    Token next = following.get(i);
                    best = Math.max(best, lookaheadScore(tail, next.text, modelScores) - next.score);
                }
                evidence[1] = Math.min(2, best);
            }
            if (evidence[1] > .25) alternatives.put(path, path.score + evidence[1]);
        }
        List<Path> protectedPaths = new ArrayList<>(alternatives.keySet());
        protectedPaths.sort(Comparator.comparingDouble((Path p) -> alternatives.get(p)).reversed()
            .thenComparing(p -> p.text));
        Set<String> histories = new HashSet<>();
        for (Path path : result) histories.add(OfflineLanguageModel.contextTail(context + path.text));
        for (Path path : protectedPaths) {
            if (path.score < floor || !seen.add(path.text)) continue;
            if (!histories.add(OfflineLanguageModel.contextTail(context + path.text))) continue;
            result.add(path);
            if (result.size() == BEAM + PATH_RESERVE) break;
        }
        return result;
    }

    private String lookaheadContext(String text) {
        if (model == null || clauseStartStrength == 0) return OfflineLanguageModel.contextTail(text);
        String history = sentenceContext(text);
        // All following tokens are Han. Once the head is outside the 12-character
        // bound its prior is zero; retain the old four-character cache sharing.
        return !ClauseStartRelations.pending(history)
            ? "#" + OfflineLanguageModel.contextTail(history) : history;
    }

    private double lookaheadScore(String context, String text, ModelScoreCache modelScores) {
        String tail = OfflineLanguageModel.contextTail(context);
        double score = languageScore(tail, text, modelScores);
        if (model != null && clauseStartStrength != 0)
            score += clauseStartStrength * ((context.startsWith("#") ? 0 : ClauseStartRelations.score(context, text))
                - ClauseStartRelations.score(tail, text));
        return score;
    }

    private static List<Path> prune(List<Path> input) {
        input.sort(Comparator.comparingDouble((Path p) -> p.score).reversed());
        return distinctPaths(input);
    }

    private List<Path> pruneFinal(List<Path> input) {
        if (model == null || sentenceRanker == null) return prune(input);
        input.sort(Comparator.comparingDouble((Path p) -> p.score).reversed());
        List<Path> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (Path path : input) if (seen.add(path.text)) {
            result.add(path); if (result.size() == FINAL_POOL) break;
        }
        return result;
    }

    private static List<Path> distinctPaths(List<Path> input) {
        List<Path> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (Path path : input) if (seen.add(path.text)) { result.add(path); if (result.size() == BEAM) break; }
        return result;
    }
}
