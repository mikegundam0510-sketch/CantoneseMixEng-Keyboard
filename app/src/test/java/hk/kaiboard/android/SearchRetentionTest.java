package hk.kaiboard.android;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import java.nio.file.*;
import org.junit.Test;
import static org.junit.Assert.*;

/** Controlled ambiguity: the wanted prefix ranks beyond 48 until later codes arrive. */
public class SearchRetentionTest {
    private static String character(int cp) { return new String(Character.toChars(cp)); }

    @Test public void frequencyCutoffDoesNotHideAContextuallySupportedCantoneseCharacter() throws Exception {
        Path assets = Path.of("src/main/assets");
        DictionaryEngine dictionary = new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
            Files.newBufferedReader(assets.resolve("english.txt")), Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
        QuickDecoder decoder = new QuickDecoder(dictionary, Files.newBufferedReader(assets.resolve("quick_phrases.tsv")),
            Files.newBufferedReader(assets.resolve("hk_phrases.tsv")), Files.newBufferedReader(assets.resolve("cantonese_phrases.tsv")),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))));
        assertTrue(dictionary.quickCandidates("rr").indexOf("嗰") >= 24);
        List<String> result = decoder.decode("hmerrrysmlrp", (code, word) -> 0, "下你女性");
        int rank = result.indexOf("生活嗰方面呢");
        assertTrue("Corpus regression: frequency cutoff previously hid this sentence", rank >= 0 && rank < 5);
        for (String candidate : result) assertFalse(dictionary.matchQuickCodes("hmerrrysmlrp", candidate).isEmpty());
    }

    private static OfflineLanguageModel model() throws Exception {
        TreeMap<Long, float[]> grams = new TreeMap<>();
        for (int group = 0; group < 3; group++) for (int i = 0; i < 24; i++) {
            int cp = 0x4e00 + group * 48 + i;
            float probability = .01f;
            if (group == 0 && i == 0) probability = .010001f;
            if (group == 1 && i >= 2) probability = i == 2 ? .0099f : .009f;
            float backoff = group == 1 && i == 2 ? .1f : 1f;
            grams.put(OfflineLanguageModel.hash(new int[]{cp}, 0, 1), new float[]{probability, backoff});
        }
        int[] pair = {0x4e00 + 48 + 2, 0x4e00 + 96 + 2};
        grams.put(OfflineLanguageModel.hash(pair, 0, 2), new float[]{.8f, 1f});
        pair = new int[]{0x4e00 + 96 + 2, 0x4e00 + 96 + 3};
        grams.put(OfflineLanguageModel.hash(pair, 0, 2), new float[]{.5f, 1f});
        ByteArrayOutputStream compressed = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(new GZIPOutputStream(compressed))) {
            out.writeInt(0x4B4C4D32); out.writeInt(5); out.writeInt(grams.size()); out.writeFloat(.000001f);
            for (Map.Entry<Long, float[]> entry : grams.entrySet()) {
                out.writeLong(entry.getKey()); out.writeFloat(entry.getValue()[0]); out.writeFloat(entry.getValue()[1]);
            }
        }
        return OfflineLanguageModel.load(new ByteArrayInputStream(Base64.getEncoder().encode(compressed.toByteArray())));
    }

    @Test public void secondFollowingWordRescuesAnInitiallyLowerRankedPrefix() throws Exception {
        StringBuilder roots = new StringBuilder("...\n"), counts = new StringBuilder();
        for (int group = 0; group < 3; group++) for (int i = 0; i < 24; i++) {
            String text = character(0x4e00 + group * 48 + i);
            roots.append(text).append('\t').append(new String[]{"aa", "bb", "cc"}[group]).append('\n');
            counts.append(text).append('\t').append(i == 0 ? 1001 : 1000).append('\n');
        }
        for (int cp = 0x6000; cp < 0x6400; cp++) roots.append(character(cp)).append("\tzz\n");
        DictionaryEngine dictionary = new DictionaryEngine(new StringReader(roots.toString()),
            new StringReader(""), new StringReader(counts.toString()));
        String first = character(0x4e00 + 96) + character(0x4e00 + 97);
        String second = character(0x4e00 + 98) + character(0x4e00 + 99);
        String prefix = character(0x4e00) + character(0x4e00 + 50);
        QuickDecoder decoder = new QuickDecoder(dictionary,
            new StringReader("cccc\t" + first + "\t1000\ncccc\t" + second + "\t900\n"), null, null, model());
        String wanted = prefix + second;
        // 24x24 possible prefixes; all 48 combinations ending in the first two
        // bb characters have a higher score than this prefix before cc arrives.
        int higher = 0;
        for (int left = 0; left < 24; left++) for (int right = 0; right < 24; right++)
            if (decoder.languageScore("", character(0x4e00 + left) + character(0x4e00 + 48 + right))
                    > decoder.languageScore("", prefix)) higher++;
        assertTrue(higher >= 48);
        List<String> result = decoder.decode("aabbcccc", (code, word) -> 0);
        assertTrue("Later codes must rescue the prefix into the candidate list", result.contains(wanted));
        assertEquals(wanted, result.get(0));
        assertFalse(decoder.knownWord(wanted));
        assertEquals(result.size(), new HashSet<>(result).size());
        for (String candidate : result) assertFalse(dictionary.matchQuickCodes("aabbcccc", candidate).isEmpty());
        assertTrue(result.size() <= 20);
    }
}
