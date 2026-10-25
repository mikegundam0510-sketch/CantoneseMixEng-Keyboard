package hk.cantonesemixeng.keyboard;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.view.KeyEvent;
import android.view.inputmethod.*;
import android.widget.*;
import androidx.test.filters.SdkSuppress;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import static org.junit.Assert.*;

/** Real editor focus and Android ICU checks; no phone text is logged or saved. */
@SdkSuppress(minSdkVersion=31)
public class SpaceCursorAndroidTest {
    private final Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
    private Activity activity;
    private EditText edit,other;
    private InputConnection connection;
    private SpaceCursorController controller;
    private int keyEvents;

    @Before public void setup() {
        activity=instrumentation.startActivitySync(new Intent(instrumentation.getTargetContext(),KeyboardPreviewActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        instrumentation.runOnMainSync(() -> {
            LinearLayout row=new LinearLayout(activity);
            other=new EditText(activity);other.setText("其他輸入欄");
            edit=new EditText(activity);edit.setText("香港");
            row.addView(other,new LinearLayout.LayoutParams(0,150,1));
            row.addView(edit,new LinearLayout.LayoutParams(0,150,1));
            activity.setContentView(row);edit.requestFocus();edit.setSelection(1);
            connection=wrap(edit.onCreateInputConnection(new EditorInfo()),false);
            controller=new SpaceCursorController();
        });
    }

    @After public void finish() {
        instrumentation.runOnMainSync(() -> {if(activity!=null)activity.finish();});
    }

    private InputConnection wrap(InputConnection target,boolean unavailable) {
        return new InputConnectionWrapper(target,false) {
            @Override public SurroundingText getSurroundingText(int before,int after,int flags) {
                return unavailable?null:super.getSurroundingText(before,after,flags);
            }
            @Override public ExtractedText getExtractedText(ExtractedTextRequest request,int flags) {
                return unavailable?null:super.getExtractedText(request,flags);
            }
            @Override public boolean sendKeyEvent(KeyEvent event) {keyEvents++;return super.sendKeyEvent(event);}
        };
    }

    @Test public void leftBoundaryDoesNotFocusAdjacentInput() {
        instrumentation.runOnMainSync(() -> {
            for(int n=0;n<20;n++)controller.move(connection,-1);
            assertEquals(0,edit.getSelectionEnd());assertTrue(edit.hasFocus());assertFalse(other.hasFocus());
            assertEquals("香港",edit.getText().toString());assertEquals(0,keyEvents);
        });
    }

    @Test public void rightBoundaryAndEmptyFieldStayFocused() {
        instrumentation.runOnMainSync(() -> {
            for(int n=0;n<20;n++)controller.move(connection,1);
            assertEquals(edit.length(),edit.getSelectionEnd());assertTrue(edit.hasFocus());
            edit.setText("");controller.move(connection,-20);controller.move(connection,20);
            assertEquals(0,edit.getSelectionEnd());assertTrue(edit.hasFocus());assertEquals(0,keyEvents);
        });
    }

    @Test public void actualIcuKeepsEmojiFamilyAndCombiningMarkWhole() {
        instrumentation.runOnMainSync(() -> {
            String family="👨‍👩‍👧‍👦";edit.setText("A"+family+"e\u0301港");edit.setSelection(edit.length());
            controller.move(connection,-1);assertEquals(edit.length()-1,edit.getSelectionEnd());
            controller.move(connection,-1);assertEquals(1+family.length(),edit.getSelectionEnd());
            controller.move(connection,-1);assertEquals(1,edit.getSelectionEnd());
            controller.move(connection,-20);assertEquals(0,edit.getSelectionEnd());
            controller.move(connection,-20);assertTrue(edit.hasFocus());assertEquals(0,keyEvents);
        });
    }

    @Test public void unsupportedEditorDoesNotSendArrowFallback() {
        instrumentation.runOnMainSync(() -> {
            InputConnection unsupported=wrap(connection,true);
            assertFalse(controller.move(unsupported,-1));assertEquals(1,edit.getSelectionEnd());
            assertTrue(edit.hasFocus());assertEquals(0,keyEvents);
        });
    }
}
