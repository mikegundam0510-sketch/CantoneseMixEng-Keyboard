"""Actual five-stroke input checks on a disposable emulator."""
import pathlib,subprocess,time,shlex,re,sys,xml.etree.ElementTree as ET
out=pathlib.Path('stroke-evidence');out.mkdir(exist_ok=True)
def adb(*a):
 if a and a[0]=='shell':a=('shell',shlex.join(a[1:]))
 return subprocess.check_output(['adb',*a],text=True,timeout=30)
def tree():
 for _ in range(4):
  try:
   adb('shell','uiautomator','dump','--windows','/sdcard/stroke.xml')
   return ET.fromstring(adb('shell','cat','/sdcard/stroke.xml'))
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
 n=next(n for n in tree().iter('node') if n.get('class')=='android.widget.EditText');b=bounds(n)
 adb('shell','input','tap',str((b[0]+b[2])//2),str(b[1]+40));time.sleep(.5)
 adb('shell','am','start','--activity-single-top','-n','hk.kaiboard.android/.KeyboardPreviewActivity','--es','test_text','__EMPTY__','--es','test_input_type',kind);time.sleep(1)
def editor():return next(n.get('text') for n in tree().iter('node') if n.get('class')=='android.widget.EditText')
def code(value):
 names={'h':'筆劃：橫','s':'筆劃：豎','p':'筆劃：撇','n':'筆劃：點捺','z':'筆劃：折','*':'筆劃：萬用一筆'}
 nodes={n.get('content-desc'):n for n in tree().iter('node')}
 for stroke in value:
  b=bounds(nodes[names[stroke]]);adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.12)
 time.sleep(.4)
def wait_candidate(word):
 for _ in range(20):
  if find('筆劃候選：'+word) is not None:return
  time.sleep(.3)
 raise AssertionError('Missing stroke candidate '+word)
def check_empty_code():
 n=find('筆劃字碼');assert n is not None and n.get('text')=='筆劃',n.attrib if n is not None else None
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
 adb('shell','wm','size',size);adb('shell','wm','density','320');reset()
 for _ in range(20):
  if find('筆劃') is not None:break
  time.sleep(.5)
 assert find('手寫') is None
 tap('筆劃')
 for _ in range(30):
  n=find('筆劃字碼')
  if n is not None and n.get('text')=='筆劃':break
  time.sleep(.3)
 check_empty_code()
 code('hshhsznnnn');wait_candidate('馬');shot(name+'-horse')
 assert editor() in ('','試打中文、English 或 Emoji…'),'Unconfirmed stroke code leaked into editor'
 tap('筆劃候選：馬');assert editor()=='馬';check_empty_code()
 code('hh');tap('筆劃退格');assert find('筆劃字碼').get('text')=='一'
 tap('清除筆劃');check_empty_code();assert editor()=='馬'
 code('*shhsznnnn');wait_candidate('馬');tap('筆劃候選：馬');assert editor()=='馬馬'
 code('pspzznzpn');wait_candidate('係');tap('筆劃候選：係');assert editor()=='馬馬係'
 code('h');wait_candidate('一');tap('展開或收起筆劃候選');shot(name+'-expanded');tap('筆劃候選：一');assert editor()=='馬馬係一'
 tap('筆劃逗號');tap('筆劃句點');tap('筆劃空白');assert editor()=='馬馬係一,. '
 tap('筆劃退格');assert editor()=='馬馬係一,.'
 code('h');tap('返回鍵盤');assert find('O，人') is not None;tap('筆劃');check_empty_code()
 assert adb('shell','settings','get','secure','default_input_method').strip()==ime
 shot(name+'-strokes');tap('返回鍵盤');shot(name+'-keyboard')
reset('password');assert find('筆劃').get('enabled')=='false'
reset('number');assert find('筆劃').get('enabled')=='false'
(out/'result.txt').write_text('PASS: cover/unfolded; 馬 and 係; wildcard; pending code stays local; candidate commit; expand; backspace; clear; punctuation/space; return to Quick; secure/numeric restriction; no handwriting entry\\n')

