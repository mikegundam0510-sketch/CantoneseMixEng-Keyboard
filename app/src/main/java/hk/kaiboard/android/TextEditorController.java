package hk.kaiboard.android;

import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.inputmethod.ExtractedText;
import android.view.inputmethod.ExtractedTextRequest;
import android.view.inputmethod.InputConnection;
import android.icu.text.BreakIterator;

/** Direct selection ranges; the editor still owns visual up/down line geometry. */
final class TextEditorController {
    boolean selecting;
    private int anchor = -1, generation;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private ExtractedText text(InputConnection connection) {
        return connection == null ? null : connection.getExtractedText(new ExtractedTextRequest(), 0);
    }
    void reset() {
        selecting = false; anchor = -1; generation++; handler.removeCallbacksAndMessages(null);
    }
    void setSelecting(boolean enabled, InputConnection connection) {
        reset(); selecting = enabled;
        ExtractedText value = text(connection);
        if (enabled && value != null) anchor = value.startOffset + value.selectionStart;
    }
    private void range(InputConnection connection, int focus) {
        connection.setSelection(selecting && anchor >= 0 ? anchor : focus, focus);
    }
    void move(InputConnection connection, int key) {
        if (connection == null) return;
        int request = ++generation;
        ExtractedText value = text(connection);
        if (value == null || value.text == null) { send(connection, key); return; }
        int start = value.selectionStart, end = value.selectionEnd;
        if (start < 0 || end < 0 || start > value.text.length() || end > value.text.length()) { send(connection, key); return; }
        if (selecting && anchor < 0) anchor = value.startOffset + start;
        int focus = end;
        if (key == KeyEvent.KEYCODE_DPAD_LEFT || key == KeyEvent.KEYCODE_DPAD_RIGHT) {
            if (!selecting && start != end) focus = key == KeyEvent.KEYCODE_DPAD_LEFT ? Math.min(start,end) : Math.max(start,end);
            else {
                // ICU character boundaries keep surrogate pairs and Emoji sequences together.
                BreakIterator boundaries = BreakIterator.getCharacterInstance();
                boundaries.setText(value.text.toString());
                int next = key == KeyEvent.KEYCODE_DPAD_LEFT ? boundaries.preceding(end) : boundaries.following(end);
                if (next != BreakIterator.DONE) focus = next;
            }
            range(connection, value.startOffset + focus); return;
        }
        if ((key == KeyEvent.KEYCODE_MOVE_HOME || key == KeyEvent.KEYCODE_MOVE_END) && value.startOffset == 0) {
            range(connection, key == KeyEvent.KEYCODE_MOVE_HOME ? 0 : value.text.length()); return;
        }
        if (selecting) connection.setSelection(value.startOffset + end, value.startOffset + end);
        send(connection, key);
        if (selecting) handler.postDelayed(() -> {
            if (generation != request || !selecting) return;
            ExtractedText moved = text(connection);
            if (moved != null && moved.selectionEnd >= 0) range(connection, moved.startOffset + moved.selectionEnd);
        }, 40);
    }
    private void send(InputConnection connection, int key) {
        int meta = key == KeyEvent.KEYCODE_MOVE_HOME || key == KeyEvent.KEYCODE_MOVE_END ? KeyEvent.META_CTRL_ON : 0;
        long now = android.os.SystemClock.uptimeMillis();
        connection.sendKeyEvent(new KeyEvent(now,now,KeyEvent.ACTION_DOWN,key,0,meta));
        connection.sendKeyEvent(new KeyEvent(now,now,KeyEvent.ACTION_UP,key,0,meta));
    }
    void action(InputConnection connection, int action) {
        generation++; handler.removeCallbacksAndMessages(null);
        if (connection != null) connection.performContextMenuAction(action);
    }
}
