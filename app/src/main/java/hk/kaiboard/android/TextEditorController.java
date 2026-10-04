package hk.kaiboard.android;

import android.os.SystemClock;
import android.view.KeyEvent;
import android.view.inputmethod.InputConnection;

/** Let the editor handle line geometry, Unicode cursor stops and selection anchors. */
final class TextEditorController {
    boolean selecting;
    void move(InputConnection connection, int key) {
        if (connection == null) return;
        int meta = selecting ? KeyEvent.META_SHIFT_ON | KeyEvent.META_SHIFT_LEFT_ON : 0;
        if (key == KeyEvent.KEYCODE_MOVE_HOME || key == KeyEvent.KEYCODE_MOVE_END)
            meta |= KeyEvent.META_CTRL_ON | KeyEvent.META_CTRL_LEFT_ON;
        long now = SystemClock.uptimeMillis();
        connection.sendKeyEvent(new KeyEvent(now, now, KeyEvent.ACTION_DOWN, key, 0, meta));
        connection.sendKeyEvent(new KeyEvent(now, now, KeyEvent.ACTION_UP, key, 0, meta));
    }
    void action(InputConnection connection, int action) {
        if (connection != null) connection.performContextMenuAction(action);
    }
}
