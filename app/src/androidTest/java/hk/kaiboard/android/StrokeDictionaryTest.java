package hk.kaiboard.android;
import org.junit.Test;
import androidx.test.platform.app.InstrumentationRegistry;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.Assert.*;
public class StrokeDictionaryTest {
 @Test public void bundledTraditionalAndHongKongCodes()throws Exception{
  android.content.res.AssetManager assets=InstrumentationRegistry.getInstrumentation().getTargetContext().getAssets();
  StrokeEngine engine=new StrokeEngine(new InputStreamReader(assets.open("stroke.tsv"),StandardCharsets.UTF_8));
  String[][] cases={{"馬","hshhsznnnn"},{"馬","shhhsznnnn"},{"香","phspnszhh"},{"港","nnnhsshpnzhz"},{"學","pshhpnpnzhhnzzsh"},{"我","phshzpn"},{"你","pspzspn"},{"係","pspzznzpn"},{"唔","szhhszhszh"},{"喺","szhpspzznspn"}};
  for(String[] c:cases)assertTrue(c[0]+" missing",engine.lookup(c[1],32).contains(c[0]));
  assertTrue(engine.lookup("*shhsznnnn",32).contains("馬"));
  assertFalse(Arrays.asList(assets.list("")).contains("handwriting-zh_TW.model"));
  assertFalse(Arrays.asList(assets.list("")).contains("handwriting-shapes.bin"));
 }
}
