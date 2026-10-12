package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Immutable residual evidence for a whole, already generated candidate. */
public final class SentenceRanker {
    private static final int[] HAN_RANGES = {0x3400,0x4DBF,0x4E00,0x9FFF,0xF900,0xFAFF,
        0x2E80,0x2E99,0x2E9B,0x2EF3,0x2F00,0x2FD5,0x3005,0x3005,0x3007,0x3007,
        0x3021,0x3029,0x3038,0x303B,0x16FE2,0x16FE3,0x16FF0,0x16FF1,0x20000,0x2A6DF,
        0x2A700,0x2B73F,0x2B740,0x2B81F,0x2B820,0x2CEAF,0x2CEB0,0x2EBEF,0x2EBF0,0x2EE5F,
        0x2F800,0x2FA1F,0x30000,0x3134F,0x31350,0x323AF,0x323B0,0x3347F};
    private static final String MARKERS = "我你佢係唔冇未有咗緊過會可要想就先再都又嘅啊呀喎呢嗎啦喇囉啲";
    private final Map<String, Float> weights;
    private final float strength, limit;
    private final int roleSchema;

    private SentenceRanker(Map<String, Float> weights, float strength, float limit, int roleSchema) {
        this.weights = Collections.unmodifiableMap(weights); this.strength = strength; this.limit = limit;
        this.roleSchema = roleSchema;
    }

    public static SentenceRanker load(InputStream encoded) throws IOException {
        try (DataInputStream input = new DataInputStream(new BufferedInputStream(new GZIPInputStream(
                Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if (input.readInt() != 0x53524b32) throw new IOException("Unsupported sentence ranker");
            int count = input.readInt(), roleSchema = input.readInt(); float strength = input.readFloat(), limit = input.readFloat();
            if (count < 0 || count > 16000 || !Float.isFinite(strength) || strength < 0 || strength > 2
                    || roleSchema < 1 || roleSchema > 2
                    || !Float.isFinite(limit) || limit <= 0 || limit > 3) throw new IOException("Invalid sentence ranker bounds");
            Map<String, Float> weights = new HashMap<>();
            for (int i = 0; i < count; i++) {
                int size = input.readUnsignedShort();
                if (size < 3 || size > 64) throw new IOException("Invalid sentence feature size");
                byte[] bytes = new byte[size]; input.readFully(bytes);
                String key = StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString();
                float weight = input.readFloat();
                if (!validKey(key) || !Float.isFinite(weight) || Math.abs(weight) > 1.5
                        || weights.put(key, weight) != null) throw new IOException("Invalid sentence feature");
            }
            if (input.read() != -1) throw new IOException("Unexpected sentence ranker data");
            return new SentenceRanker(weights, strength, limit, roleSchema);
        } catch (IllegalArgumentException e) { throw new IOException("Invalid sentence ranker encoding", e); }
    }

    private static boolean roleKey(String text) { return text.length() == 1 && "PNATVOMB".contains(text); }
    private static boolean han(int cp) {
        for (int i = 0; i < HAN_RANGES.length; i += 2) if (cp >= HAN_RANGES[i] && cp <= HAN_RANGES[i + 1]) return true;
        return false;
    }
    private static boolean hanText(String text) { return !text.isEmpty() && text.codePoints().allMatch(SentenceRanker::han); }
    private static boolean oneHan(String text) { return text.codePointCount(0, text.length()) == 1 && hanText(text); }
    private static boolean validKey(String key) {
        String[] p = key.split("\\|", -1);
        if (p.length == 2 && "WSE".contains(p[0]) && p[0].length() == 1) {
            int count = p[1].codePointCount(0, p[1].length());
            return hanText(p[1]) && (p[0].equals("W") ? count >= 2 && count <= 4 : count >= 1 && count <= 3);
        }
        if (p.length != 4) return false;
        if (p[0].equals("K") || p[0].equals("R")) {
            if (!Arrays.asList("2", "3", "4", "5").contains(p[2])) return false;
            return p[0].equals("K") ? oneHan(p[1]) && oneHan(p[3]) : roleKey(p[1]) && roleKey(p[3]);
        }
        if (!Arrays.asList("s", "m", "l").contains(p[2]) || !roleKey(p[3])) return false;
        return p[0].equals("D") ? roleKey(p[1]) : p[0].equals("H") && oneHan(p[1]) && MARKERS.contains(p[1]);
    }

    private static String role(int cp, int schema) {
        if ("我你佢".indexOf(cp) >= 0) return "P";
        if ("唔冇未".indexOf(cp) >= 0) return "N";
        if ("咗緊過".indexOf(cp) >= 0) return "A";
        if ("嘅啊呀喎呢嗎啦喇囉".indexOf(cp) >= 0) return "T";
        if ("係有會可要想".indexOf(cp) >= 0) return "V";
        if (schema >= 2 && "就先再都又".indexOf(cp) >= 0) return "M";
        if (schema >= 2 && cp == '啲') return "B";
        return "O";
    }

    private static String character(int cp) { return new String(Character.toChars(cp)); }
    private static void add(Map<String, Integer> result, String key) { result.merge(key, 1, (a, b) -> Math.min(2, a + b)); }

    /** Bounded short features; punctuation/Latin reset skipped relations. */
    static Map<String, Integer> features(String preceding, String text) {
        return features(preceding, text, 2);
    }
    static Map<String, Integer> features(String preceding, String text, int roleSchema) {
        int start = preceding.length(), count = 0;
        while (start > 0 && count < 12) {
            int cp = preceding.codePointBefore(start);
            if (!han(cp)) break;
            start -= Character.charCount(cp); count++;
        }
        boolean initial = count == 0;
        int[] history = new int[6]; int used = 0;
        String tail = preceding.substring(start);
        int from = tail.offsetByCodePoints(0, Math.max(0, count - 5));
        for (int at = from; at < tail.length();) {
            int cp = tail.codePointAt(at); at += Character.charCount(cp); history[used++] = cp;
        }
        Map<String, Integer> result = new LinkedHashMap<>();
        for (int at = 0; at < text.length();) {
            int cp = text.codePointAt(at); at += Character.charCount(cp);
            if (!han(cp)) { used = 0; continue; }
            history[used] = cp;
            for (int n = 2; n <= Math.min(4, used + 1); n++) add(result, "W|" + new String(history, used + 1 - n, n));
            for (int distance = 2; distance <= Math.min(5, used); distance++) {
                int previous = history[used - distance];
                if (MARKERS.indexOf(previous) >= 0 || MARKERS.indexOf(cp) >= 0) {
                    add(result, "K|" + character(previous) + "|" + distance + "|" + character(cp));
                    add(result, "R|" + role(previous, roleSchema) + "|" + distance + "|" + role(cp, roleSchema));
                }
            }
            if (used == 5) System.arraycopy(history, 1, history, 0, 5); else used++;
        }
        int end = 0, firstCount = 0;
        while (end < text.length() && han(text.codePointAt(end))) {
            end += Character.charCount(text.codePointAt(end)); firstCount++;
        }
        if (initial) for (int n = 1; n <= Math.min(3, firstCount); n++)
            add(result, "S|" + text.substring(0, text.offsetByCodePoints(0, n)));
        int tailStart = text.length(), tailCount = 0;
        while (tailStart > 0 && tailCount < 3 && han(text.codePointBefore(tailStart))) {
            tailStart -= Character.charCount(text.codePointBefore(tailStart)); tailCount++;
        }
        for (int n = 1; n <= tailCount; n++) add(result, "E|" + text.substring(text.offsetByCodePoints(text.length(), -n)));
        if (initial && end == text.length() && firstCount > 0) {
            int first = text.codePointAt(0), last = text.codePointBefore(text.length());
            String bucket = firstCount <= 4 ? "s" : firstCount <= 8 ? "m" : "l";
            add(result, "D|" + role(first, roleSchema) + "|" + bucket + "|" + role(last, roleSchema));
            if (MARKERS.indexOf(first) >= 0) add(result, "H|" + character(first) + "|" + bucket + "|" + role(last, roleSchema));
        }
        return result;
    }

    public double score(String preceding, String text) {
        if (strength == 0 || text.isEmpty()) return 0;
        double result = 0;
        for (Map.Entry<String, Integer> feature : features(preceding, text, roleSchema).entrySet()) {
            Float weight = weights.get(feature.getKey());
            if (weight != null) result += weight * feature.getValue();
        }
        return strength * Math.max(-limit, Math.min(limit, result));
    }

    public int entryCount() { return weights.size(); }
}
