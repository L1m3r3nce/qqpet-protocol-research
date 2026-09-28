"""find_penguin.py — 像素级定位企鹅并双击。

企鹅特征：深蓝色主体（睡衣+帽子），在浅色背景上。
裁剪 Q宠 容器区域 -> 找蓝紫色暗像素 -> 质心 -> 立刻双击。
"""
import subprocess
import sys
import time

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
SHOT = r".\peng.png"

# Q宠 容器（uiautomator 确认过的主页悬浮窗区域，放宽一些）
BOX = (900, 1650, 1080, 2260)


def sh(cmd, timeout=20):
    return subprocess.run([ADB, "-s", SERIAL, "shell", cmd], capture_output=True, timeout=timeout)


def screenshot():
    with open(SHOT, "wb") as f:
        p = subprocess.run([ADB, "-s", SERIAL, "exec-out", "screencap", "-p"],
                           capture_output=True, timeout=20)
        f.write(p.stdout)


def find_penguin():
    from PIL import Image
    img = Image.open(SHOT).convert("RGB")
    x0, y0, x1, y1 = BOX
    crop = img.crop((x0, y0, x1, y1))
    w, h = crop.size
    px = crop.load()
    sx = sy = n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            # 深蓝/藏青色系：蓝明显高于红，且整体偏暗
            if b > r + 25 and b > 60 and r < 140 and g < 140:
                sx += x
                sy += y
                n += 1
    if n < 20:
        return None
    return (x0 + sx // n, y0 + sy // n, n)


def on_qq_main(xml):
    """保险丝：只有确认在QQ消息主页（有Q宠节点）才允许点击。"""
    return 'content-desc="Q宠' in xml


def main():
    for attempt in range(6):
        # 先验证页面：必须能看到 Q宠 节点才继续
        r = subprocess.run([ADB, "-s", SERIAL, "shell",
                            "uiautomator dump /sdcard/ui.xml 2>&1"], capture_output=True, timeout=30)
        xml = subprocess.run([ADB, "-s", SERIAL, "shell", "cat /sdcard/ui.xml"],
                             capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
        if not on_qq_main(xml):
            print(f"[{attempt}] NOT on QQ main page (no Q宠 node) — skip, no tapping")
            time.sleep(1.5)
            continue
        screenshot()
        pos = find_penguin()
        if not pos:
            print(f"[{attempt}] no blue blob found")
            time.sleep(1.5)
            continue
        x, y, n = pos
        print(f"[{attempt}] penguin blob n={n} at ({x},{y}) -> double-tap")
        sh(f"input tap {x} {y}")
        time.sleep(0.12)
        sh(f"input tap {x} {y}")
        time.sleep(4)
        # 验证：宠物页打开后主界面 Q宠 节点消失/或出现喂食按钮
        r = subprocess.run([ADB, "-s", SERIAL, "shell",
                            "uiautomator dump /sdcard/ui.xml 2>&1"], capture_output=True, timeout=30)
        xml = subprocess.run([ADB, "-s", SERIAL, "shell", "cat /sdcard/ui.xml"],
                             capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
        if 'content-desc="Q宠' not in xml:
            print("PET PAGE OPENED")
            return 0
        print("not open yet, retry")
    return 1


if __name__ == "__main__":
    sys.exit(main())
