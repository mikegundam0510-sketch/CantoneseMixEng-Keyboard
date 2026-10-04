"""Run stroke dictionary tests, touch checks and clipboard regression."""
import pathlib,subprocess
out=pathlib.Path('stroke-evidence');out.mkdir(exist_ok=True)
subprocess.run(['adb','install','-r','app/build/outputs/apk/debug/app-debug.apk'],check=True)
subprocess.run(['adb','install','-r','app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'],check=True)
r=subprocess.run(['adb','shell','am','instrument','-w','-e','class','hk.kaiboard.android.StrokeDictionaryTest','hk.kaiboard.android.test/androidx.test.runner.AndroidJUnitRunner'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
(out/'dictionary-tests.txt').write_text(r.stdout);print(r.stdout)
assert r.returncode==0 and 'OK (' in r.stdout and 'FAILURES' not in r.stdout,'Stroke dictionary regression failed'
subprocess.run(['python3','tools/stroke_smoke.py'],check=True)
subprocess.run(['python3','tools/clipboard_smoke.py'],check=True)

