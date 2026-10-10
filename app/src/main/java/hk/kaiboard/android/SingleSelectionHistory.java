package hk.kaiboard.android;

import java.util.*;

/** Transient code-aligned confirmations, never a persisted sentence dictionary. */
final class SingleSelectionHistory {
    private String remaining = "", tail = "", originalContext = "";
    private InputCandidate original;
    private final List<InputCandidate.Segment> parts = new ArrayList<>();

    String contextFor(String input, String editorContext) {
        if (!remaining.isEmpty() && remaining.equals(input)) return tail;
        clear();
        return editorContext;
    }
    String correctionContext(String currentContext) {
        return original==null ? ContextLearning.tail(currentContext) : originalContext;
    }

    InputCandidate[] confirm(String input, InputCandidate selected, String next,
            String context, InputCandidate previous) {
        return confirm(input,selected,next,context,previous,context);
    }
    InputCandidate[] confirm(String input, InputCandidate selected, String next,
            String context, InputCandidate previous,String correctionContext) {
        if (selected.source.isEmpty() || !input.startsWith(selected.source)
                || !next.equals(input.substring(selected.source.length()))
                || selected.segments.stream().anyMatch(s -> s.english || s.translated || !QuickDecoder.hanText(s.text))) {
            clear(); return null;
        }
        if (remaining.isEmpty() && previous != null && previous.source.equals(input) && input.length() <= 48) {
            original = previous;
            originalContext = ContextLearning.tail(correctionContext);
        }
        if (original != null) parts.addAll(selected.segments);
        String combined = context + selected.text;
        int at = combined.length(), count = 0;
        while (at > 0 && count < 8 && OfflineLanguageModel.han(combined.codePointBefore(at))) {
            at -= Character.charCount(combined.codePointBefore(at)); count++;
        }
        tail = combined.substring(at); remaining = next;
        if (!next.isEmpty()) return null;
        InputCandidate[] result = original == null ? null : new InputCandidate[] {
            original, new InputCandidate(original.source, parts, false)
        };
        clear(); return result;
    }

    void clear() { remaining = ""; tail = ""; originalContext=""; original = null; parts.clear(); }
}
