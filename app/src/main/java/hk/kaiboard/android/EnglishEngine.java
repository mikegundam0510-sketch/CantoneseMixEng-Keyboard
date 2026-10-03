package hk.kaiboard.android;

import java.io.*;
import java.util.*;

/** Offline, opt-in suggestions; spelling repairs are never silently applied. */
public final class EnglishEngine {
    private final Map<String, String> words = new LinkedHashMap<>();
    public EnglishEngine(Reader input) throws IOException {
        try (BufferedReader reader = new BufferedReader(input)) {
            String line;
            while ((line = reader.readLine()) != null) if (validWord(line)) words.put(line.toLowerCase(Locale.ROOT), line);
        }
    }
    public static boolean validWord(String word) { return word.matches("[A-Za-z][A-Za-z'-]{0,39}"); }
    private Map<String, String> combined(Collection<String> personal) {
        Map<String, String> result = new LinkedHashMap<>(words);
        for (String word : personal) if (validWord(word)) result.put(word.toLowerCase(Locale.ROOT), word);
        return result;
    }
    public boolean likelyEnglish(String input, Collection<String> personal) {
        String lower = input.toLowerCase(Locale.ROOT);
        Map<String, String> all = combined(personal);
        if (input.length() >= 3 && all.containsKey(lower)) return true;
        if (input.length() >= 2 && input.equals(input.toUpperCase(Locale.ROOT)) && all.containsKey(lower)) return true;
        if (input.length() >= 4) for (String word : all.keySet()) if (word.startsWith(lower)) return true;
        if (input.length() >= 4) for (String word : all.keySet()) if (oneEdit(lower, word)) return true;
        return false;
    }
    public List<String> suggest(String input, Collection<String> personal, boolean repair) {
        if (!validWord(input)) return Collections.emptyList();
        String lower = input.toLowerCase(Locale.ROOT);
        Map<String, String> all = combined(personal);
        LinkedHashSet<String> result = new LinkedHashSet<>(); result.add(input);
        for (Map.Entry<String, String> entry : all.entrySet())
            if (entry.getKey().startsWith(lower)) result.add(casing(input, entry.getValue()));
        if (repair && input.length() >= 4) for (Map.Entry<String, String> entry : all.entrySet())
            if (!entry.getKey().equals(lower) && oneEdit(lower, entry.getKey())) result.add(casing(input, entry.getValue()));
        return new ArrayList<>(result).subList(0, Math.min(12, result.size()));
    }
    public static String casing(String input, String word) {
        if (input.equals(input.toUpperCase(Locale.ROOT))) return word.toUpperCase(Locale.ROOT);
        if (Character.isUpperCase(input.charAt(0))) return Character.toUpperCase(word.charAt(0)) + word.substring(1);
        return word;
    }
    public List<int[]> spans(String input, Collection<String> personal) {
        Map<String, String> all = combined(personal); List<int[]> result = new ArrayList<>();
        for (int start = 0; start < input.length(); start++) {
            int best = -1;
            for (int end = Math.min(input.length(), start + 40); end >= start + 4; end--) {
                if (all.containsKey(input.substring(start, end).toLowerCase(Locale.ROOT))) { best = end; break; }
            }
            if (best >= 0) { result.add(new int[]{start, best}); start = best - 1; }
            if (result.size() == 4) break;
        }
        return result;
    }
    public static boolean oneEdit(String a, String b) {
        if (Math.abs(a.length() - b.length()) > 1 || a.equals(b)) return false;
        if (a.length() == b.length()) {
            int first = -1, second = -1;
            for (int i=0;i<a.length();i++) if (a.charAt(i)!=b.charAt(i)) {
                if (first < 0) first=i; else if (second < 0) second=i; else return false;
            }
            return second < 0 || second == first + 1 && a.charAt(first) == b.charAt(second) && a.charAt(second) == b.charAt(first);
        }
        String longer=a.length()>b.length()?a:b, shorter=a.length()>b.length()?b:a;
        int i=0,j=0,edits=0;
        while(i<longer.length() && j<shorter.length()) {
            if(longer.charAt(i)==shorter.charAt(j)){i++;j++;} else {i++;if(++edits>1)return false;}
        }
        return true;
    }
}
