package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/** Controlled competing-code fixtures; these checks do not measure language accuracy. */
public class CandidateRankerDecoderTest {
    private static final class Node {
        int id;
        float value;
        final TreeMap<Integer, Node> children = new TreeMap<>();
    }

    private static void visit(Node node, List<Node> nodes) {
        node.id = nodes.size();
        nodes.add(node);
        for (Node child : node.children.values()) visit(child, nodes);
    }

    private static CandidateRanker ranker() throws Exception {
        return ranker(false);
    }
    private static CandidateRanker ranker(boolean words) throws Exception {
        Node root = new Node();
        Map<String, Float> features = words ? Map.of("甲丙甲丙", -1.5f, "乙丙乙丙", 1.5f)
            : Map.of("甲丙", -1.5f, "乙丙", 1.5f);
        for (Map.Entry<String, Float> feature : features.entrySet()) {
            Node node = root;
            int[] text = feature.getKey().codePoints().toArray();
            for (int i = text.length - 1; i >= 0; i--)
                node = node.children.computeIfAbsent(text[i], ignored -> new Node());
            node.value = feature.getValue();
        }
        List<Node> nodes = new ArrayList<>();
        visit(root, nodes);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(new GZIPOutputStream(bytes))) {
            data.writeInt(words ? 0x57524b31 : 0x43524b31);
            data.writeInt(words ? 12 : 3);
            data.writeInt(nodes.size());
            data.writeInt(nodes.size() - 1);
            data.writeFloat(.5f);
            data.writeFloat(1.5f);
            int first = 0;
            for (Node node : nodes) {
                data.writeInt(first);
                data.writeInt(node.children.size());
                data.writeFloat(node.value);
                first += node.children.size();
            }
            for (Node node : nodes) for (Map.Entry<Integer, Node> edge : node.children.entrySet()) {
                data.writeInt(edge.getKey());
                data.writeInt(edge.getValue().id);
            }
        }
        InputStream encoded = new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray()));
        return words ? CandidateRanker.loadWords(encoded) : CandidateRanker.load(encoded);
    }

    private static OfflineLanguageModel neutralLanguageModel() throws Exception {
        // Equal unigram likelihood isolates the ranker and personal preference layers.
        TreeMap<Long, Float> probabilities = new TreeMap<>();
        for (int cp : "甲乙丙".codePoints().toArray())
            probabilities.put(OfflineLanguageModel.hash(new int[]{cp}, 0, 1), .01f);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(new GZIPOutputStream(bytes))) {
            data.writeInt(0x4b4c4d32);
            data.writeInt(5);
            data.writeInt(probabilities.size());
            data.writeFloat(.001f);
            for (Map.Entry<Long, Float> entry : probabilities.entrySet()) {
                data.writeLong(entry.getKey());
                data.writeFloat(entry.getValue());
                data.writeFloat(1);
            }
        }
        return OfflineLanguageModel.load(new ByteArrayInputStream(Base64.getEncoder().encode(bytes.toByteArray())));
    }

    private static DictionaryEngine dictionary() throws Exception {
        StringBuilder entries = new StringBuilder("...\n");
        // DictionaryEngine also enforces minimum dictionary completeness in test fixtures.
        for (int cp = 0x6000; cp < 0x6400; cp++)
            entries.append(new String(Character.toChars(cp))).append("\tzz\n");
        entries.append("甲\tof\n乙\tof\n丙\tvm\n");
        return new DictionaryEngine(new StringReader(entries.toString()), new StringReader(""),
            new StringReader("甲\t100000\n乙\t100000\n丙\t100000\n"));
    }

    private static QuickDecoder decoder(DictionaryEngine dictionary, CandidateRanker ranker) throws Exception {
        return new QuickDecoder(dictionary, new StringReader(""), null, null,
            neutralLanguageModel(), null, null, ranker);
    }

    @Test public void absentRankerPreservesTheSevenArgumentDecoder() throws Exception {
        DictionaryEngine dictionary = dictionary();
        QuickDecoder old = new QuickDecoder(dictionary, new StringReader(""), null, null,
            neutralLanguageModel(), null, null);
        QuickDecoder optional = decoder(dictionary, null);
        for (String code : Arrays.asList("ofvm", "ofvmofvm", "vmofvm", "of1"))
            for (String context : Arrays.asList("", "乙", "甲，"))
                assertEquals(code + " / " + context, old.decode(code, (c, w) -> 0, context),
                    optional.decode(code, (c, w) -> 0, context));
    }

    @Test public void signedCompetingRelationsAffectExactSentenceRanking() throws Exception {
        DictionaryEngine dictionary = dictionary();
        QuickDecoder unranked = decoder(dictionary, null), ranked = decoder(dictionary, ranker());
        assertEquals("甲丙", unranked.decode("ofvm", (c, w) -> 0).get(0));
        assertEquals("乙丙", ranked.decode("ofvm", (c, w) -> 0).get(0));
        assertEquals(-.75, ranked.languageScore("甲", "丙") - unranked.languageScore("甲", "丙"), 1e-9);
        assertEquals(.75, ranked.languageScore("乙", "丙") - unranked.languageScore("乙", "丙"), 1e-9);
        assertEquals(0, ranked.languageScore("甲，", "丙") - unranked.languageScore("甲，", "丙"), 1e-9);
        for (String code : Arrays.asList("ofvm", "ofvmofvm", "vmofvm")) {
            List<String> choices = ranked.decode(code, (c, w) -> 0);
            assertTrue(choices.size() <= 20);
            assertEquals(choices.size(), new HashSet<>(choices).size());
            for (String choice : choices) assertFalse(dictionary.matchQuickCodes(code, choice).isEmpty());
        }
    }

    @Test public void explicitLocalChoicesCanOverridePublicNegativeEvidence() throws Exception {
        QuickDecoder ranked = decoder(dictionary(), ranker());
        assertEquals("乙丙", ranked.decode("ofvm", (c, w) -> 0).get(0));
        assertEquals("甲丙", ranked.decode("ofvm", (c, w) -> w.equals("甲") ? 100 : 0).get(0));
        Map<String, Integer> weights = Map.of("S:of:我:甲", 20, "S:of:我:乙", -20);
        ContextLearning.Preferences personal = new ContextLearning.Preferences(weights.keySet(),
            key -> weights.getOrDefault(key, 0));
        assertEquals("甲丙", ranked.decode("ofvm", (c, w) -> 0, "我", personal).get(0));
        // Supplying no preference leaves the immutable public model unchanged.
        assertEquals("乙丙", ranked.decode("ofvm", (c, w) -> 0, "我", null).get(0));
        assertTrue(ranked.decode("of1", (c, w) -> 100, "我", personal).isEmpty());
    }

    @Test public void longerWordEvidenceIsAppliedDuringDecodingAndPersonalChoicesStillWin() throws Exception {
        DictionaryEngine dictionary = dictionary();
        QuickDecoder old = decoder(dictionary, null);
        QuickDecoder ranked = new QuickDecoder(dictionary, new StringReader(""), null, null,
            neutralLanguageModel(), null, null, null, ranker(true));
        assertEquals("甲丙甲丙", old.decode("ofvmofvm", (c, w) -> 0).get(0));
        assertEquals("乙丙乙丙", ranked.decode("ofvmofvm", (c, w) -> 0).get(0));
        assertEquals(.75, ranked.languageScore("乙丙乙", "丙") - old.languageScore("乙丙乙", "丙"), 1e-9);
        assertEquals("甲丙甲丙", ranked.decode("ofvmofvm", (c, w) -> w.equals("甲") ? 100 : 0).get(0));
        for (String choice : ranked.decode("ofvmofvm", (c, w) -> 0))
            assertFalse(dictionary.matchQuickCodes("ofvmofvm", choice).isEmpty());
    }
}
