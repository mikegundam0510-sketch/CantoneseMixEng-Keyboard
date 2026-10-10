"""Run native numeric IME acceptance and retrieve its screenshots/report."""
import argparse
import json
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=Path('/tmp/numeric-keyboard-evidence'))
parser.add_argument('--test-apk', type=Path, default=Path('app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'))
parser.add_argument('--collect-only', action='store_true', help='Collect after connectedDebugAndroidTest has run this test')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
if not args.collect_only:
    subprocess.run(['adb', 'install', '-r', str(args.test_apk)], check=True, timeout=180)
    log = args.output / 'instrumentation.txt'
    with log.open('w', encoding='utf-8') as out:
        result = subprocess.run(['adb', 'shell', 'am', 'instrument', '-w', '-e', 'class',
            'hk.kaiboard.android.NumericKeyboardTest',
            'hk.kaiboard.android.test/androidx.test.runner.AndroidJUnitRunner'],
            stdout=out, stderr=subprocess.STDOUT, text=True, timeout=900)
    output = log.read_text(encoding='utf-8')
    print(output, flush=True)
    assert result.returncode == 0 and re.search(r'OK\s*\(1 test\)', output), 'Native numeric acceptance failed'
for name in ['result.json', 'cover-number.png', 'cover-pin.png', 'unfolded-number.png',
        'unfolded-pin.png', 'decimal.png', 'phone.png', 'datetime.png']:
    data = subprocess.check_output(['adb', 'exec-out', 'run-as', 'hk.kaiboard.android', 'cat',
        'files/numeric-keyboard-evidence/' + name], timeout=60)
    assert data, 'Missing numeric evidence: ' + name
    (args.output / name).write_bytes(data)
report = json.loads((args.output / 'result.json').read_text(encoding='utf-8'))
assert report['status'] == 'passed' and report['learning_unchanged'], 'Numeric evidence did not pass'
print('PASS: numeric layout, real digit/delete/action touches, visible icons and learning protection', flush=True)
