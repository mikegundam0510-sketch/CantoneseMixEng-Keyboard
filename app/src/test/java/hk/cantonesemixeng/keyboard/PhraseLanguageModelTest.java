package hk.cantonesemixeng.keyboard;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import java.nio.file.*;

public class PhraseLanguageModelTest {
    private static final class Node {
        int id; float value;
        final TreeMap<Integer, Node> children = new TreeMap<>();
    }
    private static void visit(Node node, List<Node> nodes) {
        node.id = nodes.size(); nodes.add(node);
        for (Node child : node.children.values()) visit(child, nodes);
    }
    private static byte[] fixture(boolean invalidEdge, float strength) throws Exception {
        Node root = new Node();
        for (String phrase : Arrays.asList("覆返個訊息", "轉錢畀我", "幾點放工", "𠮩𠹌香港")) {
            Node node = root;
            int[] text = phrase.codePoints().toArray();
            for (int i = text.length - 1; i >= 0; i--)
                node = node.children.computeIfAbsent(text[i], cp -> new Node());
            node.value = 2;
        }
        List<Node> nodes = new ArrayList<>(); visit(root, nodes);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(new GZIPOutputStream(bytes))) {
            data.writeInt(0x574c4d31); data.writeInt(12);
            data.writeInt(nodes.size()); data.writeInt(nodes.size() - 1); data.writeFloat(strength);
            int first = 0;
            for (Node node : nodes) {
                data.writeInt(first); data.writeInt(node.children.size()); data.writeFloat(node.value);
                first += node.children.size();
            }
            for (Node node : nodes) for (Map.Entry<Integer, Node> edge : node.children.entrySet()) {
                data.writeInt(edge.getKey());
                data.writeInt(invalidEdge ? 0 : edge.getValue().id);
            }
        }
        return Base64.getEncoder().encode(bytes.toByteArray());
    }
    private static PhraseLanguageModel small() throws Exception {
        return PhraseLanguageModel.load(new ByteArrayInputStream(fixture(false, .5f)));
    }
    @Test public void wordRelationsPreferAttestedCombinationsAndUnknownIsNeutral() throws Exception {
        PhraseLanguageModel model = small();
        assertEquals(1, model.score("覆返", "個訊息"), 1e-9);
        assertEquals(1, model.score("", "轉錢畀我"), 1e-9);
        assertEquals(0, model.score("覆返", "個辛德"), 1e-9);
        assertEquals(0, model.score("", "字庫冇呢個詞"), 1e-9);
    }
    @Test public void everyDecoderTokenSplitChargesTheSameEvidence() throws Exception {
        PhraseLanguageModel model = small();
        String text = "我今日問你幾點放工再覆返個訊息";
        for (int split = 0; split <= text.length(); split++) {
            String left = text.substring(0, split), right = text.substring(split);
            assertEquals(model.score("香港", text), model.score("香港", left) + model.score("香港" + left, right), 1e-9);
        }
    }
    @Test public void punctuationAndEnglishResetRelationHistory() throws Exception {
        PhraseLanguageModel model = small();
        assertEquals(0, model.score("覆返，", "個訊息"), 1e-9);
        assertEquals(0, model.score("覆返", "abc個訊息"), 1e-9);
        assertEquals(model.score("", "幾點放工"), model.score("覆返", "，幾點放工"), 1e-9);
    }
    @Test public void supplementaryHanCountsAsOneCharacter() throws Exception {
        PhraseLanguageModel model = small();
        assertEquals(1, model.score("𠮩", "𠹌香港"), 1e-9);
        assertEquals(model.score("", "𠮩𠹌香港"), model.score("", "𠮩𠹌") + model.score("𠮩𠹌", "香港"), 1e-9);
    }
    @Test public void rejectsMalformedModelsAndUnsafeTreeEdges() throws Exception {
        for (byte[] encoded : Arrays.asList("broken".getBytes(), fixture(true, .5f), fixture(false, Float.NaN))) {
            try { PhraseLanguageModel.load(new ByteArrayInputStream(encoded)); fail("Malformed model accepted"); }
            catch (IOException expected) { }
        }
    }
    @Test public void productionModelHasBoundedMemoryAndNoWholeChatStorage() throws Exception {
        PhraseLanguageModel model = PhraseLanguageModel.load(new FileInputStream("src/main/assets/phrase_model.b64"));
        assertTrue(model.arrayBytes() < 1024 * 1024);
        assertTrue(model.score("", "覆返個訊息") > 0);
        for (String value : Arrays.asList("香港", "你好𠮩𠹌", "abc，", ""))
            assertTrue(Double.isFinite(model.score("我今日", value)));
    }
    private static Reader asset(String name) throws IOException {
        return Files.newBufferedReader(Path.of("src/main/assets", name));
    }
    @Test public void productionDecoderUsesRelationsAndKeepsExactCodeCandidates() throws Exception {
        DictionaryEngine dictionary = new DictionaryEngine(asset("cangjie5.base.dict.yaml"), asset("english.txt"), asset("character_frequencies.tsv"));
        QuickDecoder decoder = new QuickDecoder(dictionary, asset("quick_phrases.tsv"), asset("hk_phrases.tsv"), asset("cantonese_phrases.tsv"),
            OfflineLanguageModel.load(new FileInputStream("src/main/assets/language_model.b64")),
            PhraseLanguageModel.load(new FileInputStream("src/main/assets/phrase_model.b64")), asset("hk_chat_phrases.tsv"));
        for (String text : Arrays.asList("你覆咗個訊息未", "你訂咗餐廳未", "你收到件貨未", "你幾時返到屋企")) {
            StringBuilder code = new StringBuilder();
            for (int cp : text.codePoints().toArray()) {
                List<String> codes = new ArrayList<>(dictionary.quickCodesFor(new String(Character.toChars(cp))));
                codes.sort(Comparator.comparingInt(String::length).reversed().thenComparing(Comparator.naturalOrder()));
                code.append(codes.get(0));
            }
            List<String> candidates = decoder.decode(code.toString(), (c, w) -> 0);
            assertEquals(text, candidates.get(0));
            assertTrue(candidates.size() <= 20);
            assertEquals(candidates.size(), new HashSet<>(candidates).size());
            for (String candidate : candidates) assertFalse(dictionary.matchQuickCodes(code.toString(), candidate).isEmpty());
        }
    }
}
