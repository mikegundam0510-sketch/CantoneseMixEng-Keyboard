package hk.kaiboard.android;

import android.app.AlertDialog;
import android.os.Looper;
import android.view.*;
import android.widget.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28)
public class SettingsFlowTest {
    private ActivityController<SettingsActivity> controller;
    private SettingsActivity activity;
    @Before public void setup() {
        Prefs.get(RuntimeEnvironment.getApplication()).edit().clear().commit();
        controller = Robolectric.buildActivity(SettingsActivity.class).setup(); activity = controller.get();
    }
    @After public void cleanup() { controller.pause().stop().destroy(); }
    private View find(View root, String text) {
        if (root instanceof TextView && text.contentEquals(((TextView)root).getText())) return root;
        if (root instanceof ViewGroup) for (int i = 0; i < ((ViewGroup)root).getChildCount(); i++) {
            View found = find(((ViewGroup)root).getChildAt(i), text); if (found != null) return found;
        }
        return null;
    }
    private void click(View view) {
        view.performClick(); Shadows.shadowOf(Looper.getMainLooper()).idle();
    }
    private AlertDialog addDialog() {
        click(find(activity.getWindow().getDecorView(), "新增／管理短語"));
        click(ShadowAlertDialog.getLatestAlertDialog().getButton(AlertDialog.BUTTON_POSITIVE));
        return ShadowAlertDialog.getLatestAlertDialog();
    }
    private void fill(AlertDialog dialog, String code, String phrase) {
        ViewGroup holder = dialog.findViewById(android.R.id.custom);
        LinearLayout form = (LinearLayout) holder.getChildAt(0);
        ((EditText)form.getChildAt(0)).setText(code); ((EditText)form.getChildAt(1)).setText(phrase);
    }
    @Test public void addingPhraseThroughSettingsPersistsOnlyAuthoredEntry() {
        AlertDialog dialog = addDialog(); fill(dialog, "HK", "香港 🇭🇰");
        click(dialog.getButton(AlertDialog.BUTTON_POSITIVE));
        assertEquals("香港 🇭🇰", CustomPhrases.parse(Prefs.get(activity).getString("custom_phrases", "")).get("hk"));
    }
    @Test public void duplicateShortcutKeepsDialogOpenAndExistingPhrase() {
        Prefs.get(activity).edit().putString("custom_phrases", "hk\t香港").commit();
        AlertDialog dialog = addDialog(); fill(dialog, "hk", "替代內容");
        click(dialog.getButton(AlertDialog.BUTTON_POSITIVE)); assertTrue(dialog.isShowing());
        assertEquals("香港", CustomPhrases.parse(Prefs.get(activity).getString("custom_phrases", "")).get("hk"));
    }
    @Test public void deletionRequiresConfirmationAndPreservesOtherShortcuts() {
        Prefs.get(activity).edit().putString("custom_phrases", "hk\t香港\nss\tSorry").commit();
        click(find(activity.getWindow().getDecorView(), "新增／管理短語"));
        AlertDialog menu = ShadowAlertDialog.getLatestAlertDialog();
        menu.getListView().performItemClick(menu.getListView().getAdapter().getView(0, null, menu.getListView()), 0, 0);
        Shadows.shadowOf(Looper.getMainLooper()).idle();
        click(ShadowAlertDialog.getLatestAlertDialog().getButton(AlertDialog.BUTTON_NEUTRAL));
        assertTrue(CustomPhrases.parse(Prefs.get(activity).getString("custom_phrases", "")).containsKey("hk"));
        click(ShadowAlertDialog.getLatestAlertDialog().getButton(AlertDialog.BUTTON_POSITIVE));
        assertFalse(CustomPhrases.parse(Prefs.get(activity).getString("custom_phrases", "")).containsKey("hk"));
        assertEquals("Sorry", CustomPhrases.parse(Prefs.get(activity).getString("custom_phrases", "")).get("ss"));
    }
}
