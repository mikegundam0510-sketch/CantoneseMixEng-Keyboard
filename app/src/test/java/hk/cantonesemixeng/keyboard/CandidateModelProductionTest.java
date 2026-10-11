package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.junit.Test;
import static org.junit.Assert.*;

/** Runs the bundled production ranker, rather than the compatibility constructor. */
public class CandidateModelProductionTest {
    @Test public void completionRegressionsRetainTheirFirstChoicesWithBundledRanker() throws Exception {
        Path assets = Path.of("src/main/assets");
        DictionaryEngine dictionary = new DictionaryEngine(Files.newBufferedReader(assets.resolve("cangjie5.base.dict.yaml")),
            Files.newBufferedReader(assets.resolve("english.txt")), Files.newBufferedReader(assets.resolve("character_frequencies.tsv")));
        QuickDecoder decoder = new QuickDecoder(dictionary, Files.newBufferedReader(assets.resolve("quick_phrases.tsv")),
            Files.newBufferedReader(assets.resolve("hk_phrases.tsv")), Files.newBufferedReader(assets.resolve("cantonese_phrases.tsv")),
            OfflineLanguageModel.load(Files.newInputStream(assets.resolve("language_model.b64"))),
            PhraseLanguageModel.load(Files.newInputStream(assets.resolve("phrase_model.b64"))),
            Files.newBufferedReader(assets.resolve("hk_chat_phrases.tsv")),
            CandidateRanker.load(Files.newInputStream(assets.resolve("candidate_ranker.b64"))),
            CandidateRanker.loadWords(Files.newInputStream(assets.resolve("word_ranker.b64"))));
        for (String line : Files.readAllLines(Path.of("../tools/hk_completion_cases.tsv"))) {
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] fields = line.split("\t", -1);
            List<String> choices = decoder.decode(fields[1], (code, word) -> 0, fields[0]);
            assertEquals(fields[2], fields[2], choices.get(0));
            for (String choice : choices) assertFalse(dictionary.matchQuickCodes(fields[1], choice).isEmpty());
        }
    }
}
