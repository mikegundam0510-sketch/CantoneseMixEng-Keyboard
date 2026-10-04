"""UI smoke test on a disposable Android emulator. Saves actual screenshots."""
import subprocess, shlex, time, xml.etree.ElementTree as ET, re, pathlib
out=pathlib.Path("symbol-evidence");out.mkdir(exist_ok=True)
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
def tap_text(label):
    node=next((n for n in tree().iter("node") if n.get("text")==label and n.get("clickable")=="true"),None)
    adb("shell","input","tap",*center(node));time.sleep(.5)
def shot(name):
    print("UI checkpoint: "+name,flush=True)
    with (out/(name+".png")).open("wb") as f:subprocess.run(["adb","exec-out","screencap","-p"],stdout=f,check=True)

adb("shell","settings","put","secure","show_ime_with_hard_keyboard","1")
adb("install","-r","apk/app-debug.apk")
ime=None
for _ in range(30):
    ime=next((line.strip() for line in adb("shell","ime","list","-a","-s").splitlines() if "hk.kaiboard.android" in line),None)
    if ime: break
    time.sleep(1)
assert ime,"Installed input method did not register"
adb("shell","ime","enable",ime);adb("shell","ime","set",ime)
def reset_field(value="x"):
    adb("shell","am","start","--activity-single-top","-n","hk.kaiboard.android/.KeyboardPreviewActivity")
    time.sleep(1)
    adb("shell","am","start","--activity-single-top","-n","hk.kaiboard.android/.KeyboardPreviewActivity","--es","test_text",value,"--es","test_input_type","normal")
    time.sleep(2)
    for _ in range(20):
        nodes=tree()
        if any(n.get("text")=="123" and n.get("clickable")=="true" for n in nodes.iter("node")): return
        prompt=next((n for n in nodes.iter("node") if n.get("text") in ("GOT IT","Got it")),None)
        editor=next((n for n in nodes.iter("node") if n.get("class")=="android.widget.EditText"),None)
        node=prompt if prompt is not None else editor
        if node is not None: adb("shell","input","tap",*center(node))
        time.sleep(1)
    shot("missing-keyboard")
    (out/"missing-keyboard.xml").write_text(ET.tostring(tree(),encoding="unicode"))
    raise AssertionError("Keyboard did not become ready")
def editor_text():
    return next(n.get("text","") for n in tree().iter("node") if n.get("class")=="android.widget.EditText")
for name,size in (("cover","720x1600"),("unfolded","1440x1800")):
    adb("shell","wm","size",size);adb("shell","wm","density","320");time.sleep(2)
    # Symbol layout: question immediately left of Delete, bottom comma/dot and longer space.
    reset_field("x");tap_text("123")
    delete=find("刪除，長按連續刪除")
    bx,by=map(int,center(delete))
    questions=[n for n in tree().iter("node") if n.get("text")=="?" and n.get("clickable")=="true"]
    left=min(questions,key=lambda n:abs(int(center(n)[0])-bx))
    qx,qy=map(int,center(left))
    assert qx<bx and abs(qy-by)<5, "Question mark is not immediately left of Backspace"
    adb("shell","input","tap",str(qx),str(qy));time.sleep(.4)
    assert editor_text()=="x?", "Question key output is incorrect"
    tap("刪除，長按連續刪除")
    assert editor_text()=="x", "Moved Backspace did not delete"
    comma=find("逗號，長按快捷標點");period=find("句號，長按快捷標點")
    cx,cy=map(int,center(comma));px,py=map(int,center(period))
    space=find("空白鍵，左右滑動移動游標")
    sx,sy=map(int,center(space))
    assert comma.get("text")=="," and period.get("text")==".", "Symbol bottom punctuation must be comma and ASCII dot"
    assert sx<cx<px and abs(cy-py)<5 and cy>by, "Bottom punctuation order is incorrect"
    sb=list(map(int,re.findall(r"\d+",space.get("bounds"))))
    cb=list(map(int,re.findall(r"\d+",comma.get("bounds"))))
    assert sb[2]-sb[0]>4*(cb[2]-cb[0]), "Symbol spacebar is too short"
    assert not any(n.get("text")=="。" and n.get("clickable")=="true" for n in tree().iter("node")), "Chinese full-stop key still present"
    tap("逗號，長按快捷標點");tap("句號，長按快捷標點")
    assert editor_text()=="x,.", "Bottom comma/dot output is incorrect"
    shot(name+"-symbols")
    tap_text("#+=")
    assert find("刪除，長按連續刪除") is not None, "Extra-symbol page lost Backspace"
    tap("刪除，長按連續刪除")
    assert editor_text()=="x,", "Extra-symbol Backspace did not delete"
    tap_text("ABC")
    
(out/"result.txt").write_text("PASS: cover/unfolded symbol question left of Backspace; moved delete works; long spacebar; comma and ASCII period labels/output; no Chinese full-stop key; extra-symbol delete.\n")
