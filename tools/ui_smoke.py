"""UI smoke test on a disposable Android emulator. Saves actual screenshots."""
import subprocess, time, xml.etree.ElementTree as ET, re, pathlib
out=pathlib.Path("ui-evidence");out.mkdir(exist_ok=True)
def adb(*args):
    return subprocess.check_output(["adb",*args],text=True,timeout=30)
def tree():
    for _ in range(3):
        try:
            adb("shell","uiautomator","dump","/sdcard/window.xml")
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
adb("shell","settings","put","secure","show_ime_with_hard_keyboard","1")
adb("install","-r","apk/app-debug.apk")
ime=None
for _ in range(20):
    ime=next((line.strip() for line in adb("shell","ime","list","-s").splitlines() if "hk.kaiboard.android" in line),None)
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
(out/"result.txt").write_text("PASS: keyboard launch, continuous category jump, scroll-driven selection, skin-tone popup and emoji commit.\n",encoding="utf-8")
