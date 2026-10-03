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
assert any(n.get("text", "").upper()=="OFONAOVRMRQ" for n in tree().iter("node")), "Swiping accidentally committed a candidate"
shot("07-candidate-scroll")
adb("shell","input","swipe",str(bounds[0]+10),y,str(bounds[2]-10),y,"450");time.sleep(.5)
tap("你今日食咗咩")
assert any("你今日食咗咩" in n.get("text","") for n in tree().iter("node") if n.get("class")=="android.widget.EditText"), "Sentence not committed"
assert find("空白鍵，左右滑動移動游標") is not None, "Space icon lost accessibility description"
assert not any(n.get("text") in ("空格","空白") for n in tree().iter("node")), "Space key still has a word label"
shot("08-sentence-commit")
def reset_field(value="__EMPTY__"):
    adb("shell","am","start","--activity-single-top","-n","hk.kaiboard.android/.KeyboardPreviewActivity","--es","test_text",value)
    time.sleep(1)
def type_code(code):
    for char in code: tap(char.upper()+"，"+radicals[char.lower()])
def editor_text():
    return next(n.get("text","") for n in tree().iter("node") if n.get("class")=="android.widget.EditText")
def long_tap(desc):
    x,y=center(find(desc));adb("shell","input","swipe",x,y,x,y,"800");time.sleep(.4)
def tap_text(value):
    node=next((n for n in tree().iter("node") if n.get("text")==value),None)
    adb("shell","input","tap",*center(node));time.sleep(.4)
# Reopen the exact original codes, then change one segment without losing the rest.
tap("重新選字")
assert "ofonaovrmrq" in editor_text(), "Reselection did not restore the original code"
tap("分段改選")
tap("1 · 你")
tap("係")
assert "係今日食咗咩" in editor_text(), "Segment replacement changed other parts"
shot("09-segment-reselection")
# English space confirms literal input; repairs remain explicit choices.
reset_field();type_code("hello");tap("空白鍵，左右滑動移動游標")
assert editor_text()=="hello ", "English space did not confirm word and add exactly one space"
tap("重新選字")
assert editor_text()=="hello", "English reselection did not remove the confirmation space"
reset_field();type_code("hellp");tap("hello")
assert editor_text()=="hello", "English spelling suggestion was not committed"
# Explicit English fallback learns an unknown word for a later session.
reset_field();type_code("nebulon");tap("指定英文段或返回自動判斷");tap("空白鍵，左右滑動移動游標")
assert editor_text()=="nebulon ", "Forced English confirmation failed"
reset_field();type_code("nebulon");tap("空白鍵，左右滑動移動游標")
assert editor_text()=="nebulon ", "Learned English word was not recognized"
shot("10-english-space-learning")
# One buffer containing Chinese codes, a case-preserved brand, and more Chinese codes.
reset_field();type_code("onaovrrov")
tap("大寫，長按鎖定大寫");type_code("m");type_code("cdonaldrh")
tap("今日食唔食Mcdonald呀")
assert editor_text()=="今日食唔食Mcdonald呀", "Mixed sentence was not preserved"
shot("11-mixed-sentence")
# Pin persists across editor resets, and can be removed.
reset_field();type_code("of");long_tap("係");tap("置頂此候選")
strip=next(n for n in tree().iter("node") if n.get("class")=="android.widget.HorizontalScrollView")
assert next(n.get("text") for n in strip.iter("node") if n.get("class")=="android.widget.TextView")=="係", "Pinned candidate did not lead"
reset_field();type_code("of");long_tap("係");tap("取消置頂")
# Adjacent-key repair is shown separately and committed only after selection.
reset_field();type_code("od");tap("修正候選：你")
assert editor_text()=="你", "Quick typo suggestion failed"
# Long-press punctuation is usable without changing input method.
reset_field();long_tap("逗號，長按快捷標點");tap("？")
assert editor_text()=="？", "Quick punctuation failed"
# Drag over character keys moves the editor cursor, without inserting those keys.
reset_field("abcdefghij")
x1,y=center(find("O，人"));x2,_=center(find("W，田"))
adb("shell","input","swipe",x1,y,x2,y,"550");time.sleep(.5);tap_text("1")
assert editor_text()=="1abcdefghij", "Left key-area swipe did not move cursor or inserted an unwanted key"
x1,y=center(find("W，田"));x2,_=center(find("O，人"))
adb("shell","input","swipe",x1,y,x2,y,"550");time.sleep(.5);tap_text("2")
assert editor_text()=="1abcdefghij2", "Right key-area swipe did not move cursor"
assert find("重新選字").get("enabled")=="false", "Cursor movement did not disable stale reselection"
shot("12-cursor-swipes")
# The visual key gap belongs to the key touch target, including its outer edge.
reset_field()
key=find("O，人"); bounds=list(map(int,re.findall(r"\d+",key.get("bounds"))))
adb("shell","input","tap",str(bounds[0]+1),str((bounds[1]+bounds[3])//2))
time.sleep(.2)
assert editor_text()=="o", "Tap at key edge was dropped"
# Type without the half-second delay used by the rest of the acceptance checks.
reset_field()
nodes=tree(); positions={n.get("content-desc"):center(n) for n in nodes.iter("node") if n.get("content-desc") and n.get("bounds")}
code="ofonaovrmrq"
for char in code: adb("shell","input","tap",*positions[char.upper()+"，"+radicals[char]])
time.sleep(.8)
assert editor_text()==code, "Rapid real-key taps lost or reordered code"
assert find("你，先輸入此字並保留後續字碼") is not None, "Exact prefix fallback is missing"
tap("你，先輸入此字並保留後續字碼")
assert editor_text()=="你onaovrmrq", "Prefix choice discarded remaining codes"
# Outstanding searches must not restore candidates after moving to a fresh editor state.
reset_field()
assert find("你今日食咗咩") is None, "Stale async candidate survived editor reset"
shot("13-key-edges-rapid-input")
(out/"result.txt").write_text("PASS: emoji, candidate swipe, HK ranking, reselection/segment edit, English space/repair/learning, mixed sentence, pin/unpin, Quick typo repair, punctuation, key-area cursor swipes, key-edge taps, rapid key input, prefix selection and stale-search cancellation. Voice and Samsung/Fold hardware remain device checks.\n",encoding="utf-8")
