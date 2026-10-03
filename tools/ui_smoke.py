"""UI smoke test on a disposable Android emulator. Saves actual screenshots."""
import subprocess, time, xml.etree.ElementTree as ET, re, pathlib
out=pathlib.Path("ui-evidence");out.mkdir(exist_ok=True)
def adb(*args):
    return subprocess.check_output(["adb",*args],text=True,timeout=30)
def tree():
    for _ in range(3):
        try:
            adb("shell","uiautomator","dump","--windows","/sdcard/window.xml")
            return ET.fromstring(adb("shell","cat","/sdcard/window.xml"))
        except Exception: time.sleep(1)
    raise AssertionError("UI dump unavailable")
def find(desc):
    return next((n for n in tree().iter("node") if n.get("content-desc")==desc),None)
def center(node):
    assert node is not None,"Expected UI control missing"
    a=list(map(int,re.findall(r"\d+",node.get("bounds"))))
    return str((a[0]+a[2])//2),str((a[1]+a[3])//2)
def tap(desc):
    adb("shell","input","tap",*center(find(desc)));time.sleep(.5)
def shot(name):
    with (out/(name+".png")).open("wb") as f:subprocess.run(["adb","exec-out","screencap","-p"],stdout=f,check=True)
import sys
def failure(kind,value,tb):
    try:
        shot("failure")
        (out/"failure-logcat.txt").write_text(adb("logcat","-d"),encoding="utf-8")
        (out/"failure.xml").write_text(ET.tostring(tree(),encoding="unicode"),encoding="utf-8")
    except Exception: pass
    sys.__excepthook__(kind,value,tb)
sys.excepthook=failure
adb("shell","settings","put","secure","show_ime_with_hard_keyboard","1")
adb("install","-r","apk/app-debug.apk")
ime=None
for _ in range(20):
    ime=next((line.strip() for line in adb("shell","ime","list","-a","-s").splitlines() if "hk.kaiboard.android" in line),None)
    if ime: break
    time.sleep(1)
assert ime,"Installed input method was not registered"
print(adb("shell","ime","enable",ime),flush=True)
print(adb("shell","ime","set",ime),flush=True)
assert adb("shell","settings","get","secure","default_input_method").strip()==ime,"IME switch failed"
adb("shell","am","start","-n","hk.kaiboard.android/.KeyboardPreviewActivity")
time.sleep(3)
for _ in range(10):
    if find("Emoji") is not None: break
    nodes=tree()
    editor=next((n for n in nodes.iter("node") if n.get("class")=="android.widget.EditText"),None)
    if editor is not None:
        x,y=center(editor);adb("shell","input","tap",x,y)
    time.sleep(1)
(out/"startup.xml").write_text(ET.tostring(tree(),encoding="unicode"),encoding="utf-8")
(out/"logcat.txt").write_text(adb("logcat","-d"),encoding="utf-8")
shot("01-keyboard")
tap("Emoji")
shot("02-emoji")
tap("人物")
node=find("waving hand")
assert node is not None,"People section must start with waving hand"
x,y=center(node)
adb("shell","input","swipe",x,y,x,y,"800");time.sleep(.5)
shot("03-skin-tones")
tap("waving hand: medium skin tone")
assert any("👋🏽" in n.get("text","") for n in tree().iter("node")),"Skin-tone emoji not committed"
tap("旗幟")
assert find("旗幟").get("selected")=="true","Category jump not selected"
shot("04-flags")
tap("人物")
lst=next(n for n in tree().iter("node") if n.get("class")=="android.widget.ListView")
bounds=list(map(int,re.findall(r"\d+",lst.get("bounds"))))
x=str((bounds[0]+bounds[2])//2)
# Scroll backwards from People into Smileys; category highlight must follow.
for _ in range(3):
    adb("shell","input","swipe",x,str(bounds[1]+25),x,str(bounds[3]-25),"350");time.sleep(.4)
assert find("表情").get("selected")=="true","Scroll did not update current category"
shot("05-scroll-category")
# Exercise real key touches, whole-sentence ranking and the horizontal candidate strip.
tap("Emoji")
radicals=dict(zip("abcdefghijklmnopqrstuvwxyz", "日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重"))
for char in "ofonaovrmrq": tap(char.upper()+"，"+radicals[char])
first=find("你今日食咗咩")
assert first is not None, "HK sentence must lead the candidate strip"
shot("06-hk-candidates")
strip=next(n for n in tree().iter("node") if n.get("class")=="android.widget.HorizontalScrollView")
bounds=list(map(int,re.findall(r"\d+",strip.get("bounds"))))
y=str((bounds[1]+bounds[3])//2)
before=first.get("bounds")
adb("shell","input","swipe",str(bounds[2]-10),y,str(bounds[0]+10),y,"450");time.sleep(.5)
after=find("你今日食咗咩")
assert after is None or after.get("bounds") != before, "Candidate strip did not scroll"
assert any(n.get("text")=="OFONAOVRMRQ" for n in tree().iter("node")), "Swiping accidentally committed a candidate"
shot("07-candidate-scroll")
adb("shell","input","swipe",str(bounds[0]+10),y,str(bounds[2]-10),y,"450");time.sleep(.5)
tap("你今日食咗咩")
assert any("你今日食咗咩" in n.get("text","") for n in tree().iter("node") if n.get("class")=="android.widget.EditText"), "Sentence not committed"
assert find("空白鍵，左右滑動移動游標") is not None, "Space icon lost accessibility description"
assert not any(n.get("text") in ("空格","空白") for n in tree().iter("node")), "Space key still has a word label"
shot("08-sentence-commit")
(out/"result.txt").write_text("PASS: emoji browsing/tone insertion, HK sentence ranking/commit, candidate swipe without commit and icon space key. Voice and Samsung/Fold hardware remain device checks.\n",encoding="utf-8")
