package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.Base64;
import java.util.zip.GZIPInputStream;

/** Immutable word-transition evidence trained from explicitly segmented public text. */
public final class PhraseLanguageModel {
    private final int maximumLength;
    private final float strength;
    private final int[] starts, sizes, characters, targets;
    private final int[] rootIndex = new int[65536];
    private final float[] values;

    private PhraseLanguageModel(int maximumLength, float strength, int[] starts, int[] sizes,
                                float[] values, int[] characters, int[] targets) {
        this.maximumLength = maximumLength; this.strength = strength;
        this.starts = starts; this.sizes = sizes; this.values = values;
        this.characters = characters; this.targets = targets;
        // Most scanned candidates have no word relation ending in their character.
        // A direct BMP index avoids a binary root search and history allocation.
        for (int i = starts[0]; i < starts[0] + sizes[0]; i++)
            if (characters[i] < rootIndex.length) rootIndex[characters[i]] = targets[i] + 1;
    }

    public static PhraseLanguageModel load(InputStream encoded) throws IOException {
        try (DataInputStream data = new DataInputStream(new BufferedInputStream(
                new GZIPInputStream(Base64.getMimeDecoder().wrap(new BufferedInputStream(encoded)))))) {
            if (data.readInt() != 0x574c4d31) throw new IOException("Unsupported phrase model");
            int length = data.readInt(), nodes = data.readInt(), edges = data.readInt();
            float strength = data.readFloat();
            if (length < 2 || length > 12 || nodes < 1 || nodes > 200000 || edges != nodes - 1
                    || !Float.isFinite(strength) || strength < 0 || strength > 2)
                throw new IOException("Invalid phrase model header");
            int[] starts = new int[nodes], sizes = new int[nodes];
            float[] values = new float[nodes];
            int next = 0;
            for (int i = 0; i < nodes; i++) {
                starts[i] = data.readInt(); sizes[i] = data.readInt(); values[i] = data.readFloat();
                if (starts[i] != next || sizes[i] < 0 || sizes[i] > edges - next
                        || !Float.isFinite(values[i]) || values[i] < 0 || values[i] > 3)
                    throw new IOException("Invalid phrase model node");
                next += sizes[i];
            }
            if (next != edges || values[0] != 0) throw new IOException("Invalid phrase model tree");
            int[] characters = new int[edges], targets = new int[edges], depths = new int[nodes];
            for (int i = 0; i < nodes; i++) {
                int last = -1;
                if (i > 0 && depths[i] == 0) throw new IOException("Unreachable phrase model node");
                for (int j = starts[i]; j < starts[i] + sizes[i]; j++) {
                    characters[j] = data.readInt(); targets[j] = data.readInt();
                    int target = targets[j];
                    if (!OfflineLanguageModel.han(characters[j]) || characters[j] <= last
                            || target <= i || target >= nodes || depths[target] != 0 || depths[i] >= length)
                        throw new IOException("Invalid phrase model edge");
                    last = characters[j]; depths[target] = depths[i] + 1;
                }
            }
            if (data.read() != -1) throw new IOException("Unexpected phrase model data");
            return new PhraseLanguageModel(length, strength, starts, sizes, values, characters, targets);
        } catch (IllegalArgumentException e) {
            throw new IOException("Invalid phrase model encoding", e);
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

    /** Evidence is charged once at each character endpoint, independent of decoder tokens.
     * Unknown relations are neutral. Only the strongest overlapping relation is used.
     * Punctuation/Latin clears history; no editor text is kept by this immutable model.
     */
    public double score(String preceding, String text) {
        if (strength == 0 || text.isEmpty()) return 0;
        if (text.codePointCount(0, text.length()) == 1 && child(0, text.codePointAt(0)) < 0) return 0;
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
            int node = child(0, cp); float best = node < 0 ? 0 : values[node];
            for (int i = used - 2; node >= 0 && i >= 0; i--) {
                node = child(node, history[i]);
                if (node < 0) break;
                best = Math.max(best, values[node]);
            }
            result += strength * best;
            if (used == maximumLength) {
                System.arraycopy(history, 1, history, 0, --used);
            }
        }
        return result;
    }

    public long arrayBytes() { return 12L * starts.length + 8L * characters.length + 4L * rootIndex.length; }
}
