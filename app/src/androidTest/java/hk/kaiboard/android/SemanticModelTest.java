package hk.kaiboard.android;

import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import static org.junit.Assert.*;
import java.io.*;
import java.util.*;

public class SemanticModelTest {
    @Test public void realNativeModelUsesEarlierContextWithoutGeneratingNewCandidates() throws Exception {
        Assume.assumeTrue(BuildConfig.SEMANTIC_MODEL);
        var app=InstrumentationRegistry.getInstrumentation().getTargetContext();
        Assume.assumeTrue(new SemanticRanker(app).budget()!=null);
        File weights=new File(app.getCacheDir(),"semantic-test.gguf");
        try(var in=app.getAssets().open("semantic-model.gguf");var out=new FileOutputStream(weights)) {
            byte[] buffer=new byte[65536];int count;
            while((count=in.read(buffer))!=-1)out.write(buffer,0,count);
        }
        try(var model=SemanticNative.load(weights.getAbsolutePath(),2)) {
            assertNotNull("Bundled native inference must load",model);
            List<String> values=Arrays.asList("有時間","冇時間","希時間","有時暑");
            long start=System.nanoTime();
            float[] scores=model.rank(SemanticPrompt.build("我星期六日都返足成日工，咁即係",values),values.size(),60000);
            assertNotNull(scores);assertEquals(values.size(),scores.length);
            List<String> ordered=SemanticPolicy.promote(values,values,scores);
            assertEquals("冇時間",ordered.get(0));assertEquals(new HashSet<>(values),new HashSet<>(ordered));
            // Only aggregate timing is recorded. Never log the editor prompt or scores.
            android.util.Log.i("SemanticAcceptance","native_inference_ms="+(System.nanoTime()-start)/1000000);
        } finally { weights.delete(); }
    }
}
