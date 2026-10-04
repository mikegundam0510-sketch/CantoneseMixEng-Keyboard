"""Actual native handwriting-pad smoke check on a disposable emulator."""
import pathlib,subprocess,time,shlex,re,sys,xml.etree.ElementTree as ET
out=pathlib.Path('handwriting-evidence');out.mkdir(exist_ok=True)
def adb(*a):
 if a and a[0]=='shell':a=('shell',shlex.join(a[1:]))
 return subprocess.check_output(['adb',*a],text=True,timeout=30)
def tree():
 for _ in range(4):
  try:
   adb('shell','uiautomator','dump','--windows','/sdcard/hwr.xml')
   return ET.fromstring(adb('shell','cat','/sdcard/hwr.xml'))
  except Exception:time.sleep(1)
 raise AssertionError('UI dump unavailable')
def find(desc):return next((n for n in tree().iter('node') if n.get('content-desc')==desc),None)
def bounds(n):assert n is not None;return list(map(int,re.findall(r'\d+',n.get('bounds'))))
def tap(desc):
 b=bounds(find(desc));adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.4)
def shot(name):
 with (out/(name+'.png')).open('wb') as f:subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
 (out/(name+'.xml')).write_text(ET.tostring(tree(),encoding='unicode'))
def dismiss_system_prompt():
 for node in tree().iter('node'):
  if node.get('text') in ('GOT IT','Got it'):
   b=bounds(node);adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(1);return
def reset(kind='normal'):
 adb('shell','am','start','--activity-single-top','-n','hk.kaiboard.android/.KeyboardPreviewActivity','--es','test_text','__EMPTY__','--es','test_input_type',kind);time.sleep(2);dismiss_system_prompt()
def editor():return next(n.get('text') for n in tree().iter('node') if n.get('class')=='android.widget.EditText')
def draw_horizontal():
 b=bounds(find('手寫區'));size=min(b[2]-b[0],b[3]-b[1])-28;cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
 adb('shell','input','swipe',str(round(cx-size*.36)),str(round(cy)),str(round(cx+size*.36)),str(round(cy)),'600')
 for _ in range(20):
  if find('手寫候選：一') is not None:return
  time.sleep(.3)
 raise AssertionError('Native handwriting did not recognize the horizontal stroke as 一')
def failure(kind,value,tb):
 try:
  (out/'failure-logcat.txt').write_text(adb('logcat','-d'))
  shot('failure')
 except Exception:pass
 sys.__excepthook__(kind,value,tb)
sys.excepthook=failure
adb('install','-r','app/build/outputs/apk/debug/app-debug.apk')
adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
ime=None
for _ in range(30):
 ime=next((x.strip() for x in adb('shell','ime','list','-a','-s').splitlines() if 'hk.kaiboard.android' in x),None)
 if ime:break
 time.sleep(1)
assert ime,'Installed input method was not registered'
adb('shell','ime','enable',ime);adb('shell','ime','set',ime)
for name,size in [('cover','720x1600'),('unfolded','1440x1800')]:
 adb('shell','wm','size',size);adb('shell','wm','density','320');reset();
 for _ in range(20):
  if find('手寫') is not None:break
  time.sleep(.5)
 tap('手寫');assert find('手寫區') is not None
 draw_horizontal();shot(name+'-candidates');tap('手寫候選：一');assert editor()=='一'
 assert find('手寫候選：一') is None
 draw_horizontal();tap('撤銷一筆');assert find('手寫候選：一') is None
 draw_horizontal();tap('清除');assert find('手寫候選：一') is None
 tap('鍵盤');assert find('O，人') is not None
 assert adb('shell','settings','get','secure','default_input_method').strip()==ime
 shot(name+'-keyboard')
reset('password');assert find('手寫').get('enabled')=='false'
(out/'result.txt').write_text('PASS: native handwriting 一 candidate/commit, undo, clear, return, same IME, cover/unfolded, password restriction\n')
