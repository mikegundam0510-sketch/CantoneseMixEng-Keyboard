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
  SystemClock.sleep(500);
  Rect previous=null;int stable=0;
  for(int tries=0;tries<40;tries++){
   for(AccessibilityWindowInfo window:instrumentation.getUiAutomation().getWindows()){
    AccessibilityNodeInfo node=find(window.getRoot(),desc);
    if(node!=null){Rect bounds=new Rect();node.getBoundsInScreen(bounds);if(bounds.width()>0&&bounds.height()>0){stable=bounds.equals(previous)?stable+1:0;previous=bounds;if(stable>=2)return bounds;}}
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
  if(dx==0){
   MotionEvent event=MotionEvent.obtain(down,down,MotionEvent.ACTION_DOWN,x,y,0);event.setSource(InputDevice.SOURCE_TOUCHSCREEN);assertTrue(instrumentation.getUiAutomation().injectInputEvent(event,true));event.recycle();SystemClock.sleep(50);
   event=MotionEvent.obtain(down,SystemClock.uptimeMillis(),MotionEvent.ACTION_UP,x,y,0);event.setSource(InputDevice.SOURCE_TOUCHSCREEN);assertTrue(instrumentation.getUiAutomation().injectInputEvent(event,true));event.recycle();instrumentation.waitForIdleSync();SystemClock.sleep(300);return;
  }
  for(int i=0;i<=12;i++){
   int action=i==0?MotionEvent.ACTION_DOWN:i==12?MotionEvent.ACTION_UP:MotionEvent.ACTION_MOVE;
   MotionEvent event=MotionEvent.obtain(down,SystemClock.uptimeMillis(),action,x+dx*i/12f,y,0);
   event.setSource(InputDevice.SOURCE_TOUCHSCREEN);
   assertTrue(instrumentation.getUiAutomation().injectInputEvent(event,true));event.recycle();SystemClock.sleep(20);
  }
  instrumentation.waitForIdleSync();SystemClock.sleep(200);
 }

 private java.io.Reader asset(String name)throws Exception{return new java.io.InputStreamReader(instrumentation.getTargetContext().getAssets().open(name),java.nio.charset.StandardCharsets.UTF_8);}
 private String[] autoFixture()throws Exception{
  DictionaryEngine d=new DictionaryEngine(asset("cangjie5.base.dict.yaml"),asset("english.txt"),asset("character_frequencies.tsv"));
  QuickDecoder decoder=new QuickDecoder(d,asset("quick_phrases.tsv"),asset("hk_phrases.tsv"),asset("cantonese_phrases.tsv"),OfflineLanguageModel.load(instrumentation.getTargetContext().getAssets().open("language_model.b64")));
  QuickTypos repairs=new QuickTypos(d,decoder);EnglishEngine english=new EnglishEngine(asset("english.txt"));
  for(String context:new String[]{"我想見","我想食","我想飲","研究","唔","香","開","多"})
   for(String source:new String[]{"oa","oz","oq","iz","zz","pp","qx","wz","xx","za","xs","xz","qa","qs","qz","gq","fq","xq","zq","bz","od","vr","mm","qo","ha","rr","ab","on","of","my"}){
    if(english.likelyEnglish(source,java.util.Collections.emptyList()))continue;
    java.util.List<InputCandidate> baseline=new java.util.ArrayList<>();for(String word:d.quickCandidates(source))baseline.add(InputCandidate.chinese(d,source,word));
    InputCandidate winner=ChineseAutocorrect.choose(source,context,baseline,repairs.suggest(source,baseline.subList(0,Math.min(3,baseline.size())),context),text->decoder.languageScore(context,text));
    if(winner!=null&&decoder.supportsCorrection(context,winner.text))return new String[]{context,source,winner.text};
   }
  throw new AssertionError("No confidence-qualified autocorrect fixture");
 }
 @Test public void actualImeGesturesOnCoverAndUnfolded()throws Exception{
  shell("settings put secure show_ime_with_hard_keyboard 1");
  AccessibilityServiceInfo serviceInfo=instrumentation.getUiAutomation().getServiceInfo();
  serviceInfo.flags|=AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
  instrumentation.getUiAutomation().setServiceInfo(serviceInfo);
  String[] repair=autoFixture();
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
   screenshot("can-"+size);Rect translated=key("英轉中候選：可以");drag(translated,0);
   main(()->assertEquals("可以",edit.getText().toString()));
   main(()->{edit.setText("");edit.setSelection(0);((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).restartInput(edit);});
   SystemClock.sleep(300);
   for(String desc:new String[]{"O，人","F，火","C，金","A，日","N，弓"})drag(key(desc),0);
   Rect mixed=key("英轉中候選：你可以");drag(mixed,0);
   main(()->assertEquals("你可以",edit.getText().toString()));
   main(()->{edit.setText(repair[0]);edit.setSelection(edit.length());((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).restartInput(edit);});
   SystemClock.sleep(500);
   String radicals="日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重";
   for(char c:repair[1].toCharArray())drag(key(Character.toUpperCase(c)+"，"+radicals.charAt(c-'a')),0);
   drag(key("空白鍵，左右滑動移動游標"),0);
   main(()->assertEquals(repair[0]+repair[2],edit.getText().toString()));
   screenshot("autocorrect-"+size);
   drag(key("刪除，長按連續刪除"),0);
   main(()->assertEquals(repair[0]+repair[1],edit.getText().toString()));

   main(()->{edit.setText("");edit.setSelection(0);((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).restartInput(edit);});
   SystemClock.sleep(300);drag(key("切換中英文，長按選擇系統鍵盤"),0);
   for(String desc:new String[]{"英文字母 C","英文字母 A","英文字母 N"})drag(key(desc),0);
   drag(key("英轉中候選：可以"),0);main(()->assertEquals("可以",edit.getText().toString()));
  }
 }
}
