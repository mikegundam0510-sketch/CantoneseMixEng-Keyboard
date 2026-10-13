package hk.cantonesemixeng.keyboard;

import java.nio.file.*;
import java.io.*;
import java.util.*;

/** Check serialized runtime scores against the frozen offline candidate lists. */
public final class SentenceRankingEvaluation {
    public static void main(String[] args) throws Exception {
        SentenceRanker model = SentenceRanker.load(Files.newInputStream(Path.of(args[0])));
        try (BufferedWriter out = Files.newBufferedWriter(Path.of(args[2]))) {
            for (String line : Files.readAllLines(Path.of(args[1]))) {
                String[] f = line.split("\t", -1);
                List<String> values = f[5].isEmpty() ? new ArrayList<>() : new ArrayList<>(Arrays.asList(f[5].split("\\|")));
                String[] numbers = f[6].isEmpty() ? new String[0] : f[6].split("\\|");
                if (values.size() != numbers.length) throw new IllegalArgumentException(line);
                Map<String, Double> scores = new HashMap<>();
                for (int i = 0; i < values.size(); i++) scores.put(values.get(i), Double.valueOf(numbers[i]) + model.score(f[1], values.get(i)));
                if (f.length != 8) throw new IllegalArgumentException("Structural annotation required");
                String[] support = f[7].isEmpty() ? new String[0] : f[7].split("\\|");
                if (support.length != values.size()) throw new IllegalArgumentException("Structural annotation incomplete");
                String original = !values.isEmpty() && Double.valueOf(support[0]) > 0 ? values.remove(0) : null;
                values.sort(Comparator.comparingDouble((String text) -> scores.get(text)).reversed());
                if (original != null) values.add(0, original);
                if(values.size()>20) values=new ArrayList<>(values.subList(0,20));
                int rank = values.indexOf(f[3]) + 1;
                out.write(String.join("\t", f[0], f[1], f[2], f[3], Integer.toString(rank), String.join("|", values)) + "\n");
            }
        }
    }
}
