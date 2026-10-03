# Build verification — 0.2.0

Verified on 2026-10-03 (Hong Kong time).

- JDK 17, Gradle 8.13, Android Gradle Plugin 8.9.2, compile/target SDK 35, minimum SDK 26.
- Clean build and 22 JVM tests succeeded. Final `testDebugUnitTest lintDebug assembleDebug` also succeeded after adding the debug-only local editor.
- Tests: 8 dictionary/learning, 3 sensitive-input policy, 7 continuous Quick decoder, 4 Emoji catalog/deletion tests. No failures or skipped tests.
- `ofvdrf` ranks 你好嗎 first; phrase alternatives consume all typed codes. Tests also cover 香港, 唔該, one-code characters, invalid input and bounded decoding.
- Base dictionary: 23,947 accepted entries, checked for reachability using derived Quick codes. Derived phrase file: 108,880 entries. Emoji catalog: 3,773 fully-qualified Unicode 15.1 sequences across 9 categories.
- Emoji tests check whole-sequence deletion for skin tones, flags, family, heart and keycap sequences, preserving adjacent text.
- Android lint: 0 errors, 9 warnings (6 string internationalisation checks, 2 custom touch/accessibility checks, 1 drawing allocation). TalkBack requires device testing.
- Debug APK signature verified with `apksigner verify`. Package `hk.kaiboard.android`, versionName `0.2.0`, versionCode `2`, application label `粵語中英混合keyboard`.
- Manifest requests no permissions, including no Internet permission. IME service is protected by `BIND_INPUT_METHOD`.
- Debug signing certificate SHA-256: `834f689227ae089a8cbc1fdc8f6bcd5f8035e6cb59379fb625f2acf550e46fb6`. The earlier environment's debug signing key was unavailable: an installed 0.1.0 APK may need uninstalling before installing this build. Uninstalling clears settings and learned data.

## UI validation limitation

APK installed successfully on an Android 15 / API 35 emulator, and the system discovered and enabled the input method. The emulator's System UI repeatedly became unresponsive under software emulation without hardware acceleration, including at reduced resolution. Consequently, end-to-end key taps, candidate selection and cover/inner-screen appearance were **not successfully verified**. No simulated screenshot is presented as a passed UI check.

Not performed: physical Galaxy Z Fold7 / One UI 8.5 testing, Samsung Galaxy AI integration, fold/unfold lifecycle checks, or full accessibility acceptance. The split layout is selected using available width >= 600dp; it still needs testing on the target device. See TESTING.md for the concrete acceptance checklist. This is a debug build for device trials, not a certified production release.
