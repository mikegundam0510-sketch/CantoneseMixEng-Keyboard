"""Clipboard/custom toolbar acceptance on a disposable emulator; synthetic text only."""
import pathlib, subprocess, time, shlex, re, xml.etree.ElementTree as ET
out=pathlib.Path('clipboard-evidence');out.mkdir(exist_ok=True)
def adb(*a):
    if a and a[0]=='shell': a=('shell',shlex.join(a[1:]))
    return subprocess.check_output(['adb',*a],text=True,timeout=30)
def tree():
    adb('shell','uiautomator','dump','/sdcard/clipboard.xml')
    return ET.fromstring(adb('shell','cat','/sdcard/clipboard.xml'))
def find(desc): return next((n for n in tree().iter('node') if n.get('content-desc')==desc),None)
def tap(desc):
    n=find(desc);assert n is not None,desc
    b=list(map(int,re.findall(r'\d+',n.get('bounds'))))
    adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.4)
def tap_text(label):
    n=next(n for n in tree().iter('node') if n.get('text')==label)
    b=list(map(int,re.findall(r'\d+',n.get('bounds'))));adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.4)
def reset(kind='normal'):
    adb('shell','am','start','--activity-single-top','-n','hk.kaiboard.android/.KeyboardPreviewActivity','--es','test_text','__EMPTY__','--es','test_input_type',kind);time.sleep(1)
def copy(text,sensitive=False):
    adb('shell','am','start','--activity-single-top','-n','hk.kaiboard.android/.KeyboardPreviewActivity','--es','test_clipboard',text,'--ez','test_sensitive_clip',str(sensitive).lower());time.sleep(.4)
def editor():return next(n.get('text','') for n in tree().iter('node') if n.get('class')=='android.widget.EditText')
def shot(name):
    with (out/(name+'.png')).open('wb') as f:subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
    (out/(name+'.xml')).write_text(ET.tostring(tree(),encoding='unicode'))
adb('install','-r','apk/app-debug.apk')
adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
ime='hk.kaiboard.android/.KaiboardService';adb('shell','ime','enable',ime);adb('shell','ime','set',ime)
reset();copy('alpha')
assert find('選擇鍵盤') is None,'Old toolbar keyboard switch remains'
tap('剪貼簿');tap('貼上剪貼簿：alpha');assert editor()=='alpha'
copy('beta');tap('更新剪貼簿')
assert find('貼上剪貼簿：alpha') is not None
assert find('貼上剪貼簿：beta') is not None
shot('01-history')
tap('刪除剪貼簿項目：alpha');assert find('貼上剪貼簿：alpha') is None
tap('清空剪貼簿暫存');assert find('貼上剪貼簿：beta') is None
tap('更新剪貼簿');tap('返回鍵盤')
adb('shell','input','keyevent','4');time.sleep(.5)
copy('gamma')
adb('shell','input','tap','250','200');time.sleep(.8)
tap('剪貼簿');assert find('貼上剪貼簿：beta') is None
copy('sensitive-fixture',True);tap('清空剪貼簿暫存');tap('更新剪貼簿')
assert find('貼上剪貼簿：sensitive-fixture') is None
reset('password');assert find('剪貼簿').get('enabled')=='false'
shot('02-password')
reset('private');copy('private-one');tap('剪貼簿');copy('private-two');tap('更新剪貼簿')
assert find('貼上剪貼簿：private-one') is None
assert find('貼上剪貼簿：private-two') is not None
reset()
# Change options via real settings UI, then verify persistence and the next editor session.
def configure(label):
    adb('shell','am','start','-n','hk.kaiboard.android/.SettingsActivity');time.sleep(.8)
    for _ in range(15):
        n=next((n for n in tree().iter('node') if n.get('text','').startswith('自訂功能鍵')),None)
        if n is not None:break
        adb('shell','input','swipe','200','700','200','300','300');time.sleep(.2)
    assert n is not None
    b=list(map(int,re.findall(r'\d+',n.get('bounds'))));adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.3)
    n=next(n for n in tree().iter('node') if n.get('text')==label)
    b=list(map(int,re.findall(r'\d+',n.get('bounds'))));adb('shell','input','tap',str((b[0]+b[2])//2),str((b[1]+b[3])//2));time.sleep(.3)
    adb('shell','input','keyevent','4');time.sleep(.7);reset()
configure('快捷文字');tap('快捷文字')
assert any('未有快捷文字' in n.get('text','') for n in tree().iter('node'))
tap('管理快捷文字');time.sleep(.7)
for _ in range(15):
    if any(n.get('text')=='新增快捷文字' for n in tree().iter('node')):break
    adb('shell','input','swipe','200','700','200','300','300');time.sleep(.2)
tap_text('新增快捷文字');adb('shell','input','text','AQHI-fixture');tap_text('儲存')
adb('shell','input','keyevent','4');time.sleep(.8);reset();tap('快捷文字');tap('貼上快捷文字：AQHI-fixture')
assert editor()=='AQHI-fixture'
tap('返回鍵盤');configure('Undo');assert find('Undo（重新選字）').get('enabled')=='false'
tap('O，人');tap('F，火');time.sleep(.8);tap('你')
assert editor()=='你'
tap('Undo（重新選字）');assert editor()=='of'
configure('候選展開');tap('候選展開');tap('O，人');time.sleep(1)
assert any(n.get('class')=='android.widget.ScrollView' and '逐字選擇' in ET.tostring(n,encoding='unicode') for n in tree().iter('node')) or find('指定英文段或返回自動判斷') is not None
shot('03-expanded')
(out/'result.txt').write_text('PASS: default clipboard, no toolbar keyboard switch, explicit refresh/history, paste, deletion/clear, sensitive/password exclusion, settings choices, next-input candidate expansion.\n')
