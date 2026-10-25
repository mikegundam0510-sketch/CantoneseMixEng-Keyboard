package hk.cantonesemixeng.keyboard;

import android.os.Build;
import android.view.inputmethod.*;

/** One transient automatic commit; no editor connection or learning data is retained. */
final class TopOutUndo {
    final String source, text;
    private final int cursor;
    private final String before;

    private TopOutUndo(String source, String text, int cursor, String before) {
        this.source=source; this.text=text; this.cursor=cursor; this.before=before;
    }

    static TopOutUndo capture(InputConnection connection, String source, String text, String following) {
        if (connection==null || source==null || !source.matches("[a-z]{2,48}") || text==null || text.isEmpty()) return null;
        Snapshot value=read(connection);
        if (value==null || !value.before.endsWith(text+following)) return null;
        String prefix=value.before.substring(0,value.before.length()-following.length());
        prefix=prefix.substring(Math.max(0,prefix.length()-128));
        int cursor=value.cursor-following.length();
        return cursor<text.length() ? null : new TopOutUndo(source,text,cursor,prefix);
    }

    boolean valid(InputConnection connection, String following) {
        return matches(read(connection),following);
    }

    private boolean matches(Snapshot value, String following) {
        return value!=null && following!=null && following.length()<=48
            && value.cursor==cursor+following.length() && before.endsWith(text)
            && value.before.endsWith(before+following);
    }

    boolean restore(InputConnection connection, String following) {
        if (!matches(read(connection),following)) return false;
        // Replace the auto-committed suffix and remaining composition together.
        // Never delete first: refusal must leave the actual text intact.
        connection.beginBatchEdit();
        boolean marked=false, accepted=false;
        try {
            marked=connection.setComposingRegion(cursor-text.length(),cursor+following.length());
            accepted=marked && connection.setComposingText(source+following,1);
            return accepted;
        } finally {
            if (marked && !accepted) {
                if (following.isEmpty()) connection.finishComposingText();
                else connection.setComposingRegion(cursor,cursor+following.length());
            }
            connection.endBatchEdit();
        }
    }

    private static Snapshot read(InputConnection connection) {
        if (connection==null) return null;
        if (Build.VERSION.SDK_INT>=31) {
            SurroundingText nearby=connection.getSurroundingText(256,0,0);
            if (nearby!=null) {
                Snapshot value=snapshot(nearby.getText(),nearby.getOffset(),nearby.getSelectionStart(),nearby.getSelectionEnd());
                if (value!=null) return value;
            }
        }
        ExtractedTextRequest request=new ExtractedTextRequest(); request.hintMaxChars=256; request.hintMaxLines=8;
        ExtractedText extracted=connection.getExtractedText(request,0);
        return extracted==null ? null : snapshot(extracted.text,extracted.startOffset,extracted.selectionStart,extracted.selectionEnd);
    }

    private static Snapshot snapshot(CharSequence text, int offset, int start, int end) {
        if (text==null || offset<0 || start<0 || start!=end || end>text.length() || end>Integer.MAX_VALUE-offset) return null;
        return new Snapshot(offset+end,text.subSequence(Math.max(0,end-256),end).toString());
    }

    private static final class Snapshot {
        final int cursor; final String before;
        Snapshot(int cursor,String before) {this.cursor=cursor;this.before=before;}
    }
}
