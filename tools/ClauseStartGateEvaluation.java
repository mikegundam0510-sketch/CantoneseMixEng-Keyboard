package hk.cantonesemixeng.keyboard;

import java.nio.file.*;
import java.util.*;

/** Check cache gating against every Han continuation of actual ranked outputs. */
public final class ClauseStartGateEvaluation {
    public static void main(String[] args) throws Exception {
        Set<String> texts = new HashSet<>();
        for (String arg : args) for (String line : Files.readAllLines(Path.of(arg))) {
            String[] fields = line.split("\t", -1);
            texts.add(fields[0] + fields[2]);
            if (fields.length > 4) for (String candidate : fields[4].split("\\|"))
                texts.add(fields[0] + candidate);
        }
        int checks = 0;
        for (String text : texts) {
            if (!QuickDecoder.hanText(text)) continue;
            int end = Math.min(12, text.codePointCount(0, text.length()));
            for (int cp = 0; cp <= end; cp++) {
                int at = text.offsetByCodePoints(0, cp);
                String prefix = text.substring(0, at), next = text.substring(at);
                if (ClauseStartRelations.score(prefix, next) > 0 && !ClauseStartRelations.pending(prefix))
                    throw new AssertionError("Cache gate dropped cue: " + prefix + " / " + next);
                checks++;
            }
        }
        System.out.println("texts=" + texts.size() + " continuation_checks=" + checks);
    }
}
