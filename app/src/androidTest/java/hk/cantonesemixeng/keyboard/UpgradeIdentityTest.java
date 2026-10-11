package hk.cantonesemixeng.keyboard;

import android.content.ComponentName;
import android.content.Context;
import android.content.pm.ActivityInfo;
import android.content.pm.ServiceInfo;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

/** The branding change must preserve installed package data, IME selection and launcher shortcuts. */
@RunWith(AndroidJUnit4.class)
public class UpgradeIdentityTest {
    private Context target() { return InstrumentationRegistry.getInstrumentation().getTargetContext(); }
    @Test public void oldImeComponentLoadsTheRenamedImplementation() throws Exception {
        Context context=target();
        String app=context.getPackageName();
        assertEquals("hk.kaiboard.android",app); // Persistent update identity, deliberately retained.
        ServiceInfo service=context.getPackageManager().getServiceInfo(new ComponentName(app,app+".KaiboardService"),0);
        assertEquals("android.permission.BIND_INPUT_METHOD",service.permission);
        assertTrue(CantoneseMixEngKeyboardService.class.isAssignableFrom(context.getClassLoader().loadClass(service.name)));
        assertEquals("CantoneseMixEng Keyboard",context.getString(R.string.app_name));
    }
    @Test public void existingLauncherShortcutResolvesToTheRenamedSettings() throws Exception {
        Context context=target();String app=context.getPackageName();
        ActivityInfo alias=context.getPackageManager().getActivityInfo(new ComponentName(app,app+".SettingsActivity"),0);
        assertEquals(SettingsActivity.class.getName(),alias.targetActivity);
    }
}
