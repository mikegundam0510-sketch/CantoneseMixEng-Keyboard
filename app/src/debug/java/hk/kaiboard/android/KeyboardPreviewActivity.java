package hk.kaiboard.android;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;

/** Local debug-only input fixture, with no network, messaging, or external side effects. */
public final class KeyboardPreviewActivity extends Activity {
    private EditText input;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24,24,24,24);root.setBackgroundColor(Color.rgb(248,249,251));
        root.setOnApplyWindowInsetsListener((v,i)->{v.setPadding(24,i.getSystemWindowInsetTop()+24,24,i.getSystemWindowInsetBottom()+24);return i;});
        TextView title=new TextView(this);title.setText(hk.kaiboard.android.R.string.app_name);title.setTextSize(22);title.setTextColor(Color.rgb(39,45,54));root.addView(title);
        input=new EditText(this);input.setId(android.view.View.generateViewId());input.setTextSize(24);input.setGravity(Gravity.TOP);
        input.setHint("試打中文、English 或 Emoji…");input.setMinLines(4);
        input.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        root.addView(input,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);
        input.requestFocus();input.postDelayed(()->((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showSoftInput(input,InputMethodManager.SHOW_IMPLICIT),700);
    }
    @Override protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);
        if (intent.hasExtra("test_input_type")) {
            String type = intent.getStringExtra("test_input_type");
            int flags = "uri".equals(type) ? InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI
                : "password".equals(type) ? InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
                : "number".equals(type) ? InputType.TYPE_CLASS_NUMBER
                : InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE;
            input.setInputType(flags);
        }
        if (intent.hasExtra("test_text")) {
            String value = intent.getStringExtra("test_text");
            input.setText("__EMPTY__".equals(value) ? "" : value);
            input.setSelection(input.length()); input.requestFocus();
            InputMethodManager manager = (InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
            manager.restartInput(input); manager.showSoftInput(input,InputMethodManager.SHOW_IMPLICIT);
        }
    }
}

