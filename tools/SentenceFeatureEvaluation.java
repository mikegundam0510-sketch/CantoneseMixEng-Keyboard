package hk.cantonesemixeng.keyboard;
import java.nio.file.*;
import java.io.*;
import java.util.*;
public final class SentenceFeatureEvaluation {
    public static void main(String[] args) throws Exception {
        try (BufferedWriter out = Files.newBufferedWriter(Path.of(args[1]))) {
            for (String line : Files.readAllLines(Path.of(args[0]))) {
                String[] f = line.split("\t", -1);
                Map<String, Integer> features = SentenceRanker.features(f[0], f[1]);
                List<String> values = new ArrayList<>();
                for (Map.Entry<String, Integer> e : features.entrySet()) values.add(e.getKey() + "=" + e.getValue());
                out.write(String.join("\t", values) + "\n");
            }
        }
    }
}
