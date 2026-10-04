# Voice input 0.6.13

Restore the earlier direct system-recognizer flow. Default microphone taps call the phone's default speech recognizer immediately; no on-device language preflight or per-attempt offline-model dialog blocks this path. The microphone permission explanation and settings disclose that the provider may process audio online; the keyboard does not store audio.

An optional `voice_offline_only` setting defaults to false. Enabling it preserves on-device recognition, language-support checks, and explicit recovery choices if the provider/model is unavailable. Sensitive editors remain disabled and stale callbacks cannot insert into a different editor.

Based on the integrated 0.6.12 commit `6c87f65e2af40282ea1fa9cccd769db4115dd89f`, preserving swipe selection, English-to-Chinese candidates, Chinese autocorrection, clipboard and strokes.

Tests use a synthetic recognition service registered only in the separately installed instrumentation APK. It does not access microphone/audio/network. The direct-flow test receives synthetic text through the actual system SpeechRecognizer binding, checks no per-attempt confirmation, and checks cancelling prevents a later result insertion. The offline recovery test explicitly enables the setting. The delivered keyboard APK excludes the test service. OEM recognition quality still needs Samsung device testing.
