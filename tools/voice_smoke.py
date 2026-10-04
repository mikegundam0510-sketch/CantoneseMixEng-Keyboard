"""Recovery/cancellation checks on an emulator without on-device speech."""
import pathlib, subprocess, time, shlex, re, xml.etree.ElementTree as ET
out = pathlib.Path('voice-evidence'); out.mkdir(exist_ok=True)
def adb(*args):
    if args and args[0] == 'shell': args = ('shell', shlex.join(args[1:]))
    return subprocess.check_output(['adb', *args], text=True, timeout=30)
def tree():
    for _ in range(4):
        try:
            adb('shell', 'uiautomator', 'dump', '--windows', '/sdcard/voice.xml')
            return ET.fromstring(adb('shell', 'cat', '/sdcard/voice.xml'))
        except Exception: time.sleep(.5)
    raise AssertionError('UI dump unavailable')
def find(value):
    return next((n for n in tree().iter('node') if n.get('content-desc') == value or n.get('text') == value), None)
def tap(value):
    node = find(value); assert node is not None, 'Missing ' + value
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2)); time.sleep(.4)
def shot(name):
    with (out/(name+'.png')).open('wb') as f:
        subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
    (out/(name+'.xml')).write_text(ET.tostring(tree(),encoding='unicode'))
try:
    adb('install','-r','app/build/outputs/apk/debug/app-debug.apk')
    adb('shell','pm','grant','hk.kaiboard.android','android.permission.RECORD_AUDIO')
    adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
    ime = None
    for _ in range(30):
        ime = next((s.strip() for s in adb('shell','ime','list','-a','-s').splitlines() if 'hk.kaiboard.android' in s),None)
        if ime: break
        time.sleep(.5)
    assert ime
    adb('shell','ime','enable',ime); adb('shell','ime','set',ime)
    adb('shell','wm','size','720x1600'); adb('shell','wm','density','320')
    adb('shell','am','start','-n','hk.kaiboard.android/.KeyboardPreviewActivity'); time.sleep(2)
    if find('GOT IT') is not None: tap('GOT IT')
    for _ in range(30):
        if find('語音輸入') is not None: break
        time.sleep(.5)
    tap('語音輸入'); time.sleep(1)
    assert find('取消') is not None, 'Recovery dialog did not remain open'
    assert find('語音設定') is not None
    assert any('預設只用裝置內辨識' in n.get('text','') for n in tree().iter('node'))
    shot('recovery')
    tap('取消')
    assert find('語音設定') is None
    assert find('語音輸入') is not None
    assert find('停止語音輸入') is None
    tap('語音輸入'); assert find('取消') is not None
    tap('取消'); shot('cancelled')
    assert adb('shell','settings','get','secure','default_input_method').strip() == ime
    for kind in ('password','private'):
        adb('shell','am','start','--activity-single-top','-n','hk.kaiboard.android/.KeyboardPreviewActivity',
            '--es','test_text','__EMPTY__','--es','test_input_type',kind)
        time.sleep(1)
        node = find('語音輸入'); assert node is not None and node.get('enabled') == 'false'
    (out/'PASS.txt').write_text('Recovery dialog stayed visible; cancel restored keyboard; repeat did not start listening; sensitive editors disable voice.\n')
except Exception:
    try: shot('failure'); (out/'failure-logcat.txt').write_text(adb('logcat','-d'))
    except Exception: pass
    raise
