"""spawn 模式启动 QQ 并注入 hook_pet.js（冷启动，早于 QQ 反调试初始化）。"""
import datetime
import json
import sys
import threading

import frida

LOG = r"G:\plugin_qq\hook_log.jsonl"


def on_message(message, data):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if message["type"] == "send":
        payload = message["payload"]
        line = {"ts": ts, **payload}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        if payload.get("pet"):
            print(f"[{ts}] *** PET {payload['tag']} {payload['cmd']} {str(payload.get('body'))[:200]}")
    elif message["type"] == "error":
        print(f"[{ts}] SCRIPT-ERROR {message.get('description')}")
    else:
        print(f"[{ts}] {message}")


def on_console(level, message):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][{level}] {message}")


def main():
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:4778")

    # 先杀干净 QQ
    try:
        dev.kill("QQ")
    except Exception:
        pass
    import time
    time.sleep(2)

    pid = dev.spawn(["com.tencent.mobileqq"])
    print("spawned QQ pid:", pid)
    session = dev.attach(pid)
    with open(r"G:\plugin_qq\hook_pet.js", encoding="utf-8") as f:
        src = f.read()
    script = session.create_script(src)
    script.on("message", on_message)
    script.set_log_handler(on_console)
    script.load()
    print("script loaded; resuming app")
    dev.resume(pid)
    print("resumed; logging to", LOG)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
