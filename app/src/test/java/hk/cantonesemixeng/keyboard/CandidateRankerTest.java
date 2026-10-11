package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

public class CandidateRankerTest {
    private static final class Node {
        int id; float value;
        final TreeMap<Integer, Node> children = new TreeMap<>();
    }
    private static void visit(Node node, List<Node> nodes) {
        node.id = nodes.size(); nodes.add(node);
        for (Node child : node.children.values()) visit(child, nodes);
    }
    private static byte[] fixture(float strength, float endpointLimit, boolean invalidEdge, boolean invalidValue) throws Exception {
        Node root = new Node();
        Map<String, Float> features = new TreeMap<>();
        features.put("訊息", .75f); features.put("辛德", -.75f);
        features.put("個訊", .5f); features.put("個辛", -.5f);
        features.put("個訊息", .5f); features.put("個辛德", -.5f);
        features.put("𠮩𠹌", .25f); features.put("𠹌香", -.25f);
        for (Map.Entry<String, Float> entry : features.entrySet()) {
            Node node = root;
            int[] text = entry.getKey().codePoints().toArray();
            for (int i = text.length - 1; i >= 0; i--)
                node = node.children.computeIfAbsent(text[i], cp -> new Node());
            node.value = invalidValue ? Float.NaN : entry.getValue();
        }
        List<Node> nodes = new ArrayList<>(); visit(root, nodes);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(new GZIPOutputStream(bytes))) {
            data.writeInt(0x43524b31); data.writeInt(3);
            data.writeInt(nodes.size()); data.writeInt(nodes.size() - 1);
            data.writeFloat(strength); data.writeFloat(endpointLimit);
            int first = 0;
            for (Node node : nodes) {
                data.writeInt(first); data.writeInt(node.children.size()); data.writeFloat(node.value);
                first += node.children.size();
            }
            for (Node node : nodes) for (Map.Entry<Integer, Node> edge : node.children.entrySet()) {
                data.writeInt(edge.getKey()); data.writeInt(invalidEdge ? 0 : edge.getValue().id);
            }
        }
        return Base64.getEncoder().encode(bytes.toByteArray());
    }
    private static CandidateRanker small() throws Exception {
        return CandidateRanker.load(new ByteArrayInputStream(fixture(1, 1.5f, false, false)));
    }
    @Test public void signedEvidenceRewardsNaturalAndPenalizesCompetingRelations() throws Exception {
        CandidateRanker model = small();
        assertEquals(1.75, model.score("覆個", "訊息"), 1e-9);
        assertEquals(-1.75, model.score("覆個", "辛德"), 1e-9);
        assertTrue(model.score("", "你覆個訊息未") > model.score("", "你覆個辛德未"));
        assertEquals(0, model.score("香港", "字庫冇呢個詞"), 1e-9);
    }
    @Test public void shortRelationsAreIndependentOfDecoderTokenization() throws Exception {
        CandidateRanker model = small();
        String text = "你覆個訊息再覆個辛德未";
        for (int split = 0; split <= text.length(); split++) {
            String left = text.substring(0, split), right = text.substring(split);
            assertEquals(model.score("我問", text), model.score("我問", left) + model.score("我問" + left, right), 1e-9);
        }
    }
    @Test public void punctuationAndLatinResetHistoryAndSupplementaryHanIsOneCharacter() throws Exception {
        CandidateRanker model = small();
        assertEquals(.75, model.score("個，", "訊息"), 1e-9);
        assertEquals(.75, model.score("個", "abc訊息"), 1e-9);
        assertEquals(0, model.score("", "𠮩𠹌香港"), 1e-9);
        assertEquals(.25, model.score("𠮩", "𠹌"), 1e-9);
        assertEquals(-.25, model.score("𠮩𠹌", "香港"), 1e-9);
    }
    @Test public void endpointCapAndDisabledStrengthBoundPublicWeights() throws Exception {
        CandidateRanker model = CandidateRanker.load(new ByteArrayInputStream(fixture(2, .5f, false, false)));
        assertEquals(2, model.score("個", "訊息"), 1e-9);
        assertEquals(-2, model.score("個", "辛德"), 1e-9);
        CandidateRanker disabled = CandidateRanker.load(new ByteArrayInputStream(fixture(0, 1.5f, false, false)));
        assertEquals(0, disabled.score("個", "訊息"), 1e-9);
        assertTrue(model.arrayBytes() < 1024 * 1024);
    }
    @Test public void rejectsUnsafeEdgesWeightsAndHeaders() throws Exception {
        for (byte[] encoded : Arrays.asList("broken".getBytes(), fixture(1, 1.5f, true, false),
                fixture(1, 1.5f, false, true), fixture(Float.NaN, 1.5f, false, false),
                fixture(1, 2, false, false))) {
            try { CandidateRanker.load(new ByteArrayInputStream(encoded)); fail("Malformed ranker accepted"); }
            catch (IOException expected) { }
        }
    }
}
