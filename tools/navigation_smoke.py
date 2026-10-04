"""Exercise the actual IME above both navigation modes on an Android emulator."""
import subprocess, shlex, time, re, pathlib, xml.etree.ElementTree as ET
out=pathlib.Path("navigation-evidence");out.mkdir(exist_ok=True)
def adb(*args):
    if args and args[0]=="shell": args=("shell",shlex.join(args[1:]))
    return subprocess.check_output(["adb",*args],text=True,timeout=30)
def tree():
    adb("shell","uiautomator","dump","--windows","/sdcard/nav.xml")
    return ET.fromstring(adb("shell","cat","/sdcard/nav.xml"))
def bounds(n): return tuple(map(int,re.findall(r"-?\d+",n.get("bounds"))))
def find(nodes,desc): return next((n for n in nodes.iter("node") if n.get("content-desc")==desc),None)
def tap(nodes,desc):
    n=find(nodes,desc);assert n is not None,desc
    a,b,c,d=bounds(n);adb("shell","input","tap",str((a+c)//2),str((b+d)//2));time.sleep(1)
def shot(name):
    with (out/(name+".png")).open("wb") as f: subprocess.run(["adb","exec-out","screencap","-p"],stdout=f,check=True)
def safe_bottom(nodes):
    frames=[bounds(n) for n in nodes.iter("node") if "navigation_bar_frame" in n.get("resource-id","")]
    frames=[b for b in frames if b[3]>b[1] and b[2]>b[0]]
    if frames: return min(b[1] for b in frames)
    dump=adb("shell","dumpsys","window","displays")
    (out/"window-insets.txt").write_text(dump)
    frames=[]
    for line in dump.splitlines():
        if "navigationBars" not in line and "ITYPE_NAVIGATION_BAR" not in line: continue
        m=re.search(r"frame=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]",line)
        if m:
            b=tuple(map(int,m.groups()))
            if b[3]>b[1] and b[2]>b[0]: frames.append(b)
    assert frames,"No actual navigation bounds found"
    return min(b[1] for b in frames)
def check(name,descs):
    nodes=tree();bottom=safe_bottom(nodes)
    for desc in descs:
        n=find(nodes,desc);assert n is not None,name+" missing "+desc
        b=bounds(n);assert b[3]<=bottom,(name,desc,b,bottom)
    shot(name);(out/(name+".xml")).write_text(ET.tostring(nodes,encoding="unicode"))
import sys
def failure(kind,value,tb):
    try:
        shot("failure")
        (out/"failure.xml").write_text(ET.tostring(tree(),encoding="unicode"))
        (out/"failure-logcat.txt").write_text(adb("logcat","-d"))
    except Exception: pass
    sys.__excepthook__(kind,value,tb)
sys.excepthook=failure
adb("shell","settings","put","secure","show_ime_with_hard_keyboard","1")
adb("install","-r","app/build/outputs/apk/debug/app-debug.apk")
ime=None
for _ in range(30):
    ime=next((x.strip() for x in adb("shell","ime","list","-a","-s").splitlines() if "hk.kaiboard.android" in x),None)
    if ime: break
    time.sleep(1)
assert ime,"Installed input method was not registered"
adb("shell","ime","enable",ime);adb("shell","ime","set",ime)
for mode in ("threebutton","gestural"):
    adb("shell","cmd","overlay","enable-exclusive","--category","com.android.internal.systemui.navbar."+mode)
    time.sleep(2)
    adb("shell","ime","set",ime)
    adb("shell","am","start","--activity-single-top","-n","hk.kaiboard.android/.KeyboardPreviewActivity","--es","test_text","__EMPTY__")
    time.sleep(4)
    for _ in range(15):
        nodes = tree()
        prompt = next((x for x in nodes.iter("node") if x.get("text") in ("GOT IT","Got it")),None)
        if prompt is not None:
            a,b,c,d=bounds(prompt);adb("shell","input","tap",str((a+c)//2),str((b+d)//2));time.sleep(1);continue
        if find(nodes,"空白鍵，左右滑動移動游標") is not None:break
        editor=next((x for x in nodes.iter("node") if x.get("class")=="android.widget.EditText"),None)
        if editor is not None:
            a,b,c,d=bounds(editor);adb("shell","input","tap",str((a+c)//2),str((b+d)//2))
        time.sleep(1)
    check(mode+"-keyboard",["切換中英文，長按選擇系統鍵盤","空白鍵，左右滑動移動游標","逗號，長按快捷標點","句號，長按快捷標點"])
    nodes=tree();tap(nodes,"切換中英文，長按選擇系統鍵盤")
    check(mode+"-english",["切換中英文，長按選擇系統鍵盤","空白鍵，左右滑動移動游標"])
    tap(tree(),"切換中英文，長按選擇系統鍵盤")
    tap(tree(),"文字編輯")
    check(mode+"-editor",["移到文字開頭","移到文字結尾","刪除選取文字或前一個字"])
    tap(tree(),"返回鍵盤")
    check(mode+"-restored",["空白鍵，左右滑動移動游標"])
    tap(tree(),"剪貼簿")
    check(mode+"-clipboard",["返回鍵盤","更新剪貼簿","清空剪貼簿暫存"])
    tap(tree(),"返回鍵盤")
(out/"result.txt").write_text("PASS: Chinese, English, text editor and restored keyboard above actual three-button and gesture navigation bounds. Physical OEM acceptance remains a device check.")
