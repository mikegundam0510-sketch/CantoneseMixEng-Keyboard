package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.Base64;
import java.util.zip.GZIPInputStream;

/** Immutable signed relations learned from exact-code competitors; distinct short/word formats. */
public final class CandidateRanker {
    private final int maximumLength;
    private final float strength, endpointLimit;
    private final int[] starts, sizes, characters, targets;
    private final int[] rootIndex = new int[65536];
    private final float[] values;

    private CandidateRanker(int maximumLength, float strength, float endpointLimit,
                            int[] starts, int[] sizes, float[] values, int[] characters, int[] targets) {
        this.maximumLength = maximumLength; this.strength = strength; this.endpointLimit = endpointLimit;
        this.starts = starts; this.sizes = sizes; this.values = values;
        this.characters = characters; this.targets = targets;
        for (int i = starts[0]; i < starts[0] + sizes[0]; i++)
            if (characters[i] < rootIndex.length) rootIndex[characters[i]] = targets[i] + 1;
    }

    public static CandidateRanker load(InputStream encoded) throws IOException {
        return load(encoded, false);
    }

    /** Separate format for trained two/three-word relations of at most twelve Han characters. */
    public static CandidateRanker loadWords(InputStream encoded) throws IOException {
        return load(encoded, true);
    }

    private static CandidateRanker load(InputStream encoded, boolean wordRelations) throws IOException {
        try (DataInputStream data = new DataInputStream(new BufferedInputStream(
                new GZIPInputStream(Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if (data.readInt() != (wordRelations ? 0x57524b31 : 0x43524b31))
                throw new IOException("Unsupported candidate ranker");
            int length = data.readInt(), nodes = data.readInt(), edges = data.readInt();
            float strength = data.readFloat(), endpointLimit = data.readFloat();
            if (length < 2 || length > (wordRelations ? 12 : 3) || nodes < 1 || nodes > 150000 || edges != nodes - 1
                    || !Float.isFinite(strength) || strength < 0 || strength > 2
                    || !Float.isFinite(endpointLimit) || endpointLimit <= 0 || endpointLimit > 1.5f)
                throw new IOException("Invalid candidate ranker header");
            int[] starts = new int[nodes], sizes = new int[nodes];
            float[] values = new float[nodes];
            int next = 0;
            for (int i = 0; i < nodes; i++) {
                starts[i] = data.readInt(); sizes[i] = data.readInt(); values[i] = data.readFloat();
                if (starts[i] != next || sizes[i] < 0 || sizes[i] > edges - next
                        || !Float.isFinite(values[i]) || Math.abs(values[i]) > 1.5f)
                    throw new IOException("Invalid candidate ranker node");
                next += sizes[i];
            }
            if (next != edges || values[0] != 0) throw new IOException("Invalid candidate ranker tree");
            int[] characters = new int[edges], targets = new int[edges], depths = new int[nodes];
            for (int i = 0; i < nodes; i++) {
                int last = -1;
                if (i > 0 && depths[i] == 0) throw new IOException("Unreachable candidate ranker node");
                if (depths[i] < 2 && values[i] != 0) throw new IOException("Invalid candidate ranker feature");
                for (int j = starts[i]; j < starts[i] + sizes[i]; j++) {
                    characters[j] = data.readInt(); targets[j] = data.readInt();
                    int target = targets[j];
                    if (!OfflineLanguageModel.han(characters[j]) || characters[j] <= last
                            || target <= i || target >= nodes || depths[target] != 0 || depths[i] >= length)
                        throw new IOException("Invalid candidate ranker edge");
                    last = characters[j]; depths[target] = depths[i] + 1;
                }
            }
            if (data.read() != -1) throw new IOException("Unexpected candidate ranker data");
            return new CandidateRanker(length, strength, endpointLimit, starts, sizes, values, characters, targets);
        } catch (IllegalArgumentException e) {
            throw new IOException("Invalid candidate ranker encoding", e);
        }
    }

    private int child(int node, int character) {
        if (node == 0 && character < rootIndex.length) return rootIndex[character] - 1;
        int left = starts[node], right = left + sizes[node] - 1;
        while (left <= right) {
            int middle = (left + right) >>> 1;
            if (characters[middle] == character) return targets[middle];
            if (characters[middle] < character) left = middle + 1; else right = middle - 1;
        }
        return -1;
    }

    /** Charges signed relations at character endpoints, including the editor/context boundary.
     * Consults at most maximumLength - 1 preceding Han characters. Unknown text is neutral and punctuation
     * or Latin clears history. Splitting a sentence into decoder tokens preserves its score.
     */
    public double score(String preceding, String text) {
        if (strength == 0 || text.isEmpty()) return 0;
        if (text.codePointCount(0, text.length()) == 1) {
            int node = child(0, text.codePointAt(0));
            if (node < 0) return 0;
            // Most lattice edges add one character. Traverse only the matching
            // suffix instead of copying up to eleven context characters first.
            double endpoint = 0;
            int at = preceding.length();
            for (int depth = 1; at > 0 && depth < maximumLength; depth++) {
                int cp = preceding.codePointBefore(at);
                if (!OfflineLanguageModel.han(cp)) break;
                at -= Character.charCount(cp);
                node = child(node, cp);
                if (node < 0) break;
                endpoint += values[node];
            }
            return strength * Math.max(-endpointLimit, Math.min(endpointLimit, endpoint));
        }
        int[] history = new int[maximumLength];
        int start = preceding.length(), used = 0;
        while (start > 0 && used < maximumLength - 1) {
            int cp = preceding.codePointBefore(start);
            if (!OfflineLanguageModel.han(cp)) break;
            start -= Character.charCount(cp); used++;
        }
        int at = start;
        for (int i = 0; i < used; i++) {
            history[i] = preceding.codePointAt(at); at += Character.charCount(history[i]);
        }
        double result = 0;
        for (at = 0; at < text.length();) {
            int cp = text.codePointAt(at); at += Character.charCount(cp);
            if (!OfflineLanguageModel.han(cp)) { used = 0; continue; }
            history[used++] = cp;
            int node = child(0, cp);
            double endpoint = 0;
            for (int i = used - 2; node >= 0 && i >= 0; i--) {
                node = child(node, history[i]);
                if (node < 0) break;
                endpoint += values[node];
            }
            result += strength * Math.max(-endpointLimit, Math.min(endpointLimit, endpoint));
            if (used == maximumLength) System.arraycopy(history, 1, history, 0, --used);
        }
        return result;
    }

    public long arrayBytes() { return 12L * starts.length + 8L * characters.length + 4L * rootIndex.length; }
}
