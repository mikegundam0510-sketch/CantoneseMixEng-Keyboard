package hk.kaiboard.android;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.*;
import android.content.*;
import android.graphics.Rect;
import android.os.*;
import android.text.*;
import android.view.*;
import android.view.accessibility.*;
import android.widget.EditText;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.*;
import org.junit.runner.RunWith;
import org.json.*;
import java.io.*;
import java.lang.reflect.Field;
import java.util.*;
import static org.junit.Assert.*;

/** Actual IME touch injection and editor acknowledgements, without per-key UI polling. */
@RunWith(AndroidJUnit4.class)
public class TypingFluencyTest {
    private final Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
    private final UiAutomation automation=instrumentation.getUiAutomation();
    private Activity activity;
    private EditText editor;
    private SharedPreferences preferences;
    private Map<String,?> saved;
    private final Map<Character,Rect> keys=new HashMap<>();
    private final List<Sample> pending=new ArrayList<>();
    private final List<Long> latencies=new ArrayList<>();
    private int acknowledged;
    private Rect deleteKey;
    private static final String CONTEXT="聽日要返工，";
    private static final String CODE="onardrjjjhionardrjjjyeomm";
    private static class Sample {
        final String text;final long time;
        Sample(String text,long time){this.text=text;this.time=time;}
    }
    @Before public void setup() throws Exception {
        preferences=Prefs.get(instrumentation.getTargetContext());saved=preferences.getAll();
        preferences.edit().putBoolean("quick",true).putBoolean("continuous",true)
            .putBoolean("english",false).putBoolean("chinese_autocorrect",false)
            .putBoolean("context_candidates",true).putBoolean("learning",false)
            .putBoolean("semantic_candidates",false).commit();
        AccessibilityServiceInfo info=automation.getServiceInfo();
        info.flags|=AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
        automation.setServiceInfo(info);
        Intent intent=new Intent(instrumentation.getTargetContext(),KeyboardPreviewActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);intent.putExtra("test_text",CONTEXT);
        activity=instrumentation.startActivitySync(intent);
        Field field=KeyboardPreviewActivity.class.getDeclaredField("input");field.setAccessible(true);
        editor=(EditText)field.get(activity);
        instrumentation.runOnMainSync(()->editor.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void afterTextChanged(Editable e){}
            public void onTextChanged(CharSequence s,int start,int before,int count){
                synchronized(pending){
                    if(acknowledged<pending.size()&&s.toString().equalsIgnoreCase(pending.get(acknowledged).text)){
                        latencies.add(SystemClock.uptimeMillis()-pending.get(acknowledged).time);acknowledged++;
                    }
                }
            }
        }));
        // am instrument stops the target process, including its previously bound IME.
        // Re-select after the instrumented activity is attached so the service is bound again.
        capture("ime reset","ime-reset.txt");
        capture("ime enable hk.kaiboard.android/.KaiboardService","ime-enable.txt");
        capture("ime set hk.kaiboard.android/.KaiboardService","ime-select.txt");
        instrumentation.runOnMainSync(()->{
            editor.requestFocus();
            var manager=(android.view.inputmethod.InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);
            manager.restartInput(editor);
            manager.showSoftInput(editor,android.view.inputmethod.InputMethodManager.SHOW_FORCED);
        });
        for(char c:CODE.toCharArray())if(!keys.containsKey(c))keys.put(c,find("英文字母 "+Character.toUpperCase(c)));
        deleteKey=find("刪除，長按連續刪除");
    }
    private Rect find(String prefix) throws Exception {
        long end=SystemClock.uptimeMillis()+15000;
        while(SystemClock.uptimeMillis()<end){
            for(AccessibilityWindowInfo window:automation.getWindows()){
                AccessibilityNodeInfo root=window.getRoot();
                Rect result=search(root,prefix);if(result!=null)return result;
            }
            SystemClock.sleep(100);
        }
        capture("dumpsys input_method","ime-unavailable.txt");
        capture("dumpsys activity activities","activity-unavailable.txt");
        throw new AssertionError("IME key unavailable: "+prefix);
    }
    private Rect search(AccessibilityNodeInfo node,String prefix){
        if(node==null)return null;
        CharSequence description=node.getContentDescription();
        if(description!=null&&description.toString().startsWith(prefix)){
            Rect bounds=new Rect();node.getBoundsInScreen(bounds);if(!bounds.isEmpty())return bounds;
        }
        for(int i=0;i<node.getChildCount();i++){Rect found=search(node.getChild(i),prefix);if(found!=null)return found;}
        return null;
    }
    private void tap(Rect bounds,String expected){
        long now=SystemClock.uptimeMillis();
        synchronized(pending){pending.add(new Sample(expected,now));}
        MotionEvent down=MotionEvent.obtain(now,now,MotionEvent.ACTION_DOWN,bounds.centerX(),bounds.centerY(),0);
        MotionEvent up=MotionEvent.obtain(now,now+1,MotionEvent.ACTION_UP,bounds.centerX(),bounds.centerY(),0);
        down.setSource(InputDevice.SOURCE_TOUCHSCREEN);up.setSource(InputDevice.SOURCE_TOUCHSCREEN);
        try{assertTrue(automation.injectInputEvent(down,false));assertTrue(automation.injectInputEvent(up,false));}
        finally{down.recycle();up.recycle();}
        SystemClock.sleep(25);
    }
    private void awaitAcknowledgements() {
        long end=SystemClock.uptimeMillis()+8000;
        while(SystemClock.uptimeMillis()<end){synchronized(pending){if(acknowledged==pending.size())return;}SystemClock.sleep(10);}
        synchronized(pending){assertEquals("Every touch must reach the editor in order",pending.size(),acknowledged);}
    }
    private void capture(String command,String filename) throws IOException {
        try(var descriptor=automation.executeShellCommand(command);
            var input=new android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor);
            var output=new FileOutputStream(new File(activity.getExternalFilesDir(null),filename))){
            byte[] bytes=new byte[16384];int n;while((n=input.read(bytes))!=-1)output.write(bytes,0,n);
        }
    }
    private boolean modelMapped() throws IOException {
        try(var in=new BufferedReader(new FileReader("/proc/self/maps"))){
            String line;while((line=in.readLine())!=null)if(line.contains(".gguf"))return true;
        }
        return false;
    }
    private JSONObject phase(String name,boolean semantic,boolean allowColdLoad) throws Exception {
        capture("dumpsys gfxinfo hk.kaiboard.android reset",name+"-frames-reset.txt");
        preferences.edit().putBoolean("semantic_candidates",semantic).commit();
        synchronized(pending){pending.clear();latencies.clear();acknowledged=0;}
        // This warm-up opens a real exact-candidate request. A pause lets loading overlap subsequent typing.
        String code="";
        for(int i=0;i<8;i++){code+=CODE.charAt(i);tap(keys.get(CODE.charAt(i)),CONTEXT+code);}
        awaitAcknowledgements();
        SystemClock.sleep(allowColdLoad?650:2500);
        for(int i=8;i<CODE.length();i++){code+=CODE.charAt(i);tap(keys.get(CODE.charAt(i)),CONTEXT+code);}
        awaitAcknowledgements();
        for(int i=CODE.length();i>0;i--)tap(deleteKey,CONTEXT+CODE.substring(0,i-1));
        awaitAcknowledgements();
        List<Long> measured; synchronized(pending){measured=new ArrayList<>(latencies);}
        Collections.sort(measured);
        Debug.MemoryInfo memory=new Debug.MemoryInfo();Debug.getMemoryInfo(memory);
        JSONObject result=new JSONObject();result.put("phase",name);result.put("touches",measured.size());
        result.put("missing_touches",0);result.put("p50_ms",measured.get(measured.size()/2));
        result.put("p95_ms",measured.get((int)Math.ceil(measured.size()*0.95)-1));
        result.put("max_ms",measured.get(measured.size()-1));result.put("process_pss_kib",memory.getTotalPss());
        result.put("semantic_requested",semantic);result.put("model_bundled",BuildConfig.SEMANTIC_MODEL);
        result.put("model_mapped",modelMapped());
        capture("dumpsys gfxinfo hk.kaiboard.android framestats",name+"-frames.txt");
        return result;
    }
    @Test public void actualImeKeepsEveryRapidTypingAndDeleteTouch() throws Exception {
        JSONArray phases=new JSONArray();
        JSONObject baseline=phase("basic",false,false);phases.put(baseline);
        JSONObject cold=phase("semantic_cold",true,true);phases.put(cold);
        JSONObject warm=phase("semantic_warm",true,false);phases.put(warm);
        var manager=(ActivityManager)activity.getSystemService(Context.ACTIVITY_SERVICE);
        var memory=new ActivityManager.MemoryInfo();manager.getMemoryInfo(memory);
        JSONObject report=new JSONObject();report.put("phases",phases);report.put("total_memory_bytes",memory.totalMem);
        report.put("available_memory_bytes",memory.availMem);report.put("model_budget_available",SemanticPolicy.budget(memory.totalMem,memory.availMem,memory.lowMemory)!=null);
        report.put("hardware_note","Android emulator; not a physical Fold 7 measurement");
        try(var out=new FileOutputStream(new File(activity.getExternalFilesDir(null),"typing-fluency.json"))){
            out.write(report.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
        // Relative and absolute gates allow emulator variance but reject visible input stalls.
        long limit=Math.max(150,baseline.getLong("p95_ms")*2+50);
        assertTrue("Cold model loading delays typing",cold.getLong("p95_ms")<=limit);
        assertTrue("Warm inference delays typing",warm.getLong("p95_ms")<=limit);
        for(int i=0;i<phases.length();i++)assertTrue("Visible keyboard stall",phases.getJSONObject(i).getLong("max_ms")<1000);
    }
    @After public void teardown(){
        if(activity!=null){
            try{capture("dumpsys meminfo hk.kaiboard.android","final-memory.txt");}
            catch(IOException unavailable){ /* Timing assertions remain authoritative. */ }
            instrumentation.runOnMainSync(()->activity.finish());
        }
        if(preferences==null||saved==null)return;
        SharedPreferences.Editor edit=preferences.edit().clear();
        for(var item:saved.entrySet()){
            Object value=item.getValue();String key=item.getKey();
            if(value instanceof Boolean)edit.putBoolean(key,(Boolean)value);
            else if(value instanceof String)edit.putString(key,(String)value);
            else if(value instanceof Integer)edit.putInt(key,(Integer)value);
            else if(value instanceof Long)edit.putLong(key,(Long)value);
            else if(value instanceof Float)edit.putFloat(key,(Float)value);
            else if(value instanceof Set)edit.putStringSet(key,(Set<String>)value);
        }
        edit.commit();
    }
}
