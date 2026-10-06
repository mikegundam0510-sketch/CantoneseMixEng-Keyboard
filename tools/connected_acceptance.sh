#!/usr/bin/env bash
# Collect evidence before emulator-runner shuts down, including on failure.
set -u
status=0
bash ./gradlew connectedDebugAndroidTest --no-daemon || status=$?
mkdir -p ui-evidence
adb pull /sdcard/Android/data/hk.kaiboard.android/files ui-evidence/instrumentation || true
adb logcat -d > ui-evidence/instrumentation-logcat.txt
exit "$status"
