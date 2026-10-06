package hk.kaiboard.android;

import java.io.*;
import java.util.*;

/** Offline, opt-in suggestions; spelling repairs are never silently applied. */
public final class EnglishEngine {
    private static final java.util.regex.Pattern WORD = java.util.regex.Pattern.compile("[A-Za-z][A-Za-z'-]{0,39}");
    private List<String> cachedPersonal = Collections.emptyList();
    private Map<String, String> cachedWords;
    private final Map<String, String> words = new LinkedHashMap<>();
    private Map<String, String> indexedWords;
    private NavigableMap<String, String> prefixIndex;
    private Map<Integer, List<String>> lengthIndex;
    private Map<String, Integer> ranks;
    private String lastLikelyInput;
    private boolean lastLikely;
    private final LinkedHashMap<String, List<String>> suggestionCache = new LinkedHashMap<>();
    private void index(Map<String, String> all) {
        if (indexedWords == all) return;
        indexedWords = all; prefixIndex = new TreeMap<>(all); lengthIndex = new HashMap<>(); ranks = new HashMap<>();
        int rank = 0;
        for (String word : all.keySet()) {
            ranks.put(word, rank++);
            lengthIndex.computeIfAbsent(word.length(), key -> new ArrayList<>()).add(word);
        }
        lastLikelyInput = null; suggestionCache.clear();
    }
    private List<String> nearbyLengths(int length) {
        List<String> result = new ArrayList<>();
        for (int size = length - 1; size <= length + 1; size++) result.addAll(lengthIndex.getOrDefault(size, Collections.emptyList()));
        result.sort(Comparator.comparingInt(ranks::get)); return result;
    }
    public EnglishEngine(Reader input) throws IOException {
        try (BufferedReader reader = new BufferedReader(input)) {
            String line;
            while ((line = reader.readLine()) != null) if (validWord(line)) words.put(line.toLowerCase(Locale.ROOT), line);
        }
    }
    public static boolean validWord(String word) { return WORD.matcher(word).matches(); }
    private synchronized Map<String, String> combined(Collection<String> personal) {
        if (personal.isEmpty()) { cachedPersonal = Collections.emptyList(); cachedWords = null; return words; }
        List<String> snapshot = new ArrayList<>(personal);
        if (snapshot.equals(cachedPersonal) && cachedWords != null) return cachedWords;
        Map<String, String> result = new LinkedHashMap<>(words);
        for (String word : personal) if (validWord(word)) result.put(word.toLowerCase(Locale.ROOT), word);
        cachedPersonal = snapshot; cachedWords = result;
        return result;
    }
    public synchronized boolean likelyEnglish(String input, Collection<String> personal) {
        Map<String, String> all = combined(personal); index(all);
        if (input.equals(lastLikelyInput)) return lastLikely;
        String lower = input.toLowerCase(Locale.ROOT);
        boolean result = input.length() >= 3 && all.containsKey(lower)
            || input.length() >= 2 && input.equals(input.toUpperCase(Locale.ROOT)) && all.containsKey(lower);
        if (!result && input.length() >= 4) {
            String prefix = prefixIndex.ceilingKey(lower);
            result = prefix != null && prefix.startsWith(lower);
            if (!result) for (int length = lower.length()-1; length <= lower.length()+1; length++) {
                for (String word : lengthIndex.getOrDefault(length, Collections.emptyList()))
                    if (oneEdit(lower, word)) { result = true; break; }
                if (result) break;
            }
        }
        lastLikelyInput = input; lastLikely = result; return result;
    }
    public synchronized List<String> suggest(String input, Collection<String> personal, boolean repair) {
        if (!validWord(input)) return Collections.emptyList();
        String lower = input.toLowerCase(Locale.ROOT);
        Map<String, String> all = combined(personal); index(all);
        String cacheKey = (repair ? "1:" : "0:") + input;
        List<String> cached = suggestionCache.get(cacheKey);
        if (cached != null) return new ArrayList<>(cached);
        LinkedHashSet<String> result = new LinkedHashSet<>(); result.add(input);
        List<String> matches = new ArrayList<>();
        for (String word : prefixIndex.tailMap(lower, true).keySet()) {
            if (!word.startsWith(lower)) break;
            matches.add(word);
        }
        matches.sort(Comparator.comparingInt(ranks::get));
        for (String word : matches) {
            result.add(casing(input, all.get(word))); if (result.size() >= 12) break;
        }
        if (repair && input.length() >= 4 && result.size() < 12) for (String word : nearbyLengths(lower.length())) {
            if (!word.equals(lower) && oneEdit(lower, word)) result.add(casing(input, all.get(word)));
            if (result.size() >= 12) break;
        }
        List<String> values = new ArrayList<>(result);
        if (suggestionCache.size() >= 8) suggestionCache.remove(suggestionCache.keySet().iterator().next());
        suggestionCache.put(cacheKey, values);
        return new ArrayList<>(values);
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

