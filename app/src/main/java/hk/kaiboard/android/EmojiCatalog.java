package hk.kaiboard.android;

import java.io.*;
import java.util.*;

/** Unicode 15.1 fully-qualified emoji, grouped for browsing; immutable after load. */
public final class EmojiCatalog {
    public static final String[] LABELS = {"表情", "人物", "動物", "飲食", "交通", "活動", "物品", "符號", "旗幟"};
    public static final class Entry {
        public final String symbol, name;
        Entry(String symbol, String name) { this.symbol = symbol; this.name = name; }
    }
    private static final class Node { final Map<Character, Node> children = new HashMap<>(); boolean end; }
    private final Node reverse = new Node();
    private final List<List<Entry>> groups = new ArrayList<>();
    private final Map<String, List<Entry>> tones = new LinkedHashMap<>();
    private final Map<String, Entry> entries = new LinkedHashMap<>();
    public EmojiCatalog(Reader source) throws IOException {
        Map<String, Integer> ids = new LinkedHashMap<>();
        try (BufferedReader reader = new BufferedReader(source)) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.startsWith("#")) continue;
                String[] f = line.split("\t"); if (f.length != 3) continue;
                if (!ids.containsKey(f[0])) { ids.put(f[0], groups.size()); groups.add(new ArrayList<>()); }
                Entry entry = new Entry(f[1], f[2]); groups.get(ids.get(f[0])).add(entry); entries.put(entry.symbol, entry);
                tones.computeIfAbsent(toneKey(entry.symbol), key -> new ArrayList<>()).add(entry);
                Node n = reverse;
                for (int i = entry.symbol.length() - 1; i >= 0; i--) n = n.children.computeIfAbsent(entry.symbol.charAt(i), key -> new Node());
                n.end = true;
            }
        }
    }
    private static String toneKey(String symbol) {
        StringBuilder key = new StringBuilder();
        symbol.codePoints().filter(cp -> (cp < 0x1F3FB || cp > 0x1F3FF) && cp != 0xFE0F).forEach(key::appendCodePoint);
        return key.toString();
    }
    public List<Entry> skinVariants(String symbol) {
        return Collections.unmodifiableList(tones.getOrDefault(toneKey(symbol),Collections.emptyList()));
    }
    /** Keep one representative per tone family; every variant remains accessible by long press. */
    public List<Entry> browseGroup(int index) {
        Map<String, Entry> unique = new LinkedHashMap<>();
        for (Entry entry : groups.get(index)) unique.putIfAbsent(toneKey(entry.symbol), entry);
        return new ArrayList<>(unique.values());
    }
    public List<Entry> search(String query) {
        String q = query.trim().toLowerCase(Locale.ROOT);
        if (q.isEmpty()) return Collections.emptyList();
        List<Entry> result = new ArrayList<>();
        for (Entry entry : entries.values())
            if (entry.name.toLowerCase(Locale.ROOT).contains(q) || entry.symbol.equals(q)) result.add(entry);
        return result;
    }
    public int size() { return entries.size(); }
    public int groupCount() { return groups.size(); }
    public List<Entry> group(int index) { return Collections.unmodifiableList(groups.get(index)); }
    public List<Entry> recent(String saved) {
        List<Entry> result = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (String s : saved.split("\n")) if (entries.containsKey(s) && seen.add(s)) result.add(entries.get(s));
        return result;
    }
    public String remember(String saved, String symbol) {
        LinkedHashSet<String> result = new LinkedHashSet<>();
        if (entries.containsKey(symbol)) result.add(symbol);
        for (Entry e : recent(saved)) { if (result.size() >= 40) break; result.add(e.symbol); }
        return String.join("\n", result);
    }
    /** UTF-16 units for InputConnection.deleteSurroundingText, preserving entire known emoji. */
    public int deletionUnits(CharSequence beforeCursor) {
        if (beforeCursor == null || beforeCursor.length() == 0) return 0;
        int matched = 0, length = beforeCursor.length(); Node n = reverse;
        for (int i = length - 1; i >= 0; i--) {
            n = n.children.get(beforeCursor.charAt(i)); if (n == null) break;
            if (n.end) matched = length - i;
        }
        return matched > 0 ? matched : Character.charCount(Character.codePointBefore(beforeCursor, length));
    }
}
