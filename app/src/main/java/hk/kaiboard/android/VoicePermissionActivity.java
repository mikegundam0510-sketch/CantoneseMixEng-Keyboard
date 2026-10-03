package hk.kaiboard.android;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.widget.Toast;

/** Permission is requested from an Activity; audio is captured only after a subsequent mic tap. */
public final class VoicePermissionActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) { finish(); return; }
        if (state == null) new AlertDialog.Builder(this)
            .setTitle("語音輸入")
            .setMessage("使用手機嘅語音辨識服務，可能需要網絡並將語音交畀服務供應商處理。允許咪高峰後，返回輸入框再撳咪開始。")
            .setPositiveButton("繼續", (dialog, which) -> requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1))
            .setNegativeButton("取消", (dialog, which) -> finish())
            .setOnCancelListener(dialog -> finish()).show();
        else finish();
    }
    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        Toast.makeText(this, results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED ?
            "已允許，返回輸入框再撳咪開始" : "未允許咪高峰；可於系統 App 設定開啟", Toast.LENGTH_LONG).show();
        finish();
    }
}
