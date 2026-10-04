# Input privacy

Reviewed source: development branch based on 05fd15e3656518e6abf846e0578ce2822aa4126b.

The application manifest has no INTERNET permission. Production code has no HTTP client,
analytics SDK, remote endpoint, input-text logging or recording-file writer. The debug
log contains window inset dimensions only. The IME service requires BIND_INPUT_METHOD.
Cloud backup and device transfer exclude all application data.

Automatic word learning and recent Emoji history are disabled by default. On the first
start after this change, existing automatically learned Chinese/English entries and
recent Emoji are cleared. Explicitly added custom words and pinned candidates remain.
Users can opt in to local learning in settings; this saves selected words and usage
counts, and may include sensitive words entered in an ordinary text box. Learning
should remain off when handling confidential content. The app cannot determine whether
arbitrary plain text is confidential.

Password variants, email, URI, person-name, postal-address, numeric, phone, date/time,
TYPE_NULL and NO_PERSONALIZED_LEARNING editors never use or update personal history.
They also do not read surrounding text for language-model context or start voice input.
Ordinary-field context is used temporarily for offline suggestions, not written to disk.
Clipboard contents are accessed only for an explicit paste action, with no clipboard
listener or history store.

Voice input defaults to Android's on-device recognition API (API 31+), only after a
user tap and microphone permission. If a service or language model is unavailable,
the user may explicitly choose the network-capable system recognizer for that attempt
in a keyboard dialog. The dialog discloses that the provider may process audio online.
There is no automatic network fallback or saved consent; every new microphone tap
starts with on-device recognition. The app does not save audio. The recognition service and operating system remain separate
components, outside this source review. Galaxy AI shortcuts only explain how to use
Samsung's tools; choosing those tools is subject to Samsung's own data handling.

Source review is not an absolute guarantee against vulnerabilities or compromised
devices/services. Android's keyboard-enablement warning describes the access afforded
to an input method; it is not evidence that this app records or transmits keystrokes.

Validation includes unit tests for sensitive editor policies and Android instrumentation
tests for fresh-install defaults, history removal on upgrade, preservation of manual
words/settings, and persistence of an explicit subsequent opt-in.
