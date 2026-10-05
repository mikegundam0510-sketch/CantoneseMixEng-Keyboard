package hk.kaiboard.android;

import android.app.Activity;
import android.content.Intent;
import android.os.SystemClock;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;
import android.view.MotionEvent;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.concurrent.atomic.AtomicInteger;

/** Android View dispatch, including overlapping fingers on separate keys. */
@RunWith(AndroidJUnit4.class)
public final class CursorGestureTouchTest {
    private android.app.Instrumentation getInstrumentation() { return InstrumentationRegistry.getInstrumentation(); }
    private Activity activity;
    private CursorGestureRow row;
    private final AtomicInteger clicks = new AtomicInteger();
    private final AtomicInteger starts = new AtomicInteger();
    private final AtomicInteger steps = new AtomicInteger();
    private long down;

    @Before public void setUp() throws Exception {
        Intent intent = new Intent(getInstrumentation().getTargetContext(), KeyboardPreviewActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        activity = getInstrumentation().startActivitySync(intent);
        getInstrumentation().runOnMainSync(() -> {
            row = new CursorGestureRow(activity, starts::incrementAndGet, steps::addAndGet);
            row.setMotionEventSplittingEnabled(true);
            for (int i=0;i<2;i++) {
                KeyboardKey key = new KeyboardKey(activity);
                key.typingTouch(true);
                key.setContentDescription(i==0 ? "A，日" : "B，月");
                key.setOnClickListener(v -> clicks.incrementAndGet());
                row.addView(key,new LinearLayout.LayoutParams(200,100));
            }
            activity.setContentView(row);
        });
        getInstrumentation().waitForIdleSync();
        getInstrumentation().runOnMainSync(() -> {
            row.measure(View.MeasureSpec.makeMeasureSpec(400,View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(100,View.MeasureSpec.EXACTLY));
            row.layout(0,0,400,100);
        });
        down=SystemClock.uptimeMillis();
    }

    private void event(int action, int[] ids, float[] xs) {
        getInstrumentation().runOnMainSync(() -> {
            MotionEvent.PointerProperties[] props=new MotionEvent.PointerProperties[ids.length];
            MotionEvent.PointerCoords[] coords=new MotionEvent.PointerCoords[ids.length];
            for(int i=0;i<ids.length;i++) {
                props[i]=new MotionEvent.PointerProperties();props[i].id=ids[i];props[i].toolType=MotionEvent.TOOL_TYPE_FINGER;
                coords[i]=new MotionEvent.PointerCoords();coords[i].x=xs[i];coords[i].y=50;coords[i].pressure=1;coords[i].size=1;
            }
            MotionEvent e=MotionEvent.obtain(down,SystemClock.uptimeMillis(),action,ids.length,props,coords,0,0,1,1,0,0,android.view.InputDevice.SOURCE_TOUCHSCREEN,0);
            row.dispatchTouchEvent(e);e.recycle();
        });
        getInstrumentation().waitForIdleSync();
    }
    @Test public void testOverlappingFingerTapsKeepBothClicks() {
        for(int i=0;i<25;i++) {
            event(MotionEvent.ACTION_DOWN,new int[]{0},new float[]{100});
            event(MotionEvent.ACTION_POINTER_DOWN | (1<<MotionEvent.ACTION_POINTER_INDEX_SHIFT),new int[]{0,1},new float[]{100,300});
            event(MotionEvent.ACTION_POINTER_UP,new int[]{0,1},new float[]{100,300});
            event(MotionEvent.ACTION_UP,new int[]{1},new float[]{300});
        }
        assertEquals(50,clicks.get());assertEquals(0,starts.get());assertEquals(0,steps.get());
    }
    @Test public void testHorizontalDragCancelsKeyClick() {
        event(MotionEvent.ACTION_DOWN,new int[]{0},new float[]{20});
        event(MotionEvent.ACTION_MOVE,new int[]{0},new float[]{190});
        event(MotionEvent.ACTION_MOVE,new int[]{0},new float[]{350});
        event(MotionEvent.ACTION_UP,new int[]{0},new float[]{350});
        assertEquals(0,clicks.get());assertEquals(1,starts.get());assertTrue(steps.get()>0);
    }
    @Test public void testSmallFingerMovementStillClicks() {
        event(MotionEvent.ACTION_DOWN,new int[]{0},new float[]{100});
        event(MotionEvent.ACTION_MOVE,new int[]{0},new float[]{102});
        event(MotionEvent.ACTION_UP,new int[]{0},new float[]{102});
        assertEquals(1,clicks.get());assertEquals(0,starts.get());
    }
    @Test public void testOuterKeyEdgesAcceptClicks() {
        event(MotionEvent.ACTION_DOWN,new int[]{0},new float[]{1});
        event(MotionEvent.ACTION_UP,new int[]{0},new float[]{1});
        event(MotionEvent.ACTION_DOWN,new int[]{0},new float[]{399});
        event(MotionEvent.ACTION_UP,new int[]{0},new float[]{399});
        assertEquals(2,clicks.get());assertEquals(0,starts.get());
    }
    @After public void tearDown() throws Exception {
        getInstrumentation().runOnMainSync(() -> activity.finish());

    }
}

