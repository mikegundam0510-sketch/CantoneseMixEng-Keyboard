"""Exercise actual IME taps and post-commit phrase tails on a disposable emulator."""
import subprocess, shlex, time, xml.etree.ElementTree as ET, re, pathlib
out = pathlib.Path('ui-evidence'); out.mkdir(exist_ok=True)
def adb(*args):
    if args and args[0] == 'shell': args = ('shell', shlex.join(args[1:]))
    return subprocess.check_output(['adb', *args], text=True, timeout=30)
def tree():
    adb('shell', 'uiautomator', 'dump', '--windows', '/sdcard/predictions.xml')
    return ET.fromstring(adb('shell', 'cat', '/sdcard/predictions.xml'))
def node(label):
    return next((n for n in tree().iter('node') if n.get('content-desc') == label or n.get('text') == label), None)
def tap_node(n):
    assert n is not None, 'Missing control'
    x1,y1,x2,y2 = map(int, re.findall(r'\d+', n.get('bounds')))
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2)); time.sleep(.5)
def tap(label): tap_node(node(label))
def text():
    return next(n.get('text','') for n in tree().iter('node') if n.get('class') == 'android.widget.EditText')
def reset(value='__EMPTY__', kind='normal'):
    adb('shell','am','start','--activity-single-top','-n','hk.kaiboard.android/.KeyboardPreviewActivity',
        '--es','test_text',value,'--es','test_input_type',kind)
    time.sleep(1)
def shot(name):
    with (out/(name+'.png')).open('wb') as f:
        subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
adb('shell','am','start','-n','hk.kaiboard.android/.SettingsActivity'); time.sleep(1)
for _ in range(10):
    setting = node('輸入完成後顯示聯想字')
    if setting is not None: break
    adb('shell','input','swipe','400','650','400','300','250'); time.sleep(.3)
assert setting is not None, 'Suggestion setting missing'
if setting.get('checked') != 'true': tap_node(setting)
# Pure Cangjie mode: the two input systems share letter keys and can both be enabled.
for _ in range(10):
    quick = node('速成（首尾碼）')
    if quick is not None: break
    adb('shell','input','swipe','400','300','400','650','250'); time.sleep(.3)
assert quick is not None, 'Quick preference missing'
if quick.get('checked') == 'true': tap_node(quick)
adb('shell','input','keyevent','4'); time.sleep(.5)
reset()
radicals = dict(zip('abcdefghijklmnopqrstuvwxyz','日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重'))
# Explicit map avoids any fixture typo in the rare X radical.
radicals['x'] = '難'; radicals['y'] = '卜'; radicals['z'] = '重'
for c in 'onf': tap(c.upper()+'，'+radicals[c])
tap('空白鍵，左右滑動移動游標')
assert text() == '你', 'Cangjie space must commit highlighted candidate without adding whitespace'
assert node('聯想字') is not None, 'Suggestions hidden after space confirmation'
shot('18-cangjie-space')
reset('研究')
assert node('一下') is not None, 'HK phrase continuation missing'
tap('一下'); assert text() == '研究一下', 'Suggestion duplicated the existing prefix'
shot('19-next-phrase')
reset('研究一'); tap('下'); assert text() == '研究一下', 'Chained next-character insertion failed'
reset('研究'); tap('空白鍵，左右滑動移動游標')
assert text() == '研究 ', 'Idle space must insert space instead of auto-accepting a suggestion'
assert node('聯想字') is None, 'Whitespace must dismiss predictions'
reset('研究。'); assert node('聯想字') is None, 'Punctuation boundary leaked predictions'
reset('研究'); tap('O，人')
assert node('聯想字') is None, 'New code must replace post-commit predictions'
reset('研究', 'private'); assert node('聯想字') is None, 'Private field leaked contextual predictions'
reset('研究', 'password'); assert node('聯想字') is None, 'Password field leaked predictions'
reset()
adb('shell','am','start','-n','hk.kaiboard.android/.SettingsActivity'); time.sleep(1)
for _ in range(10):
    quick = node('速成（首尾碼）')
    if quick is not None: break
    adb('shell','input','swipe','400','300','400','650','250'); time.sleep(.3)
assert quick is not None
if quick.get('checked') != 'true': tap_node(quick)
adb('shell','input','keyevent','4')
(out/'predictions-result.txt').write_text('PASS: Cangjie space commit, post-commit suggestions, HK phrase tails, chained insertion, idle space, punctuation/new-code dismissal and private/password fields.\n')
print('Post-commit suggestion UI checks passed', flush=True)
