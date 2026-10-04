# Voice input 0.6.10

Previous builds always requested `yue-HK` or `en-HK` from the on-device recognizer, then displayed the same generic failure for missing language models, provider errors, and microphone failures. Service availability does not establish that a particular language model is installed.

On Android 13 and later, check recognition support and select an installed Cantonese or English language tag reported by the provider. Prefer HK English, but permit installed UK/US English. Never substitute Mandarin for Cantonese. Services that cannot answer support queries retain the direct recognition path; a 3.5-second support-query timeout prevents a stuck microphone button.

The default remains `createOnDeviceSpeechRecognizer`. If the on-device service/model cannot be used, an attached keyboard dialog offers cancel, voice settings, or **今次用系統語音**. Only that explicit per-attempt choice calls `createSpeechRecognizer`; the provider may process audio online. No consent or cloud preference is persisted. The keyboard never stores audio. Permission, microphone availability, silence, provider busy/rate limits, and language/model errors have separate messages.

Cancel pending support checks and dialogs when input finishes or switches. Ignore stale recognition/support callbacks, and insert results only into the original live non-sensitive editor. Password/private and numeric fields keep their existing speech restrictions.

Validation: VoicePolicy regression tests cover provider language tags, English fallback, refusal to substitute Mandarin, and error distinctions. CI compiles the application, runs all JVM tests, runs Android lint, and verifies the APK signature. Samsung Fold/One UI recognition provider availability, attached-dialog interaction, permission denial, switching editor during support checks, and actual Cantonese/English transcription still require physical-device checks. An emulator cannot establish OEM model support.

This branch is based on 0.6.9 and changes voice input only. Other ongoing feature work is not part of this fix.
