package hk.kaiboard.android;

import android.app.*;
import android.content.*;
import android.graphics.Rect;
import android.os.*;
import android.view.*;
import android.view.accessibility.*;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.view.inputmethod.*;
import android.widget.*;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import static org.junit.Assert.*;

public class SwipeSelectionTest {
 private final Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
 private Activity activity;
 private EditText edit;
 private InputConnection connection;
 private SwipeSelectionController selection;
 @Before public void setup()throws Exception{
  activity=instrumentation.startActivitySync(new Intent(instrumentation.getTargetContext(),KeyboardPreviewActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
  instrumentation.runOnMainSync(()->{edit=new EditText(activity);activity.setContentView(edit);edit.requestFocus();connection=edit.onCreateInputConnection(new EditorInfo());selection=new SwipeSelectionController();});
 }
 @After public void finish(){instrumentation.runOnMainSync(()->{selection.reset();activity.finish();});}
 private void main(Runnable r){instrumentation.runOnMainSync(r);instrumentation.waitForIdleSync();}
 @Test public void reverseShrinksAndStopsAtAnchorAcrossSeparateSwipes(){
  main(()->{
   edit.setText("甲乙丙丁戊己庚辛");edit.setSelection(6);assertTrue(selection.begin(connection));
   selection.move(connection,-2);assertEquals(6,edit.getSelectionStart());assertEquals(4,edit.getSelectionEnd());
   assertTrue(selection.begin(connection));selection.move(connection,1);assertEquals(5,edit.getSelectionEnd());
   selection.move(connection,8);assertEquals(6,edit.getSelectionStart());assertEquals(6,edit.getSelectionEnd());
   selection.move(connection,2);assertEquals(6,edit.getSelectionEnd());
   assertTrue(selection.begin(connection));selection.move(connection,1);assertEquals(7,edit.getSelectionEnd());
  });
 }
 @Test public void rightSelectionAndExternalCursorChange(){
  main(()->{
   edit.setText("甲乙丙丁戊");edit.setSelection(1);assertTrue(selection.begin(connection));selection.move(connection,2);
   assertEquals(1,edit.getSelectionStart());assertEquals(3,edit.getSelectionEnd());
   assertTrue(selection.begin(connection));selection.move(connection,-9);assertEquals(1,edit.getSelectionStart());assertEquals(1,edit.getSelectionEnd());
   edit.setSelection(4);assertTrue(selection.begin(connection));selection.move(connection,-1);
   assertEquals(4,edit.getSelectionStart());assertEquals(3,edit.getSelectionEnd());
  });
 }
 @Test public void emojiCombiningMarksAndTextLimitsStayWhole(){
  main(()->{
   String family="👨‍👩‍👧‍👦";edit.setText("A"+family+"e\u0301港");edit.setSelection(edit.length());assertTrue(selection.begin(connection));
   selection.move(connection,-1);assertEquals(edit.length()-1,edit.getSelectionEnd());
   selection.move(connection,-1);assertEquals(1+family.length(),edit.getSelectionEnd());
   selection.move(connection,-1);assertEquals(1,edit.getSelectionEnd());
   selection.move(connection,-20);assertEquals(0,edit.getSelectionEnd());
   selection.move(connection,20);assertEquals(edit.length(),edit.getSelectionEnd());assertEquals(edit.length(),edit.getSelectionStart());
  });
 }
 private void shell(String command)throws Exception{
  try(ParcelFileDescriptor descriptor=instrumentation.getUiAutomation().executeShellCommand(command);
      java.io.InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(descriptor)){byte[] b=new byte[1024];while(in.read(b)!=-1){}}
 }
 private AccessibilityNodeInfo find(AccessibilityNodeInfo node,String desc){
  if(node==null)return null;
  if(desc.contentEquals(node.getContentDescription()==null?"":node.getContentDescription()) || desc.contentEquals(node.getText()==null?"":node.getText()))return node;
  for(int i=0;i<node.getChildCount();i++){AccessibilityNodeInfo found=find(node.getChild(i),desc);if(found!=null)return found;}
  return null;
 }
 private Rect key(String desc)throws Exception{
  for(int tries=0;tries<40;tries++){
   for(AccessibilityWindowInfo window:instrumentation.getUiAutomation().getWindows()){
    AccessibilityNodeInfo node=find(window.getRoot(),desc);
    if(node!=null){Rect bounds=new Rect();node.getBoundsInScreen(bounds);if(bounds.width()>0&&bounds.height()>0)return bounds;}
   }
   Thread.sleep(250);
  }
  screenshot("missing-key");
  throw new AssertionError("IME key missing: "+desc);
 }
 private void screenshot(String name)throws Exception{
  android.graphics.Bitmap bitmap=instrumentation.getUiAutomation().takeScreenshot();
  try(java.io.FileOutputStream out=new java.io.FileOutputStream(new java.io.File(instrumentation.getTargetContext().getExternalFilesDir(null),name+".png"))){bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();
 }
 private void drag(Rect start,int dx){
  long down=SystemClock.uptimeMillis();float x=start.exactCenterX(),y=start.exactCenterY();
  for(int i=0;i<=12;i++){
   int action=i==0?MotionEvent.ACTION_DOWN:i==12?MotionEvent.ACTION_UP:MotionEvent.ACTION_MOVE;
   MotionEvent event=MotionEvent.obtain(down,SystemClock.uptimeMillis(),action,x+dx*i/12f,y,0);
   event.setSource(InputDevice.SOURCE_TOUCHSCREEN);
   assertTrue(instrumentation.getUiAutomation().injectInputEvent(event,true));event.recycle();SystemClock.sleep(20);
  }
  instrumentation.waitForIdleSync();SystemClock.sleep(200);
 }
 @Test public void actualImeGesturesOnCoverAndUnfolded()throws Exception{
  shell("settings put secure show_ime_with_hard_keyboard 1");
  AccessibilityServiceInfo serviceInfo=instrumentation.getUiAutomation().getServiceInfo();
  serviceInfo.flags|=AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
  instrumentation.getUiAutomation().setServiceInfo(serviceInfo);
  for(String size:new String[]{"720x1600","1440x1800"}){
   main(()->activity.finish());
   shell("wm size "+size);shell("wm density 320");SystemClock.sleep(700);
   activity=instrumentation.startActivitySync(new Intent(instrumentation.getTargetContext(),KeyboardPreviewActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
   main(()->{
    edit=new EditText(activity);edit.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
    activity.setContentView(edit);edit.setText("甲乙丙丁戊己庚辛壬癸ABC");edit.setSelection(6);edit.requestFocus();
   });
   SystemClock.sleep(700);
   main(()->{InputMethodManager manager=(InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);manager.restartInput(edit);manager.showSoftInput(edit,InputMethodManager.SHOW_FORCED);});
   Rect g=key("G，土");drag(g,-180);
   main(()->{assertEquals(6,edit.getSelectionStart());assertTrue(edit.getSelectionEnd()<6);assertEquals("甲乙丙丁戊己庚辛壬癸ABC",edit.getText().toString());});
   screenshot("selection-"+size);
   drag(g,260);
   main(()->{assertEquals(6,edit.getSelectionStart());assertEquals(6,edit.getSelectionEnd());});
   drag(g,180);
   main(()->{assertEquals(6,edit.getSelectionStart());assertTrue(edit.getSelectionEnd()>6);});
   drag(g,-260);
   main(()->{assertEquals(6,edit.getSelectionStart());assertEquals(6,edit.getSelectionEnd());});
   main(()->{edit.setText("");edit.setSelection(0);((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).restartInput(edit);});
   SystemClock.sleep(400);
   for(String desc:new String[]{"C，金","A，日","N，弓"})drag(key(desc),0);
   Rect translated=key("英轉中候選：可以");screenshot("can-"+size);drag(translated,0);
   main(()->assertEquals("可以",edit.getText().toString()));
   main(()->{edit.setText("");edit.setSelection(0);((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).restartInput(edit);});
   SystemClock.sleep(300);
   for(String desc:new String[]{"O，人","F，火","C，金","A，日","N，弓"})drag(key(desc),0);
   Rect mixed=key("英轉中候選：你可以");drag(mixed,0);
   main(()->assertEquals("你可以",edit.getText().toString()));
   main(()->{edit.setText("");edit.setSelection(0);((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).restartInput(edit);});
   SystemClock.sleep(300);drag(key("切換中英文，長按選擇系統鍵盤"),0);
   for(String desc:new String[]{"英文字母 C","英文字母 A","英文字母 N"})drag(key(desc),0);
   drag(key("英轉中候選：可以"),0);main(()->assertEquals("可以",edit.getText().toString()));
  }
 }
}
