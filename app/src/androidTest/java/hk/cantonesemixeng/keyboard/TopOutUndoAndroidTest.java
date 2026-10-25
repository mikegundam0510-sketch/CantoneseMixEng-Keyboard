package hk.cantonesemixeng.keyboard;

import android.app.*;
import android.view.ContextThemeWrapper;
import android.view.inputmethod.*;
import android.widget.EditText;
import androidx.test.filters.SdkSuppress;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import static org.junit.Assert.*;

/** Real Android composition spans and UTF-16 positions, including refused editor operations. */
@SdkSuppress(minSdkVersion=31)
public class TopOutUndoAndroidTest {
    private final Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
    private EditText edit;
    private InputConnection connection;
    private TopOutUndo undo;

    @Before public void setup() {
        instrumentation.runOnMainSync(()->{
            // Exercise the real platform EditableInputConnection without relying
            // on the software emulator's window manager or keyboard animations.
            edit=new EditText(new ContextThemeWrapper(instrumentation.getTargetContext(),android.R.style.Theme_Material_Light));
            connection=edit.onCreateInputConnection(new EditorInfo());assertNotNull(connection);
        });
    }
    private void seed(String prefix,String source,String automatic,String following) {
        edit.setText(prefix+automatic+following);edit.setSelection(edit.length());
        connection.setComposingRegion(prefix.length()+automatic.length(),edit.length());
        undo=TopOutUndo.capture(connection,source,automatic,following);assertNotNull(undo);
    }
    @Test public void restorePreservesFollowingKeyAndCreatesOneComposition() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");assertTrue(undo.restore(connection,"z"));
            assertEquals("前文ofz",edit.getText().toString());assertEquals(5,edit.getSelectionStart());
            assertEquals(2,BaseInputConnection.getComposingSpanStart(edit.getText()));
            assertEquals(5,BaseInputConnection.getComposingSpanEnd(edit.getText()));
        });
    }
    @Test public void supplementaryAutomaticCharacterAndMultipleFollowingKeysKeepOffsets() {
        instrumentation.runOnMainSync(()->{
            seed("前文","rn","𠮩","vz");assertTrue(undo.restore(connection,"vz"));
            assertEquals("前文rnvz",edit.getText().toString());assertEquals(6,edit.getSelectionEnd());
        });
    }
    @Test public void multipleAutomaticCharactersRestoreAllTheirRawCodes() {
        instrumentation.runOnMainSync(()->{
            seed("前文","ofvd","你好","z");assertTrue(undo.restore(connection,"z"));
            assertEquals("前文ofvdz",edit.getText().toString());
        });
    }
    @Test public void laterRawKeysStillBelongToTheRestoredComposition() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");connection.setComposingText("zx",1);
            assertTrue(undo.valid(connection,"zx"));assertTrue(undo.restore(connection,"zx"));
            assertEquals("前文ofzx",edit.getText().toString());
        });
    }
    @Test public void refusedRegionDoesNotDeleteText() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");
            InputConnection refusal=new InputConnectionWrapper(connection,false) {
                @Override public boolean setComposingRegion(int start,int end){return false;}
            };
            assertFalse(undo.restore(refusal,"z"));assertEquals("前文係z",edit.getText().toString());
        });
    }
    @Test public void refusedReplacementRestoresPreviousCompositionSpan() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");
            InputConnection refusal=new InputConnectionWrapper(connection,false) {
                @Override public boolean setComposingText(CharSequence text,int cursor){return false;}
            };
            assertFalse(undo.restore(refusal,"z"));assertEquals("前文係z",edit.getText().toString());
            assertEquals(3,BaseInputConnection.getComposingSpanStart(edit.getText()));
            assertEquals(4,BaseInputConnection.getComposingSpanEnd(edit.getText()));
        });
    }
    @Test public void cursorMovementAndSelectionRejectUndo() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");edit.setSelection(0);
            assertFalse(undo.restore(connection,"z"));assertEquals("前文係z",edit.getText().toString());
            edit.setSelection(2,4);assertFalse(undo.restore(connection,"z"));
        });
    }
    @Test public void changedTextAtTheSameCursorIsNotReplaced() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");edit.setText("前文你z");edit.setSelection(edit.length());
            assertFalse(undo.restore(connection,"z"));assertEquals("前文你z",edit.getText().toString());
        });
    }
    @Test public void extractedTextFallbackHonorsNonzeroWindowOffsets() {
        instrumentation.runOnMainSync(()->{
            String prefix=new String(new char[180]).replace("\0","香港");seed(prefix,"of","係","z");
            InputConnection window=new InputConnectionWrapper(connection,false) {
                @Override public SurroundingText getSurroundingText(int before,int after,int flags){return null;}
                @Override public ExtractedText getExtractedText(ExtractedTextRequest request,int flags) {
                    ExtractedText value=new ExtractedText();value.startOffset=300;
                    value.text=edit.getText().subSequence(300,edit.length());
                    value.selectionStart=edit.getSelectionStart()-300;value.selectionEnd=edit.getSelectionEnd()-300;return value;
                }
            };
            TopOutUndo saved=TopOutUndo.capture(window,"of","係","z");assertNotNull(saved);
            assertTrue(saved.restore(window,"z"));assertEquals(prefix+"ofz",edit.getText().toString());
        });
    }
    @Test public void unavailablePositionCannotRestoreText() {
        instrumentation.runOnMainSync(()->{
            seed("前文","of","係","z");
            InputConnection unsupported=new InputConnectionWrapper(connection,false) {
                @Override public SurroundingText getSurroundingText(int before,int after,int flags){return null;}
                @Override public ExtractedText getExtractedText(ExtractedTextRequest request,int flags){return null;}
            };
            assertNull(TopOutUndo.capture(unsupported,"of","係","z"));
            assertFalse(undo.restore(unsupported,"z"));assertEquals("前文係z",edit.getText().toString());
        });
    }
}
