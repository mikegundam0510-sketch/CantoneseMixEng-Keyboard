package hk.kaiboard.android;

import java.io.*;
import java.util.*;

/** Offline completion and conservative, explicitly selected spelling suggestions. */
final class EnglishEngine {
    private final NavigableSet<String> words = new TreeSet<>();
    private final List<String> preferred = new ArrayList<>();
    EnglishEngine(Reader source) throws IOException {
        try (BufferedReader reader = new BufferedReader(source)) {
            String line;
            while ((line = reader.readLine()) != null) {
                String word = line.trim().toLowerCase(Locale.ROOT);
                if (!word.matches("[a-z]{1,30}") || !words.add(word)) continue;
                if (preferred.size() < 256) preferred.add(word);
            }
        }
    }
    int size() { return words.size(); }
    List<String> suggest(String input, boolean spelling) {
        if (input.isEmpty()) return Collections.emptyList();
        String code = input.toLowerCase(Locale.ROOT);
        LinkedHashSet<String> result = new LinkedHashSet<>();
        for (String word : preferred) {
            if (word.startsWith(code) && !word.equals(code)) result.add(word);
            if (result.size() >= 8) break;
        }
        for (String word : words.tailSet(code, true)) {
            if (!word.startsWith(code) || result.size() >= 8) break;
            if (!word.equals(code)) result.add(word);
        }
        if (spelling && code.length() >= 3 && code.length() <= 24 && !words.contains(code)) {
            // One edit only; dictionary order breaks ties. Never silently replace typed text.
            Set<String> edits = new HashSet<>();
            for (int i = 0; i < code.length(); i++) {
                edits.add(code.substring(0, i) + code.substring(i + 1));
                if (i + 1 < code.length()) edits.add(code.substring(0, i) + code.charAt(i + 1) + code.charAt(i) + code.substring(i + 2));
                for (char c = 'a'; c <= 'z'; c++) edits.add(code.substring(0, i) + c + code.substring(i + 1));
            }
            for (int i = 0; i <= code.length(); i++)
                for (char c = 'a'; c <= 'z'; c++) edits.add(code.substring(0, i) + c + code.substring(i));
            List<String> matches = new ArrayList<>();
            for (String word : edits) if (words.contains(word)) matches.add(word);
            matches.sort(Comparator.comparingInt((String w) -> preferred.contains(w) ? preferred.indexOf(w) : Integer.MAX_VALUE).thenComparing(w -> w));
            for (String word : matches) { if (result.size() >= 8) break; result.add(word); }
        }
        List<String> output = new ArrayList<>();
        for (String word : result) {
            if (input.equals(input.toUpperCase(Locale.ROOT))) word = word.toUpperCase(Locale.ROOT);
            else if (Character.isUpperCase(input.charAt(0))) word = Character.toUpperCase(word.charAt(0)) + word.substring(1);
            output.add(word);
        }
        return output;
    }
}
