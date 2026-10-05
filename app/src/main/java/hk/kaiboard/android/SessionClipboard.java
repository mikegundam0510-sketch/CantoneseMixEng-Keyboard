package hk.kaiboard.android;

import java.util.ArrayList;
import java.util.List;
import java.util.function.LongSupplier;

/** On-demand, bounded clipboard memory; no disk access or clipboard listener. */
final class SessionClipboard {
    private static final class Entry {
        final String text;
        final long captured;
        Entry(String text, long captured) { this.text = text; this.captured = captured; }
    }
    private final List<Entry> values = new ArrayList<>();
    private final LongSupplier clock;
    private long maxAgeMillis;
    SessionClipboard() { this(() -> System.nanoTime() / 1_000_000L); }
    SessionClipboard(LongSupplier clock) { this.clock = clock; }
    void setMaxAgeMillis(long age) { maxAgeMillis = Math.max(0, age); prune(); }
    private void prune() {
        if (maxAgeMillis == 0) return;
        long now = clock.getAsLong();
        values.removeIf(entry -> now - entry.captured >= maxAgeMillis);
    }
    void add(String text, boolean allowHistory) {
        prune();
        if (!allowHistory) clear();
        if (text == null || text.trim().isEmpty() || text.length() > 20000) return;
        Entry existing = null;
        for (Entry entry : values) if (entry.text.equals(text)) { existing = entry; break; }
        if (existing != null) values.remove(existing);
        values.add(0, existing == null ? new Entry(text, clock.getAsLong()) : existing);
        while (values.size() > 10) values.remove(values.size() - 1);
    }
    List<String> items() {
        prune();
        List<String> result = new ArrayList<>();
        for (Entry entry : values) result.add(entry.text);
        return result;
    }
    long nextExpiryMillis() {
        prune();
        if (maxAgeMillis == 0 || values.isEmpty()) return -1;
        long now = clock.getAsLong(), delay = Long.MAX_VALUE;
        for (Entry entry : values) delay = Math.min(delay, maxAgeMillis - (now - entry.captured));
        return Math.max(1, delay);
    }
    void remove(String text) { values.removeIf(entry -> entry.text.equals(text)); }
    void clear() { values.clear(); }
}
