package hk.kaiboard.android;

/** A decaying recent layer added to existing lifetime counts; no editor text is stored. */
final class RecentLearning {
    private static final double HALF_LIFE_MS = 7 * 24 * 60 * 60 * 1000.0;
    private static final double MAX_RECENT = 32;
    private RecentLearning() {}

    static double recent(String value, long now) {
        if (value == null) return 0;
        try {
            String[] fields = value.split(":", -1);
            if (fields.length != 2) return 0;
            long saved = Long.parseLong(fields[0]);
            double count = Double.parseDouble(fields[1]);
            if (saved < 0 || !Double.isFinite(count) || count < 0) return 0;
            // Clock rollback must neither amplify history nor erase lifetime counts.
            double age = Math.max(0, (double) now - saved);
            return Math.min(MAX_RECENT, count) * Math.pow(.5, age / HALF_LIFE_MS);
        } catch (NumberFormatException ignored) { return 0; }
    }

    static int weight(int lifetimeCount, String value, long now) {
        if (lifetimeCount <= 0) return 0;
        return Math.min(100000, lifetimeCount) + (int) Math.round(3 * recent(value, now));
    }

    static String update(String value, long now, int delta) {
        double count = Math.max(0, Math.min(MAX_RECENT, recent(value, now) + delta));
        return count == 0 ? null : Math.max(0, now) + ":" + count;
    }

    static int weight(Object lifetime, Object recent, long now) {
        return weight(lifetime instanceof Integer ? (Integer) lifetime : 0,
            recent instanceof String ? (String) recent : null, now);
    }
}
