package hk.kaiboard.android;

/** One-step reselection only when the editor still has the exact last committed suffix and cursor. */
public final class ReselectionRecord {
    public final InputCandidate candidate;
    public final int cursor;
    private final String before;
    public ReselectionRecord(InputCandidate candidate, int cursor, String before) {
        this.candidate = candidate; this.cursor = cursor; this.before = before;
    }
    public boolean valid(int start, int end, CharSequence currentBefore) {
        return cursor >= candidate.text.length() && start == cursor && end == cursor && currentBefore != null
            && before.equals(currentBefore.toString()) && before.endsWith(candidate.text);
    }
}
