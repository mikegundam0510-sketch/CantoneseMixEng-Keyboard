package hk.kaiboard.android;

import java.util.*;

/** User-authored shortcuts only; never collected from editor text. */
final class CustomPhrases {
    static final int LIMIT = 100;
    static boolean valid(String code, String phrase) {
        return code != null && code.matches("[a-zA-Z]{1,24}") && phrase != null
            && !phrase.trim().isEmpty() && phrase.length() <= 100
            && !phrase.contains("\n") && !phrase.contains("\r") && !phrase.contains("\t");
    }
    static LinkedHashMap<String, String> parse(String saved) {
        LinkedHashMap<String, String> result = new LinkedHashMap<>();
        for (String line : saved.split("\n")) {
            String[] f = line.split("\t", 2);
            if (f.length == 2 && valid(f[0], f[1]) && result.size() < LIMIT)
                result.put(f[0].toLowerCase(Locale.ROOT), f[1]);
        }
        return result;
    }
    static String save(Map<String, String> phrases) {
        List<String> lines = new ArrayList<>();
        for (Map.Entry<String, String> e : phrases.entrySet()) {
            if (lines.size() >= LIMIT) break;
            if (valid(e.getKey(), e.getValue())) lines.add(e.getKey().toLowerCase(Locale.ROOT) + "\t" + e.getValue());
        }
        return String.join("\n", lines);
    }
}
