# Hong Kong personal learning — 0.6.19

Based on `340d6cd` (`codex/hk-context-collocations`, version 0.6.18), with its
existing keyboard, offline model, clipboard, stroke and voice features retained.

## Resulting behavior

Opting in to learning now records counts for bundled Chinese words of 2–8
characters, as well as the existing single-character and English counts.
An explicitly chosen exact word can move ahead of an ambiguous code's other
candidates. Choosing a continuation such as 晒 after 唔該 learns 唔該晒 and
can improve that continuation's rank. Longer matching context remains more
important than short-prefix guesses. Automatic corrections do not add counts;
reselection reverses the selected candidate's phrase increments.

The model learns only words already in the bundled vocabulary, not unknown
sentences. Counts remain on the phone, are off by default, and can be cleared
through the existing learning control. Sensitive editors do not use or update
these counts. Character and phrase quotas are independent (2,000 and 1,000).
The existing preference file and single-character key formats remain unchanged.

23 new everyday words are added, including 凍檸茶, 搭小巴, 多謝你, 聽日見 and
搞掂晒. Existing vocabulary rows and priorities are retained. The additions are
authored priorities, not measured frequencies; `tools/hk_daily_words.txt` is
also included by the language-data generator.

## Validation

`testDebugUnitTest`, `lintDebug`, `assembleDebug`, `assembleDebugAndroidTest`
and `assembleRelease` pass: 95 JVM tests, no failed/error/skipped tests; lint
has zero errors and 23 warnings. Eight new JVM tests cover learning boundaries,
exact-code reachability, phrase promotion, continuation personalization and
preservation of the legacy key format. Signing tests exercise disposable keys
and fail-closed behavior; no real private key is printed.

The unpersonalized comparison against `340d6cd` passes:

| Suite | Cases | Before/after first | Before/after top 5 | Before/after top 8 |
|---|---:|---:|---:|---:|
| Development | 40 | 33 / 33 | 39 / 39 | 39 / 39 |
| Separate held-out conversations | 120 | 61 / 61 | 97 / 97 | 105 / 105 |

All returned candidates were checked against the complete input codes. These
results establish no regression on these cases, rather than a general accuracy
gain or full-sentence understanding. Personalized improvements are covered
by the explicit-choice tests. Host timings were collected alongside builds and
do not establish device fluency. Reproduce with:

```sh
bash tools/context_accuracy.sh 340d6cd /tmp/hk-learning-context-evidence
python3 tools/test_signing.py
```

The new persistent signing baseline begins at 0.6.19 by explicit user request.
Both debug and release APKs verify against the same new pinned certificate.
The previous 0.6.18 private key was unavailable; transition from its old signer
cannot promise retention of existing phone data. See PERSISTENT_SIGNING.md.

The API 31 software emulator connected but did not complete Android service
initialization. APK installation failed in StorageManagerService with a missing
PackageManagerInternal; activity-manager instrumentation could not execute.
The preference instrumentation and same-signer version-code 26→27 install
test were therefore **not completed**, and no device-upgrade result is claimed.
A separate code-27 APK was prepared only as a local test fixture. The delivered
APK is the verified release build with code 26 / version 0.6.19. Real-device
typing, actual learned-choice persistence and Fold-specific acceptance remain
to be exercised using the device checklist.
