package hk.kaiboard.android;

import android.text.InputType;
import android.view.inputmethod.EditorInfo;

final class InputPolicy {
    static boolean isSecure(int inputType) {
        int type = inputType & InputType.TYPE_MASK_CLASS;
        int variation = inputType & InputType.TYPE_MASK_VARIATION;
        return type == InputType.TYPE_CLASS_TEXT && (variation == InputType.TYPE_TEXT_VARIATION_PASSWORD
            || variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD || variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD)
            || type == InputType.TYPE_CLASS_NUMBER && variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD;
    }
    static boolean noLearning(int inputType, int imeOptions) {
        int type = inputType & InputType.TYPE_MASK_CLASS;
        int variation = inputType & InputType.TYPE_MASK_VARIATION;
        return isSecure(inputType) || (imeOptions & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) != 0
            || type == InputType.TYPE_NULL || type == InputType.TYPE_CLASS_NUMBER
            || type == InputType.TYPE_CLASS_PHONE || type == InputType.TYPE_CLASS_DATETIME
            || type == InputType.TYPE_CLASS_TEXT && (variation == InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
                || variation == InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS
                || variation == InputType.TYPE_TEXT_VARIATION_URI
                || variation == InputType.TYPE_TEXT_VARIATION_PERSON_NAME
                || variation == InputType.TYPE_TEXT_VARIATION_POSTAL_ADDRESS);
    }
}
