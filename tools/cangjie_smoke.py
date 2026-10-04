"""Use actual settings switches and IME keys to verify full Cangjie without Quick."""
import pathlib, re, subprocess, time, xml.etree.ElementTree as ET

out = pathlib.Path("ui-evidence")
out.mkdir(exist_ok=True)

def adb(*args):
    return subprocess.check_output(["adb", *args], text=True, timeout=30)

def tree():
    adb("shell", "uiautomator", "dump", "--windows", "/sdcard/cangjie.xml")
    return ET.fromstring(adb("shell", "cat", "/sdcard/cangjie.xml"))

def node(value, attr="content-desc"):
    return next((n for n in tree().iter("node") if n.get(attr) == value), None)

def tap(n):
    assert n is not None, "Control missing"
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", n.get("bounds")))
    adb("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))
    time.sleep(.25)

def shot(name):
    with (out / (name+".png")).open("wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, check=True)
    print("Cangjie checkpoint: " + name, flush=True)

def reset():
    adb("shell", "am", "start", "--activity-single-top", "-n",
        "hk.kaiboard.android/.KeyboardPreviewActivity", "--es", "test_text", "__EMPTY__",
        "--es", "test_input_type", "normal")
    time.sleep(1)

def editor():
    return next(n.get("text", "") for n in tree().iter("node")
                if n.get("class") == "android.widget.EditText")

radicals = dict(zip("abcdefghijklmnopqrstuvwxyz", "日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重"))

def type_code(code):
    for c in code:
        tap(node(c.upper()+"，"+radicals[c]))
    time.sleep(.6)

def settings(quick):
    adb("shell", "am", "start", "-n", "hk.kaiboard.android/.SettingsActivity")
    time.sleep(1)
    control = None
    for _ in range(10):
        control = node("速成（首尾碼）", "text")
        if control is not None:
            break
        time.sleep(1)
    assert control is not None, "Settings switch did not appear"
    if (control.get("checked") == "true") != quick:
        tap(control)
    assert node("速成（首尾碼）", "text").get("checked") == str(quick).lower()
    control = node("倉頡五代（完整字碼）", "text")
    assert control is not None
    if control.get("checked") != "true":
        tap(control)
    shot("cangjie-settings-" + ("quick-on" if quick else "quick-off"))

try:
    adb("shell", "settings", "put", "secure", "show_ime_with_hard_keyboard", "1")
    adb("install", "-r", "apk/app-debug.apk")
    ime = "hk.kaiboard.android/.KaiboardService"
    adb("shell", "ime", "enable", ime)
    adb("shell", "ime", "set", ime)
    settings(False)
    reset()
    # Wait for the actual offline dictionary; incomplete codes are not a load failure.
    for attempt in range(30):
        reset()
        type_code("onf")
        if node("你") is not None:
            break
        time.sleep(1)
    assert node("你") is not None, "ONF failed with Quick disabled"
    for code, character in (("onf", "你"), ("vnd", "好"), ("hda", "香"),
                            ("etcu", "港"), ("srlb", "屌")):
        reset()
        type_code(code)
        assert node(character) is not None, code+" has no full Cangjie candidate"
        shot("cangjie-"+code)
        tap(node(character))
        assert editor() == character, code+" did not commit selected character"
    reset()
    type_code("srb")
    assert node("屌") is None, "Incomplete code unexpectedly matched full code"
    shot("cangjie-srb-incomplete")
    # Inserting the missing L into the code must make the reported character available.
    tap(node("刪除，長按連續刪除"))
    type_code("lb")
    assert node("屌") is not None, "Correcting SRB to SRLB did not refresh candidates"
    tap(node("屌"))
    assert editor() == "屌"
    for name, size in (("cover", "720x1600"), ("unfolded", "1440x1800")):
        adb("shell", "wm", "size", size)
        adb("shell", "wm", "density", "320")
        time.sleep(2)
        reset()
        shot("cangjie-legend-"+name)
        type_code("srlb")
        assert node("屌") is not None, name+" Cangjie candidate missing"
        shot("cangjie-srlb-"+name)
    (out/"cangjie-result.txt").write_text(
        "PASS: real settings disabled Quick and enabled Cangjie; ONF/VND/HDA/ETCU/SRLB "
        "candidates and commits; SRB does not map to 屌; correcting SRB to SRLB refreshes "
        "candidates; cover/unfolded screenshots with inset English legends.\n", encoding="utf-8")
finally:
    adb("shell", "wm", "size", "reset")
    adb("shell", "wm", "density", "reset")
    settings(True)
    adb("shell", "am", "force-stop", "hk.kaiboard.android")
