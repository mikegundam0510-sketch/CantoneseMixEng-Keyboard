#!/usr/bin/env bash
set -euo pipefail
mkdir -p fluency-evidence
app_apk=$(find fluency-apks -name app-debug.apk -print -quit)
test_apk=$(find fluency-apks -name app-debug-androidTest.apk -print -quit)
test -n "$app_apk"
test -n "$test_apk"
adb install -r -g "$app_apk"
adb install -r -g "$test_apk"
adb shell ime enable hk.kaiboard.android/.KaiboardService
adb shell ime set hk.kaiboard.android/.KaiboardService
adb shell dumpsys gfxinfo hk.kaiboard.android reset > fluency-evidence/frames-reset.txt
status=0
adb shell am instrument -w -r -e class hk.kaiboard.android.TypingFluencyTest hk.kaiboard.android.test/androidx.test.runner.AndroidJUnitRunner > fluency-evidence/instrumentation.txt || status=$?
adb pull /sdcard/Android/data/hk.kaiboard.android/files fluency-evidence/metrics || true
adb shell dumpsys gfxinfo hk.kaiboard.android framestats > fluency-evidence/frames.txt
adb shell dumpsys meminfo hk.kaiboard.android > fluency-evidence/memory.txt
python3 - <<'PY'
from pathlib import Path
import json
output=Path('fluency-evidence/instrumentation.txt').read_text()
if 'OK (1 test)' not in output:
    raise SystemExit('Actual IME fluency test did not pass; inspect instrumentation.txt')
reports=list(Path('fluency-evidence/metrics').rglob('typing-fluency.json'))
if len(reports)!=1:raise SystemExit('Missing actual editor latency report')
report=json.loads(reports[0].read_text())
if not all(p['model_bundled'] for p in report['phases']):
    raise SystemExit('Experimental model was not included in this fluency test')
print(json.dumps(report,ensure_ascii=False,indent=2))
PY
exit "$status"
