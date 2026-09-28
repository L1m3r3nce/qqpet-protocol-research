"""open_pet.py — 通过 uiautomator dump 找 Q宠容器 并点击打开宠物页。"""
import subprocess
import sys
import time

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"


def sh(cmd, timeout=30):
    r = subprocess.run([ADB, "-s", SERIAL, "shell", cmd], capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace")


def on_pet_home(xml):
    """宠物主页的特征节点（Kuikly 暴露的无障碍描述）。"""
    for kw in ("喂食", "洗澡", "好友"):
        if f'content-desc="{kw}' in xml or f'text="{kw}' in xml:
            return True
    return False


def open_pet(retries=4):
    for _ in range(retries):
        out = sh("uiautomator dump /sdcard/ui.xml 2>&1")
        if "dumped" not in out:
            time.sleep(2)
            continue
        xml = sh("cat /sdcard/ui.xml")
        import re

        if on_pet_home(xml):
            print("already on pet home")
            return True

        # 回访列表页等：返回键即回宠物主页
        if "回访" in xml:
            print("on visit-list page, pressing BACK to pet home")
            sh("input keyevent KEYCODE_BACK")
            time.sleep(3)
            out = sh("uiautomator dump /sdcard/ui.xml 2>&1")
            if "dumped" in out:
                xml = sh("cat /sdcard/ui.xml")
                if on_pet_home(xml):
                    print("pet home OPENED via BACK")
                    return True

        # 主页：找 Q宠 容器点击
        m = re.search(r'content-desc="Q宠[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if not m:
            print("no Q宠 node on this page")
            time.sleep(2)
            continue
        x = (int(m.group(1)) + int(m.group(3))) // 2
        y = (int(m.group(2)) + int(m.group(4))) // 2
        print(f"Q宠 at [{m.group(1)},{m.group(2)}][{m.group(3)},{m.group(4)}], tapping ({x},{y})")
        sh(f"input tap {x} {y}")
        time.sleep(4)
        out = sh("uiautomator dump /sdcard/ui.xml 2>&1")
        if "dumped" in out:
            xml2 = sh("cat /sdcard/ui.xml")
            if on_pet_home(xml2):
                print("pet home OPENED via tap")
                return True
        print("retrying...")
    return False


if __name__ == "__main__":
    ok = open_pet()
    sys.exit(0 if ok else 1)
