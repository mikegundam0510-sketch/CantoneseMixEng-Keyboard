"""Run every device check and retain individual results on the disposable emulator."""
import subprocess,pathlib,sys,json
out=pathlib.Path('acceptance-evidence');out.mkdir(exist_ok=True)
results={}
subprocess.run(['adb','install','-r','apk/app-debug.apk'],check=True)
subprocess.run(['adb','install','-r','app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'],check=True)
r=subprocess.run(['adb','shell','am','instrument','-w','hk.kaiboard.android.test/androidx.test.runner.AndroidJUnitRunner'],text=True,capture_output=True,timeout=180)
(out/'instrumentation.txt').write_text(r.stdout+r.stderr)
results['Android touch tests']=r.returncode==0 and 'OK (' in r.stdout and 'FAILURES!!!' not in r.stdout
for script in ['clipboard_smoke.py','editor_smoke.py','ui_smoke.py','handwriting_smoke.py']:
    print('Running '+script,flush=True)
    r=subprocess.run([sys.executable,'tools/'+script],text=True,capture_output=True,timeout=1200)
    (out/(script+'.log')).write_text(r.stdout+r.stderr)
    print((r.stdout+r.stderr)[-4000:],flush=True)
    results[script]=r.returncode==0
(out/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2),flush=True)
sys.exit(0 if all(results.values()) else 1)
