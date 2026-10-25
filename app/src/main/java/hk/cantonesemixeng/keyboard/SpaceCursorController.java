package hk.cantonesemixeng.keyboard;

import android.icu.text.BreakIterator;
import android.os.Build;
import android.view.inputmethod.ExtractedText;
import android.view.inputmethod.ExtractedTextRequest;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.SurroundingText;

/** Space drags change selection inside the editor, never dispatch navigation keys. */
final class SpaceCursorController {
    interface Boundary { int adjacent(int position, int direction); }
    interface Boundaries { Boundary forText(CharSequence text); }
    private final Boundaries boundaries;

    SpaceCursorController() {
        this(text -> {
            BreakIterator iterator = BreakIterator.getCharacterInstance();
            iterator.setText(text.toString());
            return (position, direction) -> direction < 0
                ? iterator.preceding(position) : iterator.following(position);
        });
    }

    SpaceCursorController(Boundaries boundaries) { this.boundaries = boundaries; }

    boolean move(InputConnection connection, int steps) {
        if (connection == null || steps == 0) return false;
        Snapshot value = read(connection);
        if (value == null) return false;
        int direction = Integer.signum(steps), focus = value.end;
        int count = (int)Math.min(20L, Math.abs((long)steps));
        Boundary characters = null;
        for (int i = 0; i < count; i++) {
            if (i == 0 && value.start != value.end) {
                focus = direction < 0 ? Math.min(value.start, value.end) : Math.max(value.start, value.end);
                continue;
            }
            if (direction < 0 && focus == 0 || direction > 0 && focus == value.text.length()) break;
            if (characters == null) characters = boundaries.forText(value.text);
            int next = characters.adjacent(focus, direction);
            if (next < 0 || next > value.text.length() || direction < 0 && next >= focus
                    || direction > 0 && next <= focus) break;
            focus = next;
        }
        if (value.start == value.end && focus == value.end) return false;
        int absolute = value.offset + focus;
        // Unsupported/rejected selection is a no-op. DPAD fallback can move
        // application focus out of the input field, especially at its start.
        return connection.setSelection(absolute, absolute);
    }

    private Snapshot read(InputConnection connection) {
        if (Build.VERSION.SDK_INT >= 31) {
            SurroundingText nearby = connection.getSurroundingText(256, 256, 0);
            if (nearby != null) {
                Snapshot value = snapshot(nearby.getText(), nearby.getOffset(),
                    nearby.getSelectionStart(), nearby.getSelectionEnd());
                if (value != null) return value;
            }
        }
        ExtractedTextRequest request = new ExtractedTextRequest();
        request.hintMaxChars = 1024; request.hintMaxLines = 16;
        ExtractedText value = connection.getExtractedText(request, 0);
        return value == null ? null : snapshot(value.text, value.startOffset, value.selectionStart, value.selectionEnd);
    }

    private Snapshot snapshot(CharSequence text, int offset, int start, int end) {
        if (text == null || offset < 0 || text.length() > Integer.MAX_VALUE - offset
                || start < 0 || end < 0 || start > text.length() || end > text.length()) return null;
        return new Snapshot(text, offset, start, end);
    }

    /** Text is transient for this move; no editor contents or connection persist. */
    private static final class Snapshot {
        final CharSequence text;
        final int offset, start, end;
        Snapshot(CharSequence text, int offset, int start, int end) {
            this.text = text; this.offset = offset; this.start = start; this.end = end;
        }
    }
}
