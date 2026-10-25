package hk.cantonesemixeng.keyboard;

import android.content.Context;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.json.JSONObject;
import java.io.File;
import java.nio.file.Files;
import java.security.MessageDigest;
import static org.junit.Assert.*;

/** Compare real installed preference files across adb install -r, without exposing their contents. */
public class InstalledDataRetentionTest {
    @Test public void installedUpdatePreservesPreferenceFiles() throws Exception {
        String expected=InstrumentationRegistry.getArguments().getString("expected_preferences");
        Assume.assumeNotNull(expected);
        Context target=InstrumentationRegistry.getInstrumentation().getTargetContext();
        assertEquals("hk.kaiboard.android",target.getPackageName());
        assertEquals(47,target.getPackageManager().getPackageInfo(target.getPackageName(),0).versionCode);
        JSONObject hashes=new JSONObject(expected);assertTrue(hashes.length()>0);
        for(java.util.Iterator<String> names=hashes.keys();names.hasNext();) {
            String name=names.next();assertTrue(name.matches("[a-z_]+\\.xml"));
            File file=new File(new File(target.getDataDir(),"shared_prefs"),name);
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file.toPath()));
            StringBuilder hex=new StringBuilder();for(byte b:digest)hex.append(String.format("%02x",b&255));
            assertEquals(name,hashes.getString(name),hex.toString());
        }
    }
}
