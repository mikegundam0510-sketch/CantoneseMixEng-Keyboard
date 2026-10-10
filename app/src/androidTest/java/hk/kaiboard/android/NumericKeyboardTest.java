package hk.kaiboard.android;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.*;
import android.content.*;
import android.graphics.*;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.view.accessibility.*;
import android.view.inputmethod.*;
import android.widget.EditText;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.*;
import org.junit.runner.RunWith;
import org.json.*;
import java.io.*;
import java.lang.reflect.Field;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.Assert.*;

/** Real IME events, editor acknowledgements and pixels, including protected PIN fields. */
@RunWith(AndroidJUnit4.class)
public class NumericKeyboardTest {
    private final Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
    private final UiAutomation automation=instrumentation.getUiAutomation();
    private Activity activity;
    private EditText editor;
    private SharedPreferences preferences;
    private Map<String,?> saved;
    private Map<String,Map<String,?>> learningBefore;
    private File evidence;
    private final AtomicInteger receivedAction=new AtomicInteger();
    private final JSONArray checks=new JSONArray();
    private static final String[] STORES={"learned","recent_learned","rejected_learned","english_learned"};

    @Before public void setup() throws Exception {
        Context context=instrumentation.getTargetContext();
        preferences=Prefs.get(context);saved=preferences.getAll();
        learningBefore=new HashMap<>();
        for(String name:STORES) learningBefore.put(name,context.getSharedPreferences(name,0).getAll());
        preferences.edit().putBoolean("learning",true).putString("hand","full").putString("height","44")
            .putString("theme","dark").putBoolean("split",true).commit();
        evidence=new File(context.getFilesDir(),"numeric-keyboard-evidence");evidence.mkdirs();
        writeResult(new JSONObject().put("status","running"));
        AccessibilityServiceInfo info=automation.getServiceInfo();
        info.flags|=AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS|AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
        automation.setServiceInfo(info);
        shell("settings put secure show_ime_with_hard_keyboard 1");
    }
    private void shell(String command) throws Exception {
        try(ParcelFileDescriptor fd=automation.executeShellCommand(command);
                InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(fd)) {
            byte[] buffer=new byte[1024];while(in.read(buffer)!=-1) { /* Drain shell output on Android 12. */ }
        }
    }
    private void window(String size) throws Exception {
        if(activity!=null) instrumentation.runOnMainSync(()->activity.finish());
        shell("wm size "+size);shell("wm density 320");
        progress("Display configured: "+size);
        Intent intent=new Intent(instrumentation.getTargetContext(),KeyboardPreviewActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);intent.putExtra("test_input_type","number");
        activity=instrumentation.startActivitySync(intent);
        Field field=KeyboardPreviewActivity.class.getDeclaredField("input");field.setAccessible(true);
        editor=(EditText)field.get(activity);
        progress("Native editor attached");
        instrumentation.runOnMainSync(()->editor.setOnEditorActionListener((v,id,event)->{receivedAction.set(id);return true;}));
        // Instrumentation stops the target process; rebind the IME after attaching its editor.
        shell("ime reset");shell("ime enable hk.kaiboard.android/.KaiboardService");
        shell("ime set hk.kaiboard.android/.KaiboardService");
        progress("IME selected");
    }
    private void input(int type,int action) {
        receivedAction.set(0);
        instrumentation.runOnMainSync(()->{
            editor.setInputType(type);editor.setImeOptions(action);editor.setText("");editor.requestFocus();
            InputMethodManager manager=(InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);
            manager.restartInput(editor);manager.showSoftInput(editor,InputMethodManager.SHOW_FORCED);
        });
    }
    private AccessibilityNodeInfo find(AccessibilityNodeInfo root,String description) {
        if(root==null) return null;
        if(description.contentEquals(root.getContentDescription()==null ? "" : root.getContentDescription())) return root;
        for(int i=0;i<root.getChildCount();i++) {
            AccessibilityNodeInfo found=find(root.getChild(i),description);
            if(found!=null) return found;
        }
        return null;
    }
    private AccessibilityNodeInfo node(String description) {
        long deadline=SystemClock.uptimeMillis()+60000;
        while(SystemClock.uptimeMillis()<deadline) {
            List<AccessibilityWindowInfo> windows=automation.getWindows();
            // Software CPU emulation can stall System UI during a display resize.
            // Dismiss only that system dialog; application ANRs remain test failures.
            boolean dismissed=false;
            for(AccessibilityWindowInfo window:windows) {
                AccessibilityNodeInfo root=window.getRoot();
                if(root==null || root.findAccessibilityNodeInfosByText("System UI isn't responding").isEmpty()) continue;
                for(AccessibilityNodeInfo button:root.findAccessibilityNodeInfosByText("Close app")) {
                    Rect bounds=new Rect();button.getBoundsInScreen(bounds);tap(bounds,0);dismissed=true;break;
                }
            }
            if(dismissed) {
                instrumentation.runOnMainSync(()->{
                    editor.requestFocus();
                    InputMethodManager manager=(InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);
                    manager.restartInput(editor);manager.showSoftInput(editor,InputMethodManager.SHOW_FORCED);
                });
                SystemClock.sleep(500);continue;
            }
            for(AccessibilityWindowInfo window:windows) {
                AccessibilityNodeInfo found=find(window.getRoot(),description);
                if(found!=null) return found;
            }
            SystemClock.sleep(100);
        }
        throw new AssertionError("Missing numeric control: "+description);
    }
    private Rect box(String description) {
        Rect result=new Rect();node(description).getBoundsInScreen(result);return result;
    }
    private void tap(Rect box,long held) {
        long down=SystemClock.uptimeMillis();
        MotionEvent start=MotionEvent.obtain(down,down,MotionEvent.ACTION_DOWN,box.exactCenterX(),box.exactCenterY(),0);
        start.setSource(InputDevice.SOURCE_TOUCHSCREEN);assertTrue(automation.injectInputEvent(start,true));start.recycle();
        if(held>0) SystemClock.sleep(held);
        MotionEvent end=MotionEvent.obtain(down,SystemClock.uptimeMillis(),MotionEvent.ACTION_UP,box.exactCenterX(),box.exactCenterY(),0);
        end.setSource(InputDevice.SOURCE_TOUCHSCREEN);assertTrue(automation.injectInputEvent(end,true));end.recycle();
    }
    private String text() {
        String[] value={""};instrumentation.runOnMainSync(()->value[0]=editor.getText().toString());return value[0];
    }
    private void expect(String wanted) {
        long deadline=SystemClock.uptimeMillis()+15000;
        while(SystemClock.uptimeMillis()<deadline) {
            if(text().equals(wanted)) return;SystemClock.sleep(50);
        }
        assertEquals(wanted,text());
    }
    private void action(Rect key,int expected) {
        tap(key,0);long deadline=SystemClock.uptimeMillis()+10000;
        while(receivedAction.get()!=expected && SystemClock.uptimeMillis()<deadline) SystemClock.sleep(50);
        assertEquals("Native editor action",expected,receivedAction.get());
    }
    private void screenshot(String name,String actionDescription) throws Exception {
        for(int attempt=0;attempt<3;attempt++) {
            Rect delete=box("刪除，長按連續刪除"),action=box(actionDescription);
            // Native screen bytes also work when UiAutomation's screenshot path is unavailable.
            Bitmap image;
            try(ParcelFileDescriptor fd=automation.executeShellCommand("screencap -p");
                    InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(fd)) {
                image=BitmapFactory.decodeStream(in);
            }
            assertNotNull("Native screen capture unavailable",image);
            try(FileOutputStream out=new FileOutputStream(new File(evidence,name+".png"))) {
                assertTrue(image.compress(Bitmap.CompressFormat.PNG,100,out));
            }
            boolean icons=pixels(image,delete,0xFFE8EAED)>20 && pixels(image,action,0xFF173358)>20;
            image.recycle();
            boolean stable=delete.equals(box("刪除，長按連續刪除")) && action.equals(box(actionDescription));
            if(icons && stable) return;
            assertTrue("Icons hidden or layout unstable after navigation restart: "+name,attempt<2);
            // A software-emulated System UI restart can add navigation buttons over an old IME
            // frame. Re-show it to receive current insets; never accept a blank icon screenshot.
            instrumentation.runOnMainSync(()->((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE))
                .hideSoftInputFromWindow(editor.getWindowToken(),0));
            SystemClock.sleep(500);
            instrumentation.runOnMainSync(()->{
                InputMethodManager manager=(InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);
                editor.requestFocus();manager.restartInput(editor);manager.showSoftInput(editor,InputMethodManager.SHOW_FORCED);
            });
            SystemClock.sleep(500);
        }
    }
    private int pixels(Bitmap image,Rect box,int color) {
        int radius=Math.min(box.height()/3,box.width()/4),matches=0;
        for(int y=box.centerY()-radius;y<box.centerY()+radius;y++)
            for(int x=box.centerX()-radius;x<box.centerX()+radius;x++) {
                int pixel=image.getPixel(x,y);
                if(Math.abs(Color.red(pixel)-Color.red(color))<8 && Math.abs(Color.green(pixel)-Color.green(color))<8
                        && Math.abs(Color.blue(pixel)-Color.blue(color))<8) matches++;
            }
        return matches;
    }
    @Test public void narrowAndWideNumericInputsIconsAndPrivacy() throws Exception {
        for(String[] layout:new String[][]{{"cover","720x1600"},{"unfolded","1440x1800"}}) {
            progress("Starting "+layout[0]);
            window(layout[1]);input(InputType.TYPE_CLASS_NUMBER,EditorInfo.IME_ACTION_NEXT);
            screenshot(layout[0]+"-number","下一個");
            int width=Integer.parseInt(layout[1].split("x")[0]);
            Map<Character,Rect> digits=new HashMap<>();
            for(char c:"0123456789".toCharArray()) digits.put(c,box(String.valueOf(c)));
            Rect delete=box("刪除，長按連續刪除"),next=box("下一個");
            Rect bounds=new Rect(digits.get('1'));bounds.union(digits.get('3'));bounds.union(delete);bounds.union(next);
            assertEquals(width/2,bounds.centerX(),2);
            assertTrue(bounds.width()>width*.65 && bounds.width()<width*.78);
            for(String row:new String[]{"123","456","789"}) {
                assertEquals(digits.get(row.charAt(0)).top,digits.get(row.charAt(1)).top);
                assertEquals(digits.get(row.charAt(1)).top,digits.get(row.charAt(2)).top);
                assertTrue(digits.get(row.charAt(0)).left<digits.get(row.charAt(1)).left);
                assertTrue(digits.get(row.charAt(1)).left<digits.get(row.charAt(2)).left);
            }
            assertEquals(delete.top,digits.get('0').top);assertEquals(next.top,digits.get('0').top);
            assertTrue(delete.left<digits.get('0').left && digits.get('0').left<next.left);
            for(Rect key:digits.values()) assertTrue("Touch height below 48dp",key.height()>=96);
            progress(layout[0]+" layout and icon pixels passed");
            for(char c:"1234567890".toCharArray()) tap(box(String.valueOf(c)),0);
            expect("1234567890");tap(box("刪除，長按連續刪除"),0);expect("123456789");
            tap(box("刪除，長按連續刪除"),2000);
            long repeatDeadline=SystemClock.uptimeMillis()+15000;
            while(text().length()>=8 && SystemClock.uptimeMillis()<repeatDeadline) SystemClock.sleep(50);
            assertTrue("Delete repeat failed, remaining length: "+text().length(),text().length()<8);
            action(box("下一個"),EditorInfo.IME_ACTION_NEXT);
            input(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_VARIATION_PASSWORD,EditorInfo.IME_ACTION_NEXT);
            tap(box("1"),0);tap(box("2"),0);tap(box("3"),0);expect("123");
            tap(box("刪除，長按連續刪除"),0);expect("12");
            action(box("下一個"),EditorInfo.IME_ACTION_NEXT);
            screenshot(layout[0]+"-pin","下一個");
            progress(layout[0]+" digit, repeat deletion and PIN actions passed");
            checks.put(new JSONObject().put("layout",layout[0]).put("window",layout[1]).put("bounds",bounds.toShortString())
                .put("digit_taps",true).put("backspace_and_repeat",true).put("pin_and_next",true).put("icon_pixels",true));
        }
        int[] types={InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL|InputType.TYPE_NUMBER_FLAG_SIGNED,
            InputType.TYPE_CLASS_PHONE,InputType.TYPE_CLASS_DATETIME};
        String[] samples={"-123.4","+123*#","12:34"},names={"decimal","phone","datetime"};
        for(int i=0;i<types.length;i++) {
            input(types[i],EditorInfo.IME_ACTION_DONE);
            for(char c:samples[i].toCharArray()) tap(box(String.valueOf(c)),0);
            expect(samples[i]);action(box("完成"),EditorInfo.IME_ACTION_DONE);
            screenshot(names[i],"完成");
            progress(names[i]+" symbols and Done passed");
            checks.put(new JSONObject().put("type",names[i]).put("required_symbols_and_done",true));
        }
        for(String name:STORES) assertEquals("Numeric fields changed learning store "+name,learningBefore.get(name),
            instrumentation.getTargetContext().getSharedPreferences(name,0).getAll());
        writeResult(new JSONObject().put("status","passed").put("checks",checks).put("learning_enabled",true).put("learning_unchanged",true)
            .put("device","Android 12 emulator, not a physical Fold7"));
    }
    private void progress(String phase) {
        Bundle status=new Bundle();status.putString("stream","\nNumeric acceptance: "+phase+"\n");
        instrumentation.sendStatus(0,status);
    }
    private void writeResult(JSONObject result) throws Exception {
        try(Writer out=new OutputStreamWriter(new FileOutputStream(new File(evidence,"result.json")),java.nio.charset.StandardCharsets.UTF_8)) {
            out.write(result.toString(2));
        }
    }
    @After public void restore() throws Exception {
        SharedPreferences.Editor edit=preferences.edit().clear();
        for(Map.Entry<String,?> entry:saved.entrySet()) {
            Object v=entry.getValue();String k=entry.getKey();
            if(v instanceof Boolean) edit.putBoolean(k,(Boolean)v);
            else if(v instanceof String) edit.putString(k,(String)v);
            else if(v instanceof Integer) edit.putInt(k,(Integer)v);
            else if(v instanceof Long) edit.putLong(k,(Long)v);
            else if(v instanceof Float) edit.putFloat(k,(Float)v);
            else if(v instanceof Set) edit.putStringSet(k,(Set<String>)v);
        }
        edit.commit();shell("wm size reset");shell("wm density reset");
        if(activity!=null) instrumentation.runOnMainSync(()->activity.finish());
    }
}
