package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;

/** Bounded offline word-lattice decoder, including one-code Quick characters. */
public final class QuickDecoder {
    private static final int BEAM = 32;
    private final DictionaryEngine dictionary;
    private final Map<String, List<Token>> vocabulary = new HashMap<>();
    private static final class Token {
        final String text; final double score;
        Token(String text, double score) { this.text = text; this.score = score; }
    }
    private static final class Path {
        final String text; final double score;
        Path(String text, double score) { this.text = text; this.score = score; }
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input) throws IOException {
        this.dictionary = dictionary;
        try (BufferedReader reader = new BufferedReader(input)) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("#")) continue;
                String[] f = line.split("\t");
                if (f.length == 3) vocabulary.computeIfAbsent(f[0], k -> new ArrayList<>())
                    .add(new Token(f[1], Math.log((Double.parseDouble(f[2]) + 1) / 10000000.0)));
            }
        }
        for (List<Token> tokens : vocabulary.values()) tokens.sort(Comparator.comparingDouble((Token t) -> t.score).reversed());
    }

    public List<String> decode(String input, ToIntBiFunction<String, String> learned) {
        String code = input.toLowerCase(Locale.ROOT);
        if (code.length() < 3 || code.length() > 48 || !code.matches("[a-z]+")) return Collections.emptyList();
        List<List<Path>> lattice = new ArrayList<>();
        for (int i = 0; i <= code.length(); i++) lattice.add(new ArrayList<>());
        lattice.get(0).add(new Path("", 0));
        for (int pos = 0; pos < code.length(); pos++) {
            List<Path> paths = prune(lattice.get(pos));
            if (paths.isEmpty()) continue;
            for (int length = 1; length <= Math.min(16, code.length() - pos); length++) {
                String part = code.substring(pos, pos + length);
                LinkedHashMap<String, Double> options = new LinkedHashMap<>();
                List<Token> known = vocabulary.getOrDefault(part, Collections.emptyList());
                for (int j = 0; j < Math.min(16, known.size()); j++) options.put(known.get(j).text, known.get(j).score);
                if (length <= 2) {
                    List<String> letters = new ArrayList<>(dictionary.quickCandidates(part));
                    letters.sort(Comparator.comparingInt((String w) -> learned.applyAsInt(part, w)).reversed());
                    for (int j = 0; j < Math.min(24, letters.size()); j++) {
                        String word = letters.get(j);
                        options.putIfAbsent(word, -13.0 - j * .1);
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
                    for (Path prefix : paths) target.add(new Path(prefix.text + choice.getKey(), prefix.score + choice.getValue() + bonus));
                }
                if (target.size() > 1024) lattice.set(pos + length, prune(target));
            }
        }
        List<String> result = new ArrayList<>();
        for (Path path : prune(lattice.get(code.length()))) {
            if (path.text.codePointCount(0, path.text.length()) > 1) result.add(path.text);
            if (result.size() == 20) break;
        }
        return result;
    }

    private static List<Path> prune(List<Path> input) {
        input.sort(Comparator.comparingDouble((Path p) -> p.score).reversed());
        List<Path> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (Path path : input) if (seen.add(path.text)) { result.add(path); if (result.size() == BEAM) break; }
        return result;
    }
}
