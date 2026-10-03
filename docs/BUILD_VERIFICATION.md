# Build verification — 0.3.0

Verified on 2026-10-03 (Hong Kong time).

- JDK 17.0.12, Gradle 8.13 (distribution SHA-256 checked against the wrapper configuration), Android Gradle Plugin 8.9.2, compile/target SDK 35, minimum SDK 26.
- Final `testDebugUnitTest lintDebug assembleDebug --no-daemon --offline` succeeded. Dependencies and Android SDK were downloaded earlier; this last check used cached dependencies.
- **44 tests passed, 0 failures, 0 errors, 0 skipped.** Breakdown: 9 dictionary/learning, 9 continuous Quick/association, 4 Emoji, 3 sensitive-input policy, 4 English engine, 3 shortcut format/limits, 9 IME/editor flows and 3 settings-dialog flows.
- Robolectric 4.14.1 / Android API 28 runs the actual IME composition, candidate and commit methods against an Android in-memory editor. It checks 你好嗎, retaining `vdrf` after selecting 你, selecting a candidate beyond the first 30 from the expanded grid, literal EN Space, shortcuts in normal/private fields, password input, composing deletion, association suffix insertion, disabling associations and clearing transient context on hide.
- Settings-dialog tests exercise adding a shortcut, rejecting a duplicate without overwriting, and deleting only after confirmation while preserving other entries. Android button-handler messages are processed in the tests.
- `ofvdrf` still ranks 你好嗎 first. The bundled Quick phrase data is unchanged at 108,880 code/phrase entries. Base dictionary: 23,947 accepted entries. Emoji: 3,773 fully-qualified Unicode 15.1 sequences across 9 categories.
- English: 198,308 unique words. The pinned Wordnik source SHA-256 matches `english-provenance.json`; the rebuild script reproduces the bundled file. Completion and spelling are offline, bounded and explicitly selected; there is no grammar or context model.
- Android lint has 0 errors and 7 warnings: 4 string internationalisation checks, 2 custom-touch accessibility checks and 1 drawing allocation. TalkBack and rendering still require device testing.
- Debug APK signature verified using `apksigner verify`. Package `hk.kaiboard.android`, versionName `0.3.0`, versionCode `3`, application label `粵語中英混合keyboard`.
- `aapt dump permissions` reports no requested permissions, including no Internet permission. The IME service remains protected by `BIND_INPUT_METHOD`. Backups/device transfer exclude preferences and local records.
- Debug signing certificate SHA-256: `817d37772c31893cdb9209c38ce527e9011d6a8a5ae5a658fe8c5cae5500cd70`. It differs from the previously recorded 0.2.0 debug certificate because that key was unavailable. An installed older APK may need uninstalling first; uninstalling clears settings, learning, recent Emoji and authored shortcuts.

## UI and scope limitations

Robolectric is a JVM Android simulation, not an installed emulator or physical phone. No end-to-end emulator tapping or rendered-device screenshot was verified for 0.3.0. This environment has no `/dev/kvm`; the earlier 0.2.0 emulator UI failure is recorded in [the archived report](BUILD_VERIFICATION_0.2.0.md), rather than treated as a passed check.

Not performed: physical Galaxy Z Fold7 / One UI 8.5 testing, actual popup-window positioning, cover/inner-screen rendering, fold/unfold lifecycle checks, full accessibility acceptance, startup latency on the target phone, or Samsung Galaxy AI integration. The debug editor is present in debug builds only.

The Kaiboard official feature list could not be retrieved under the environment's network policy. This version implements the user's confirmed Quick-focused scope and the features in [FEATURE_SCOPE.md](FEATURE_SCOPE.md); it does not establish parity with every Kaiboard feature or proprietary ranking engine. See [TESTING.md](TESTING.md) for the remaining device acceptance checks. This is a debug build for device trials.
