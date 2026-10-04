"""Run native recognition fixtures and actual handwriting touch checks."""
import pathlib,subprocess
out=pathlib.Path('recognition-evidence');out.mkdir(exist_ok=True)
subprocess.run(['adb','install','-r','app/build/outputs/apk/debug/app-debug.apk'],check=True)
subprocess.run(['adb','install','-r','app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'],check=True)
r=subprocess.run(['adb','shell','am','instrument','-w','-e','class','hk.kaiboard.android.HandwritingRecognitionTest','hk.kaiboard.android.test/androidx.test.runner.AndroidJUnitRunner'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
(out/'native-tests.txt').write_text(r.stdout)
print(r.stdout)
assert r.returncode==0 and 'OK (' in r.stdout and 'FAILURES' not in r.stdout,'Native handwriting regression failed'
subprocess.run(['python3','tools/handwriting_smoke.py'],check=True)
