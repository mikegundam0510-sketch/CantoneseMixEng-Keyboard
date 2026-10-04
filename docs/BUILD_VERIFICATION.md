# Build verification — 0.6.0 source preview

## Requested physical-device test APK

On 2026-10-04 the user authorized providing a test APK and requested the display name `cantonesemixeng keyboard`. App, IME and settings title now use that name.

- Package build source: `5b461d299f29b0c50c09cfca10ec35b83e7e67b5`. Input behavior and geometry match the previously verified `ec42d6615bf686cf888f69bfee2ff4a9058419c1`; subsequent changes are display-name resources/titles and the packaging workflow.
- Packaging run: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37176101481 — success. `assembleDebug`, `apksigner verify` and `aapt dump badging` passed. This packaging result does not replace the prior emulator acceptance or establish physical-device reliability.
- APK: `cantonesemixeng-keyboard-0.6.0-device-test.apk`, app ID `hk.kaiboard.android`, version 0.6.0 / code 7, min API 26, target API 35. Display label verified in compiled manifest. Debug test package; APK Signature Scheme v2 verified.
- APK SHA256: `046ddea2e4fb07c54cc639744853e88420b2a47e778bfc5197d0e1fa861e3f6a`.
- Signing certificate SHA256: `3f9dedfa58d91126c17d741511f7e45eae3e8b84836a71905ffcb079c21cf205`. Different from earlier delivered test builds; installing over those requires uninstalling first, which removes settings and learned words.
- Artifact: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37176101481/artifacts/11293327250 (14-day retention). Contains the APK and verification report. PR remains draft and unmerged; no GitHub release was created.

## Reference key proportions

Verified code commit: `ec42d6615bf686cf888f69bfee2ff4a9058419c1`, 2026-10-04 UTC.

- Push verification: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37174672639 — success. 45 JVM tests and four AndroidX touch tests passed, no failures/skipped tests. Lint: 14 warnings, no blocking errors. Full emulator UI acceptance passed, including the new 96px / 48dp letter-key bounds and row-pitch assertions at density 320, shared-row stability and all existing input checks.
- Actual idle/typing screenshots inspected at 360dp and 720dp widths: radicals and icons are visible, and keyboard height is another 30dp lower than the shared-row build. Top edge moved from y=818 to y=878 on cover and y=1018 to y=1078 on unfolded, both 60px at density 320.
- Evidence: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37174672639/artifacts/11292759064 ; SHA256 `6adea8fafe6a0e24ebbfb2f69808b97c2e8476d317ddc991884eb44aab23f49a`. The inspected ZIP contains no APK; internal test packages were removed.
- A separate PR run on the same code (37174674487) failed its English confirmation check: `hello` was entered as `helo`, then Space added a space correctly. The independent successful run passed this check and the remaining rapid/edge/gesture checks without changing production code or weakening assertions. The cause of that isolated dropped repeat tap is unresolved; these emulator results do not guarantee zero missed taps on real Samsung/Fold hardware.

- Matched the supplied reference by proportional measurement at equal keyboard widths. Standard letter-key face height is 40dp (previously 50dp), vertical visual gap 8dp (previously 6dp), horizontal visual gap 5dp (previously 4dp). The resulting 48dp row pitch closely follows the reference's approximately 47dp pitch at 360dp width; exact physical size depends on device density, screen and one-hand settings.
- Number-key face remains 37dp. Enter now uses the same visual insets as adjacent keys. Landscape compact height is 36dp.
- Standard/high/extra-high preferences become 40/46/52dp, with one-time migration from the old 50/56/62dp choices. Full key bounds still receive touches including the visual gaps. Existing shared toolbar/candidate row behavior is retained.

## Shared toolbar and candidate row

Verified code commit: `c726b5062ed42a7b8c5873deeae77bc11ae124b7`, 2026-10-04 UTC.

- Draft PR verification: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37173415608 — success.
- Idle shows the function toolbar; uncommitted codes replace it with a compact code badge and the existing candidate strip in the same fixed 50dp slot. Committing all codes or clearing them restores the toolbar. Partial selection keeps the remaining codes in candidate mode, independent of asynchronous search results.
- Chinese/English mode is available in the idle toolbar and in the expanded candidate panel during composition. Repair candidates keep their existing plain labels and long-press provenance.
- Added API 31 UI acceptance passed at both 360dp and 720dp widths: toolbar absent during composition, bounded code badge, identical letter-key bounds before typing and after full commit, and toolbar restoration after commit and deleting the last code. Existing English forcing/learning, prefix selection, reselection, emoji and mixed-input checks passed.
- Actual screenshot inspection passed. Against the previous verified screenshots at density 320, the keyboard upper edge moved from y=720 to y=818 on the 720×1600 cover configuration and from y=920 to y=1018 on the 1440×1800 unfolded configuration: 98px / 49dp less height. No extra toolbar row remains during composition. Expanded controls remain outside the compact strip.
- `testDebugUnitTest lintDebug assembleDebug assembleDebugAndroidTest` passed: 45 JVM tests, no failures/ignored tests; lint has 14 warnings and no blocking errors. Four AndroidX touch instrumentation tests passed with no failures/skipped tests.
- Evidence: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37173415608/artifacts/11292542295 ; SHA256 `458ccd4ff6f7c89270cb08e9e3b464db6a6b87c580c504c91216ff343ea732d0`. Reports, UI acceptance result and actual screenshots only; inspected ZIP has no APK. Internal disposable emulator test packages were removed by the workflow.
- PR #1 remains draft and unmerged; no APK was published or supplied. Physical Samsung/Fold acceptance and the device limits listed below remain outstanding.

## Previous 0.6.0 validation

Verified code commit: `94bbaefa309af5ce5278202c8e12c40c563aa20e`, 2026-10-04 (Hong Kong).

- Push verification: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37172187336 — success.
- Draft PR verification: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37172189586 — success.
- `testDebugUnitTest lintDebug assembleDebug assembleDebugAndroidTest` passed. 45 JVM tests, zero failures/ignored tests. Lint: 14 warnings, no blocking errors.
- Android 12 / API 31 emulator: four AndroidX instrumentation tests passed. 25 overlapping two-finger cycles generated all 50 expected key clicks, with no cursor gesture. Outer key-edge clicks and small finger movement remained clicks; a deliberate horizontal drag cancelled the key click and moved the cursor.
- Actual UI acceptance passed: Emoji browsing/tone selection, one compact candidate strip and horizontal scrolling without committing, Cantonese ranking, reselection and segment replacement, English learning/spelling repair, mixed sentences, pin/unpin, integrated Quick repairs and long-press code provenance, punctuation, left/right cursor swipes, key-edge taps, rapid input, exact-prefix selection, stale-search cancellation and expanded per-character selection.
- URI-type editor acceptance passed: explicit Chinese switch, Chinese commit, and preserving the selected mode after `restartInput`. This uses a local editor with Android URI input flags; a real browser/address bar still needs device acceptance. Password and numeric policies passed.
- Actual screenshots and key-bound checks passed at 360dp cover-sized and 720dp unfolded-sized widths. These are representative emulator configurations, not physical Galaxy Fold hardware.
- Fixed Back handling for an open candidate menu: Back dismisses the menu while keeping the keyboard and uncommitted codes available; the UI acceptance exercises this before selecting a repair.
- Evidence artifact: https://github.com/mikegundam0510-sketch/kaiboard-samsung/actions/runs/37172187336/artifacts/11291752866
- Artifact SHA256: `c0c8c9b98ef43eecda26f09f489f0367e89a31092457338c23cf55bc969c3f6d`.
- Evidence contains test/lint reports and actual screenshots; its ZIP contains no APK. Internal test packages were prepared solely for the disposable emulator and removed after the run. No APK was published or supplied to the user.

Remaining: physical Samsung/Fold touch feel, real browser/editor quirks, fold/cover/inner lifecycle, API 35 runtime and predictive-back acceptance, voice provider/yue-HK behavior and full accessibility. The offline model does not guarantee first-choice accuracy for arbitrary sentences. PR #1 remains draft and unmerged.

## Historical 0.5.1 verification

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


