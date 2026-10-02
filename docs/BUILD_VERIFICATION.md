# Build verification — 0.1.0

Verified on 2026-10-03 (Hong Kong time).

- Clean build: `gradle clean testDebugUnitTest lintDebug assembleDebug` — successful.
- JDK 17, Gradle 8.13, Android Gradle Plugin 8.9.2, compile/target SDK 35, minimum SDK 26.
- 11 JVM tests passed: 8 dictionary/learning tests, 3 sensitive-input policy tests.
- The bundled base dictionary contains 23,947 accepted entries; every accepted entry is checked for reachability using its derived Quick code.
- Android lint: 0 errors, 5 warnings (2 custom touch/accessibility checks and 3 string internationalisation checks). Click actions are provided for both gesture keys; TalkBack still requires device testing.
- Debug APK signature verified using `apksigner verify`; APK package is `hk.kaiboard.android`, versionName `0.1.0`, versionCode `1`.
- Manifest contains no requested permissions, including no Internet permission. IME service is protected with `BIND_INPUT_METHOD`.
- Upstream dictionary file verified byte-for-byte against the pinned revision. SHA-256: `8690f2ad8aafd38780846881aa916b5779e6d9247a351a1da426d3f3257afca4`.

Not performed: emulator/UI automation, Samsung Galaxy Z Fold7 physical testing, One UI 8.5 Galaxy AI integration testing. This is a debug build for initial device trials, not a certified production release. See TESTING.md for remaining checks.
