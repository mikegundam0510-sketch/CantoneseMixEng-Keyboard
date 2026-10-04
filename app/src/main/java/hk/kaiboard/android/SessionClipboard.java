package hk.kaiboard.android;

import java.util.ArrayList;
import java.util.List;

/** On-demand, bounded clipboard memory; no disk access or clipboard listener. */
final class SessionClipboard {
    private final List<String> values = new ArrayList<>();
    void add(String text, boolean allowHistory) {
        if (!allowHistory) clear();
        if (text == null || text.trim().isEmpty() || text.length() > 20000) return;
        values.remove(text); values.add(0, text);
        while (values.size() > 10) values.remove(values.size() - 1);
    }
    List<String> items() { return new ArrayList<>(values); }
    void remove(String text) { values.remove(text); }
    void clear() { values.clear(); }
}
