"""live_watch.py — 打工期间观察响应路径：轮询 qstatus 的 responses(P钩) 完整内容。"""
import json
import os
import time

CMD = r".\cmd.json"
RESP = r".\resp.json"

for round_ in range(3):
    if os.path.exists(RESP):
        os.remove(RESP)
    json.dump({"special": "status"}, open(CMD, "w"))
    deadline = time.time() + 10
    while time.time() < deadline:
        if os.path.exists(RESP):
            r = json.load(open(RESP, encoding="utf-8"))
            print(f"=== round {round_} status: {r.get('status')} ===")
            for resp in (r.get("responses") or []):
                b = resp.get("b64")
                print(" ", resp.get("ts"), resp.get("cbId"), ("B64:" + b[:50]) if b else "")
            break
        time.sleep(0.5)
    time.sleep(6)
