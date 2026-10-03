# Build verification — 0.5.1

Verified code commit: `686827a88c400b1909d684b59d66fe8643a4f419`, 2026-10-03 UTC.

- GitHub Actions push run: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37134145242 (successful retry after an incomplete Google SDK repository download).
- `testDebugUnitTest lintDebug assembleDebug` passed; 39 JVM tests, zero failures/ignored tests. Lint: 15 warnings, no errors.
- API 31 emulator acceptance passed: prior Emoji/candidate scrolling/HK examples/reselection/English/mixed/pinning/repair/punctuation/cursor checks plus edge taps, rapid physical-key event injection, exact-prefix selection preserving remaining codes and stale-result rejection after editor reset.
- APK ZIP artifact: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37134145242/artifacts/11277891685
- UI evidence artifact: 11277822363. Test/lint reports: 11277951512.
- APK SHA256: `f68560d23eabce9b3a20cb5cd815bb28ca6894d471cf7eb8ed855270d554b224`.
- APK v2 signing certificate SHA256: `c3c50dab747c1cd3b7d7d04628ebf7807ab167bc5ffdf7d362c0cd70ea93869b`. It differs from 0.5.0; uninstall old build first, clearing settings/learning.
- VersionName 0.5.1, versionCode 6. Pending: Samsung/Fold hardware touch feel, rapid alternating fingers, fold/cover/inner lifecycle, real speech provider and full accessibility. Offline sentence ranking remains limited and is not claimed accurate for arbitrary text.

## Historical 0.5.0 verification

Verified code commit: `2dac8c49d0b7d045d515a45e9e9484c03a39785b`, 2026-10-03.

- GitHub Actions push run: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37128083672
- 39 JVM tests passed: dictionary/learning 9, Emoji browser 5, Emoji catalog 4, input policy 3, mixed input/reselection/repair 9, Quick decoder 9. No failures or ignored tests.
- `testDebugUnitTest lintDebug assembleDebug` passed. Lint reports 15 warnings, including custom touch accessibility; full TalkBack acceptance remains unverified.
- API 31 emulator passed real keyboard touches for emoji categories/tone insertion, HK sentence ordering, candidate scrolling without commit, icon space, safe reselection/one-segment edit, English Space/repair/learning, case-preserved mixed sentence, pin/unpin, separate Quick typo correction, punctuation and left/right character-key cursor swipes without key insertion.
- APK ZIP artifact: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37128083672/artifacts/11274684093
- UI screenshots/result: artifact 11275791963. Test/lint reports: artifact 11275458339.
- APK SHA256: `06ea20e347d22ac5690ec8bc1fc1ea2034f3c0abf6ae6bc97ef36a8eb43af12a`.
- APK v2 signing certificate SHA256: `0922a24de5df077f3137410db14dce14fca56453be1aeceddf7c6ced6cc0fec9`. It differs from verified 0.4.0; uninstalling the old build is required and clears settings/learning.
- VersionName 0.5.0, versionCode 5. Requires API 26+. The app requests microphone permission for explicitly invoked Android speech recognition, and has no Internet permission.

Remaining: physical Samsung/Fold cursor feel, cover/inner display/fold lifecycle, real speech provider and yue-HK results, full accessibility and custom-editor acceptance. Bounded offline Chinese/English inference can remain ambiguous; manual segment selection is available. Keep PR #1 draft and unmerged pending user feedback.

## Historical 0.2.0 verification


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

