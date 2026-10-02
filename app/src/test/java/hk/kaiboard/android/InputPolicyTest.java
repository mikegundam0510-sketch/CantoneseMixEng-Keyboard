package hk.kaiboard.android;

import android.text.InputType;
import android.view.inputmethod.EditorInfo;
import org.junit.Test;
import static org.junit.Assert.*;

public class InputPolicyTest {
    @Test public void allPasswordVariationsDisableLearning() {
        int[] types = {
            InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD,
            InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD,
            InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD,
            InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD
        };
        for (int type : types) {
            assertTrue(InputPolicy.isSecure(type));
            assertTrue(InputPolicy.noLearning(type, 0));
        }
    }
    @Test public void privateEditorSuppressesLearningEvenForPlainText() {
        assertTrue(InputPolicy.noLearning(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING | EditorInfo.IME_ACTION_SEND));
        assertFalse(InputPolicy.noLearning(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_SEND));
    }
    @Test public void ordinaryNumberAndEmailAreNotPasswords() {
        assertFalse(InputPolicy.isSecure(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL));
        assertFalse(InputPolicy.isSecure(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS));
    }
}
