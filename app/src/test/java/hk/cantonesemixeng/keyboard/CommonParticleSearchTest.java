package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/** Common particles share the contextual reserve; historical forms keep the usual cutoff. */
public class CommonParticleSearchTest {
    private static String character(int cp) { return new String(Character.toChars(cp)); }

    private static DictionaryEngine dictionary() throws Exception {
        StringBuilder roots = new StringBuilder("...\n甲\taa\n乙\tcc\n");
        StringBuilder counts = new StringBuilder("甲\t1000\n乙\t1000\n㗎\t1\n㤀\t1\n");
        for (int i = 0; i < 80; i++) {
            String filler = character(0x6000 + i);
            roots.append(filler).append("\tbb\n");
            counts.append(filler).append('\t').append(100000 - i).append('\n');
        }
        roots.append("㗎\tbb\n㤀\tbb\n");
        for (int cp = 0x7000; cp < 0x7400; cp++) roots.append(character(cp)).append("\tzz\n");
        return new DictionaryEngine(new StringReader(roots.toString()), new StringReader(""),
            new StringReader(counts.toString()));
    }

    private static OfflineLanguageModel model(boolean contextualEvidence) throws Exception {
        TreeMap<Long, float[]> grams = new TreeMap<>();
        for (int cp : "甲乙".codePoints().toArray())
            grams.put(OfflineLanguageModel.hash(new int[]{cp}, 0, 1), new float[]{.01f, 1});
        for (int i = 0; i < 80; i++)
            grams.put(OfflineLanguageModel.hash(new int[]{0x6000 + i}, 0, 1), new float[]{.01f, 1});
        for (int cp : "㗎㤀".codePoints().toArray())
            grams.put(OfflineLanguageModel.hash(new int[]{cp}, 0, 1), new float[]{.0001f, 1});
        if (contextualEvidence) {
            grams.put(OfflineLanguageModel.hash(new int[]{'甲', '㗎'}, 0, 2), new float[]{.8f, 1});
            // Even stronger likelihood must not expand the reserve to every rare form.
            grams.put(OfflineLanguageModel.hash(new int[]{'甲', '㤀'}, 0, 2), new float[]{.95f, 1});
        }
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(new GZIPOutputStream(bytes))) {
            data.writeInt(0x4b4c4d32);
            data.writeInt(5);
            data.writeInt(grams.size());
            data.writeFloat(.000001f);
            for (Map.Entry<Long, float[]> entry : grams.entrySet()) {
                data.writeLong(entry.getKey());
                data.writeFloat(entry.getValue()[0]);
                data.writeFloat(entry.getValue()[1]);
            }
        }
        return OfflineLanguageModel.load(new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray())));
    }

    @Test public void supportedCommonParticleBelowSixtyFourCanEnterBoundedExactSearch() throws Exception {
        DictionaryEngine dictionary = dictionary();
        assertTrue(dictionary.quickCandidates("bb").indexOf("㗎") >= 64);
        assertTrue(dictionary.quickCandidates("bb").indexOf("㤀") >= 64);
        QuickDecoder decoder = new QuickDecoder(dictionary, new StringReader(""), null, null, model(true));
        assertTrue(decoder.languageScore("甲", "㤀") > decoder.languageScore("甲", "㗎"));
        List<String> choices = decoder.decode("aabbcc", (code, word) -> 0);
        assertEquals("甲㗎乙", choices.get(0));
        assertFalse(decoder.knownWord("甲㗎乙"));
        assertFalse(choices.stream().anyMatch(choice -> choice.contains("㤀")));
        assertTrue(choices.size() <= 20);
        assertEquals(choices.size(), new HashSet<>(choices).size());
        for (String choice : choices) assertFalse(dictionary.matchQuickCodes("aabbcc", choice).isEmpty());
    }

    @Test public void commonParticleStillNeedsLanguageEvidenceAndRareFormsRemainInSingleLookup() throws Exception {
        DictionaryEngine dictionary = dictionary();
        QuickDecoder decoder = new QuickDecoder(dictionary, new StringReader(""), null, null, model(false));
        List<String> choices = decoder.decode("aabbcc", (code, word) -> 0);
        assertFalse(choices.isEmpty());
        assertFalse(choices.stream().anyMatch(choice -> choice.contains("㗎") || choice.contains("㤀")));
        assertTrue(dictionary.quickCandidates("bb").contains("㗎"));
        assertTrue(dictionary.quickCandidates("bb").contains("㤀"));
        for (String choice : choices) assertFalse(dictionary.matchQuickCodes("aabbcc", choice).isEmpty());
    }
}
