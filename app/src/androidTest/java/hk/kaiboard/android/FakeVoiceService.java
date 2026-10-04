package hk.kaiboard.android;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.RemoteException;
import android.speech.RecognitionService;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import java.util.ArrayList;
import java.util.Collections;

/** Test APK only: synthetic results, no microphone, network or audio files. */
public final class FakeVoiceService extends RecognitionService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private Runnable pending;
    @Override protected void onStartListening(Intent intent, Callback callback) {
        try {
            if (intent.getBooleanExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)) {
                callback.error(SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED); return;
            }
            callback.readyForSpeech(new Bundle());
            pending = () -> {
                Bundle results = new Bundle();
                results.putStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION,
                    new ArrayList<>(Collections.singletonList("語音測試")));
                try { callback.results(results); } catch (RemoteException ignored) { }
                pending = null;
            };
            handler.postDelayed(pending, 6000);
        } catch (RemoteException ignored) { }
    }
    @Override protected void onCancel(Callback callback) {
        if (pending != null) handler.removeCallbacks(pending);
        pending = null;
    }
    @Override protected void onStopListening(Callback callback) { onCancel(callback); }
    @Override public void onDestroy() { handler.removeCallbacksAndMessages(null); super.onDestroy(); }
}
