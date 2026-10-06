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

Voice input starts the phone's default recognition service directly after a microphone
button tap and permission grant. That external service may process audio online. This
behavior restores the earlier user-requested direct voice flow; no offline-model or
per-attempt provider confirmation dialog blocks the default path. Settings and the
first microphone-permission explanation disclose the provider's possible network use.
Users may explicitly enable `voice_offline_only` to require Android's on-device
recognition API. In that mode, unavailable models produce recovery choices and never
silently switch to online recognition. The keyboard does not save audio. The recognition
service and operating system remain separate
components, outside this source review. Galaxy AI shortcuts only explain how to use
Samsung's tools; choosing those tools is subject to Samsung's own data handling.

Source review is not an absolute guarantee against vulnerabilities or compromised
devices/services. Android's keyboard-enablement warning describes the access afforded
to an input method; it is not evidence that this app records or transmits keystrokes.

Validation includes unit tests for sensitive editor policies and Android instrumentation
tests for fresh-install defaults, history removal on upgrade, preservation of manual
words/settings, and persistence of an explicit subsequent opt-in.

## 0.6.19 phrase learning

Existing 0.6.18 privacy migration flags and preference files remain unchanged.
An in-place update using the same signer preserves single-character Chinese counts, English counts,
manual words, pins and settings. New `W:` keys share the existing `learned` file
and store at most 1,000 bundled Chinese words (2–8 characters) and their counts.
They do not evict the separate 2,000-character quota. Selecting a known phrase or
its continuation can update these counts; English/translation spans and punctuation
break phrase matching. An automatic correction does not learn a phrase. Reselecting
a committed candidate reverses its phrase increments. Surrounding editor text is
transient and never becomes a key; unknown sentences are not collected. Disabling
learning prevents reads and writes of these personal counts. Clearing learning
clears both character and phrase keys. Sensitive editor restrictions are unchanged.

The user-authorized new signing identity begins at 0.6.19. Transition from the
old 0.6.18 signer cannot use an ordinary in-place update and cannot promise
preservation of that installation's data. Subsequent releases must retain the
new 0.6.19 signer to preserve opted-in learning through normal updates.
