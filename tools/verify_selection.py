"""Verify swipe selection, normal key taps, and bilingual candidates on synthetic editors."""
import pathlib,subprocess
out=pathlib.Path('selection-evidence');out.mkdir(exist_ok=True)
for path in ['app/build/outputs/apk/debug/app-debug.apk','app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk']:
 subprocess.run(['adb','install','-r',path],check=True)
subprocess.run(['adb','shell','settings','put','secure','show_ime_with_hard_keyboard','1'],check=True)
subprocess.run(['adb','shell','ime','enable','hk.kaiboard.android/.KaiboardService'],check=True)
subprocess.run(['adb','shell','ime','set','hk.kaiboard.android/.KaiboardService'],check=True)
r=subprocess.run(['adb','shell','am','instrument','-w','-e','class','hk.kaiboard.android.SwipeSelectionTest,hk.kaiboard.android.CursorGestureTouchTest','hk.kaiboard.android.test/androidx.test.runner.AndroidJUnitRunner'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
(out/'tests.txt').write_text(r.stdout);print(r.stdout)
subprocess.run(['adb','pull','/sdcard/Android/data/hk.kaiboard.android/files/',str(out/'screenshots')],check=False)
if r.returncode or 'OK (' not in r.stdout or 'FAILURES' in r.stdout:
 (out/'failure-logcat.txt').write_text(subprocess.check_output(['adb','logcat','-d'],text=True))
 raise AssertionError('Selection or bilingual candidate regression failed')
