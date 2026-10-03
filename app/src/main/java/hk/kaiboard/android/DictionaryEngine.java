package hk.kaiboard.android;

import java.io.*;
import java.util.*;

/** Immutable after loading; independent of Android so the actual dictionary is testable. */
public final class DictionaryEngine {
    private final Map<String, List<String>> cangjie = new HashMap<>();
    private final Map<String, List<String>> quick = new HashMap<>();
    private final List<String> english = new ArrayList<>();
    private final Map<String, Set<String>> reverseQuick = new HashMap<>();
    private int entries;
    private final Map<String, Integer> frequencies = new HashMap<>();
    private static final String HK_COMMON = "係唔嘅咗喺佢哋嘢咁啲冇嚟啦喎睇返畀攞噉咩食飲";
    // A small, explicit preference list, not a claimed statistical language model.
    private static final String COMMON = "的一是不了在人有我他這中大來上國個到說們為子和你地出道也時年得就那要下以生會自著去之過家學對可她裡後小麼心多天而能好都然沒日於起還發成事只作當想看文無開手十用主行方又如前所本見經頭面公同三已老從動兩長知民樣現分將外但身些與高意進把法此實回二理美點月明其種聲全工己話兒者向情部正名定女問力機給等幾很業最間新什打便位因重被走電四第門相次東海口使西再平真聽世氣信北南請香港謝唔嘅咗喺佢哋嘢咁啲冇嚟啦喎睇返畀攞嘥噉";

    public DictionaryEngine(Reader chinese, Reader words) throws IOException {
        this(chinese, words, null);
    }

    public DictionaryEngine(Reader chinese, Reader words, Reader counts) throws IOException {
        if (counts != null) try (BufferedReader reader = new BufferedReader(counts)) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] fields = line.split("\\t");
                if (fields.length == 2 && !line.startsWith("#"))
                    frequencies.put(fields[0], Integer.parseInt(fields[1]));
            }
        }
        try (BufferedReader reader = new BufferedReader(chinese)) {
            String line; boolean body = false;
            while ((line = reader.readLine()) != null) {
                if (line.equals("...")) { body = true; continue; }
                if (!body || line.startsWith("#")) continue;
                String[] fields = line.split("\t");
                if (fields.length < 2 || !fields[1].matches("[a-z]{1,5}")) continue;
                String word = fields[0], code = fields[1];
                add(cangjie, code, word);
                add(quick, quickCode(code), word);
                reverseQuick.computeIfAbsent(word, key -> new HashSet<>()).add(quickCode(code));
                entries++;
            }
        }
        Comparator<String> priority = Comparator.comparingInt(this::frequency).reversed();
        cangjie.values().forEach(list -> list.sort(priority));
        quick.values().forEach(list -> list.sort(priority));
        try (BufferedReader reader = new BufferedReader(words)) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (!line.isEmpty() && !line.startsWith("#")) english.add(line);
            }
        }
        if (entries < 1000) throw new IOException("Chinese dictionary is incomplete");
    }

    public int frequency(String word) {
        int count = frequencies.getOrDefault(word, 0);
        if (HK_COMMON.contains(word)) count = Math.max(count, 25000);
        int position = COMMON.indexOf(word);
        if (count == 0 && position >= 0) count = Math.max(1, 5000 - position * 10);
        return Math.max(1, count);
    }

    private static void add(Map<String, List<String>> index, String code, String word) {
        List<String> list = index.computeIfAbsent(code, key -> new ArrayList<>());
        if (!list.contains(word)) list.add(word);
    }

    public static String quickCode(String code) {
        if (code.isEmpty()) return "";
        return code.length() == 1 ? code : "" + code.charAt(0) + code.charAt(code.length() - 1);
    }

    public int entryCount() { return entries; }

    public List<String> quickCandidates(String code) {
        return Collections.unmodifiableList(quick.getOrDefault(code.toLowerCase(Locale.ROOT), Collections.emptyList()));
    }

    public List<String> matchQuickCodes(String input, String text) {
        List<String> result = new ArrayList<>();
        return match(input.toLowerCase(Locale.ROOT), 0, text, 0, result) ? result : Collections.emptyList();
    }

    private boolean match(String code, int pos, String text, int at, List<String> result) {
        if (at == text.length()) return pos == code.length();
        String character = new String(Character.toChars(text.codePointAt(at)));
        Set<String> choices = reverseQuick.getOrDefault(character, Collections.emptySet());
        for (int size = 2; size >= 1; size--) {
            if (pos + size > code.length()) continue;
            String part = code.substring(pos, pos + size);
            if (choices.contains(part)) {
                result.add(part);
                if (match(code, pos + size, text, at + character.length(), result)) return true;
                result.remove(result.size() - 1);
            }
        }
        return false;
    }

    public List<String> lookup(String input, boolean useQuick, boolean useCangjie, boolean useEnglish) {
        if (input.isEmpty()) return Collections.emptyList();
        String code = input.toLowerCase(Locale.ROOT);
        LinkedHashSet<String> result = new LinkedHashSet<>();
        if (useQuick && code.length() <= 2) result.addAll(quick.getOrDefault(code, Collections.emptyList()));
        if (useCangjie && code.length() <= 5) result.addAll(cangjie.getOrDefault(code, Collections.emptyList()));
        if (useEnglish) {
            int added = 0;
            for (String word : english) {
                if (word.startsWith(code) && !word.equals(code)) {
                    String suggestion = word;
                    if (input.equals(input.toUpperCase(Locale.ROOT))) suggestion = word.toUpperCase(Locale.ROOT);
                    else if (Character.isUpperCase(input.charAt(0))) suggestion = Character.toUpperCase(word.charAt(0)) + word.substring(1);
                    result.add(suggestion);
                    if (++added == 8) break;
                }
            }
        }
        result.add(input); // Literal input is always available, including unknown English words.
        return new ArrayList<>(result);
    }
}

