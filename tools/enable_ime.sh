#!/usr/bin/env bash
# Package installation can return before InputMethodManager receives its update.
set -euo pipefail
ime='hk.kaiboard.android/.KaiboardService'
for attempt in $(seq 1 30); do
    if adb shell ime list -a -s | tr -d '\r' | grep -Fxq "$ime"; then
        adb shell ime enable "$ime"
        adb shell ime set "$ime"
        exit 0
    fi
    sleep 1
done
adb shell ime list -a
echo 'Installed keyboard did not register with InputMethodManager' >&2
exit 1
