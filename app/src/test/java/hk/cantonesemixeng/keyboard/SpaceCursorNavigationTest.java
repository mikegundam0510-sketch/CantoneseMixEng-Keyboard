package hk.cantonesemixeng.keyboard;

import android.view.inputmethod.ExtractedText;
import android.view.inputmethod.InputConnection;
import java.lang.reflect.Proxy;
import java.text.BreakIterator;
import org.junit.Test;
import static org.junit.Assert.*;

public class SpaceCursorNavigationTest {
    private SpaceCursorController controller() {
        // The device uses Android ICU. JVM tests exercise the actual connection
        // operations/bounds with JDK character boundaries, without mocking movement.
        return new SpaceCursorController(text -> {
            BreakIterator iterator = BreakIterator.getCharacterInstance();iterator.setText(text.toString());
            return (position,direction) -> direction < 0 ? iterator.preceding(position) : iterator.following(position);
        });
    }

    private static final class Editor {
        String text; int offset, start, end, selections, keyEvents, mutations;
        boolean unavailable, rejectSelection;
        final InputConnection connection = (InputConnection)Proxy.newProxyInstance(
            InputConnection.class.getClassLoader(), new Class<?>[]{InputConnection.class}, (proxy,method,args) -> {
                switch (method.getName()) {
                    case "getExtractedText":
                        if (unavailable) return null;
                        ExtractedText value = new ExtractedText();value.text=text;value.startOffset=offset;
                        value.selectionStart=start;value.selectionEnd=end;return value;
                    case "setSelection":
                        selections++;
                        int a=(Integer)args[0],b=(Integer)args[1];
                        assertTrue(a>=offset && b>=offset && a<=offset+text.length() && b<=offset+text.length());
                        if (rejectSelection) return false;
                        start=a-offset;end=b-offset;return true;
                    case "sendKeyEvent": keyEvents++;return false;
                    case "commitText": case "deleteSurroundingText": mutations++;return false;
                    default:
                        if (method.getReturnType()==boolean.class) return false;
                        if (method.getReturnType()==int.class) return 0;
                        return null;
                }
            });
        Editor(String text,int position) { this.text=text;start=end=position; }
        void safe() { assertEquals(0,keyEvents);assertEquals(0,mutations); }
    }

    @Test public void leftStopsAtStartInsteadOfDispatchingFocusNavigation() {
        Editor e=new Editor("香港",1);SpaceCursorController c=controller();
        assertTrue(c.move(e.connection,-1));assertEquals(0,e.end);
        for(int n=0;n<10;n++)assertFalse(c.move(e.connection,-1));
        assertEquals(1,e.selections);assertEquals("香港",e.text);e.safe();
    }
    @Test public void rightStopsAtEndWithoutNavigationKeys() {
        Editor e=new Editor("香港",1);SpaceCursorController c=controller();
        assertTrue(c.move(e.connection,1));assertEquals(2,e.end);
        assertFalse(c.move(e.connection,20));assertEquals(1,e.selections);e.safe();
    }
    @Test public void emptyInputNeverMovesFocus() {
        Editor e=new Editor("",0);assertFalse(controller().move(e.connection,-1));
        assertFalse(controller().move(e.connection,1));assertEquals(0,e.selections);e.safe();
    }
    @Test public void existingSelectionCollapsesInEitherDirection() {
        for(int direction:new int[]{-1,1})for(boolean reversed:new boolean[]{false,true}) {
            Editor e=new Editor("甲乙丙丁",0);e.start=reversed?3:1;e.end=reversed?1:3;
            assertTrue(controller().move(e.connection,direction));assertEquals(direction<0?1:3,e.end);
            assertEquals(e.start,e.end);e.safe();
        }
    }
    @Test public void partialTextUsesAbsoluteOffsetAndStopsAtWindowBoundary() {
        Editor e=new Editor("香港",1);e.offset=100;SpaceCursorController c=controller();
        assertTrue(c.move(e.connection,-20));assertEquals(0,e.end);
        assertFalse(c.move(e.connection,-1));assertTrue(c.move(e.connection,20));assertEquals(2,e.end);e.safe();
    }
    @Test public void unsupportedExtractionDoesNotFallBackToDpad() {
        Editor e=new Editor("香港",0);e.unavailable=true;
        assertFalse(controller().move(e.connection,-1));assertEquals(0,e.selections);e.safe();
    }
    @Test public void invalidSelectionAndOffsetsAreIgnored() {
        for(int[] values:new int[][]{{-1,0,0},{0,-1,0},{0,0,3},{Integer.MAX_VALUE,0,0}}) {
            Editor e=new Editor("香港",0);e.offset=values[0];e.start=values[1];e.end=values[2];
            assertFalse(controller().move(e.connection,1));assertEquals(0,e.selections);e.safe();
        }
    }
    @Test public void rejectedSelectionDoesNotDispatchAlternativeKeys() {
        Editor e=new Editor("香港",1);e.rejectSelection=true;
        assertFalse(controller().move(e.connection,-1));assertEquals(1,e.end);e.safe();
    }
    @Test public void surrogatePairAndCombiningMarkStayWhole() {
        Editor e=new Editor("A😀e\u0301港",6);SpaceCursorController c=controller();
        assertTrue(c.move(e.connection,-1));assertEquals(5,e.end);
        assertTrue(c.move(e.connection,-1));assertEquals(3,e.end);
        assertTrue(c.move(e.connection,-1));assertEquals(1,e.end);e.safe();
    }
    @Test public void eachMoveReadsTheCurrentEditorSelection() {
        Editor e=new Editor("甲乙丙丁",3);SpaceCursorController c=controller();
        assertTrue(c.move(e.connection,-1));assertEquals(2,e.end);
        e.start=e.end=4;
        assertTrue(c.move(e.connection,-1));assertEquals(3,e.end);e.safe();
    }
    @Test public void largeStepCountsAreBoundedWithoutIntegerOverflow() {
        Editor e=new Editor("甲".repeat(30),30);SpaceCursorController c=controller();
        assertTrue(c.move(e.connection,Integer.MIN_VALUE));assertEquals(10,e.end);
        assertTrue(c.move(e.connection,Integer.MAX_VALUE));assertEquals(30,e.end);e.safe();
    }
    @Test public void missingConnectionAndZeroMovementAreNoOps() {
        assertFalse(controller().move(null,-1));Editor e=new Editor("香港",1);
        assertFalse(controller().move(e.connection,0));assertEquals(0,e.selections);e.safe();
    }
}
