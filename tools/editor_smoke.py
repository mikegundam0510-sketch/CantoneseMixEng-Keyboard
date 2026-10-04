"""UI smoke test on a disposable Android emulator. Saves actual screenshots."""
import subprocess, shlex, time, xml.etree.ElementTree as ET, re, pathlib
out=pathlib.Path("ui-evidence");out.mkdir(exist_ok=True)
def adb(*args):
    if args and args[0] == "shell": args = ("shell", shlex.join(args[1:]))
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
    print("UI checkpoint: "+name,flush=True)
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
ime = None
for _ in range(20):
    ime = next((line.strip() for line in adb("shell","ime","list","-a","-s").splitlines() if "hk.kaiboard.android" in line), None)
    if ime: break
    time.sleep(1)
assert ime, "Editor smoke input method registration timed out"
adb("shell","ime","enable",ime);adb("shell","ime","set",ime)
adb("shell","am","start","-n","hk.kaiboard.android/.KeyboardPreviewActivity")
time.sleep(3)
for _ in range(15):
    if find("文字編輯") is not None: break
    if adb("shell","settings","get","secure","default_input_method").strip() != ime:
        adb("shell","ime","enable",ime); adb("shell","ime","set",ime)
    nodes = tree()
    editor = next((n for n in nodes.iter("node") if n.get("class") == "android.widget.EditText"), None)
    if editor is not None: adb("shell","input","tap",*center(editor))
    time.sleep(1)
assert adb("shell","settings","get","secure","default_input_method").strip() == ime, "Editor smoke lost selected IME"
assert find("文字編輯") is not None, "Editor smoke keyboard did not open"
radicals=dict(zip("abcdefghijklmnopqrstuvwxyz", "日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重"))
def reset_field(value="__EMPTY__"):
    adb("shell","am","start","--activity-single-top","-n","hk.kaiboard.android/.KeyboardPreviewActivity","--es","test_text",value)
    time.sleep(1)
def type_code(code):
    nodes=tree()
    positions={n.get("content-desc"):center(n) for n in nodes.iter("node") if n.get("content-desc") and n.get("bounds")}
    for char in code:
        adb("shell","input","tap",*positions[char.upper()+"，"+radicals[char.lower()]])
        time.sleep(.08)
    time.sleep(.8)
def editor_text():
    return next(n.get("text","") for n in tree().iter("node") if n.get("class")=="android.widget.EditText")
def long_tap(desc):
    x,y=center(find(desc));adb("shell","input","swipe",x,y,x,y,"800");time.sleep(.4)
def tap_text(value):
    node=next((n for n in tree().iter("node") if n.get("text")==value),None)
    adb("shell","input","tap",*center(node));time.sleep(.4)
# Bottom globe toggles English/mixed without using the toolbar.
reset_field();tap("切換中英文，長按選擇系統鍵盤")
assert find("O，人") is None, "Globe did not switch to direct English"
node=next(n for n in tree().iter("node") if n.get("text")=="o" or n.get("text")=="O")
adb("shell","input","tap",*center(node));time.sleep(.3)
assert editor_text()=="o", "Direct English globe mode failed"
tap("切換中英文，長按選擇系統鍵盤")
assert find("O，人") is not None, "Globe did not return to mixed input"
# Edit panel: switch the fixture back to multiline before testing vertical arrows.
adb("shell","am","start","--activity-single-top","-n","hk.kaiboard.android/.KeyboardPreviewActivity","--es","test_text","__EMPTY__","--es","test_input_type","normal")
time.sleep(1)
# Select with keyboard arrows, copy/paste and delete.
reset_field("香港Hello");tap("文字編輯");shot("17-text-editor")
tap("移到文字開頭");tap("開始或停止選取文字");tap("游標向右");tap("游標向右")
tap("複製選取文字");tap("開始或停止選取文字");tap("移到文字結尾");tap("貼上文字")
assert editor_text()=="香港Hello香港", "Arrow selection/copy/paste failed"
tap("全部選取");tap("刪除選取文字或前一個字")
assert editor_text()=="", "Select all/delete failed"
tap("貼上文字");assert editor_text()=="香港", "Copy contents or paste changed"
tap("返回鍵盤");assert find("O，人") is not None, "Editing back button lost keyboard"
reset_field("甲\n乙\n丙");tap("文字編輯");tap("移到文字開頭");tap("游標向下")
tap("刪除選取文字或前一個字")
assert editor_text()=="甲乙\n丙", "Down movement did not preserve column"
tap("移到文字結尾");tap("游標向上");tap("刪除選取文字或前一個字")
assert editor_text()=="乙\n丙", "Up movement did not preserve column"
tap("返回鍵盤")
reset_field("甲\n乙\n丙");tap("文字編輯");tap("移到文字開頭");tap("開始或停止選取文字");tap("游標向下")
tap("複製選取文字");tap("開始或停止選取文字");tap("移到文字結尾");tap("貼上文字")
assert editor_text()=="甲\n乙\n丙甲\n", "Vertical selection/copy failed"
tap("返回鍵盤")
reset_field("abcd");tap("文字編輯");tap("移到文字開頭");long_tap("游標向右");tap("刪除選取文字或前一個字")
assert editor_text()=="abc", "Held arrow did not repeat or failed to stop"
tap("返回鍵盤")
reset_field("A😀B");tap("文字編輯");tap("游標向左");tap("開始或停止選取文字");tap("游標向左")
tap("刪除選取文字或前一個字")
assert editor_text()=="AB", "Selection split a supplementary character"
shot("18-text-editor-selected");tap("返回鍵盤")
(out/"android-meminfo.txt").write_text(adb("shell","dumpsys","meminfo","hk.kaiboard.android"))
(out/"editor-result.txt").write_text("PASS: globe direct English/mixed; direct arrow selection/copy/paste; select all/delete; multiline up/down; supplementary character selection/delete.\n")
reset_field()
