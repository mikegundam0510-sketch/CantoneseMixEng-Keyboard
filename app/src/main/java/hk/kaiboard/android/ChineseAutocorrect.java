package hk.kaiboard.android;

import java.util.*;
import java.util.function.ToDoubleFunction;

/** Bounded, offline repairs. Only a clearly better full-code Chinese choice is automatic. */
public final class ChineseAutocorrect {
    public static InputCandidate choose(String source, String context,
            Collection<InputCandidate> exact, Collection<InputCandidate> repairs,
            ToDoubleFunction<String> score) {
        if (!source.matches("[A-Za-z]{2,16}")) return null;
        double baseline = Double.NEGATIVE_INFINITY, best = Double.NEGATIVE_INFINITY;
        double runnerUp = Double.NEGATIVE_INFINITY;
        InputCandidate winner = null;
        Set<String> seen = new HashSet<>();
        for (InputCandidate c : exact) {
            if (!c.corrected && c.source.equals(source) && !c.englishOnly()) {
                double value = score.applyAsDouble(c.text);
                if (!Double.isFinite(value)) return null;
                baseline = Math.max(baseline, value);
                seen.add(c.text);
            }
        }
        if (source.length() == 2 && !seen.isEmpty()) return null;
        for (InputCandidate c : repairs) {
            if (!c.corrected || !c.source.equals(source) || c.englishOnly() || !seen.add(c.text)) continue;
            double value = score.applyAsDouble(c.text);
            if (!Double.isFinite(value)) continue;
            if (value > best) { runnerUp = best; best = value; winner = c; }
            else runnerUp = Math.max(runnerUp, value);
        }
        // Short ambiguous codes need actual Chinese context; never guess a single radical.
        if (winner == null || context.isEmpty() || best < baseline + Math.log(8)
                || best < runnerUp + Math.log(2)) return null;
        return winner;
    }

    public static List<InputCandidate> cangjieRepairs(DictionaryEngine dictionary, String source) {
        if (!source.matches("[A-Za-z]{2,5}")) return Collections.emptyList();
        String code = source.toLowerCase(Locale.ROOT);
        List<InputCandidate> result = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        Set<String> variants = new LinkedHashSet<>();
        for (int i = 0; i < code.length(); i++) {
            for (char adjacent : QuickTypos.neighbors(code.charAt(i)).toCharArray())
                variants.add(code.substring(0,i) + adjacent + code.substring(i+1));
            if (i + 1 < code.length()) {
                variants.add(code.substring(0,i) + code.charAt(i+1) + code.charAt(i) + code.substring(i+2));
                // Repeated key taps can add a duplicate radical.
                if (code.charAt(i) == code.charAt(i+1)) variants.add(code.substring(0,i) + code.substring(i+1));
            }
        }
        // One omitted radical. Full dictionary matches only; no prefix completions.
        if (code.length() < 5) for (int i = 0; i <= code.length(); i++)
            for (char radical = 'a'; radical <= 'z'; radical++)
                variants.add(code.substring(0,i) + radical + code.substring(i));
        variants.remove(code);
        for (String fixed : variants) {
            for (String text : dictionary.lookup(fixed, false, true, false)) {
                if (!QuickDecoder.hanText(text) || !seen.add(text)) continue;
                result.add(new InputCandidate(source, Collections.singletonList(
                    new InputCandidate.Segment(fixed, text, false)), true));
            }
        }
        return result;
    }
}
