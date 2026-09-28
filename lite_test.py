"""lite_test.py — 差分实验 runner：driver_lite + 一次搭车 + 完整响应观察。"""
import base64
import json
import subprocess
import sys
import time

sys.path.insert(0, r"G:\plugin_qq")
from pet_bot import enc_str, dec_pb, fmt  # noqa: E402

ADB = r"G:\software\adb\scrcpy-win64-v3.3.3\scrcpy-win64-v3.3.3\adb.exe"
SERIAL = "0A241FDD4005G7"
PET_ID = "MTEyMDYwMjEyNS00LTItMTc4NTE2NzU0MTg2Ng"

import frida  # noqa: E402

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
pid = next((p.pid for p in dev.enumerate_processes() if p.name == "QQ"), None)
print("QQ pid:", pid)
session = dev.attach(pid)
with open(r"G:\plugin_qq\driver_lite.js", encoding="utf-8") as f:
    script = session.create_script(f.read())
script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}"))
script.on("message", lambda m, d: print(f"[js-ERR] {json.dumps(m, ensure_ascii=False)[:300]}"))
script.load()
time.sleep(2)

# 1. 排队状态查询（先排队！）
inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
import pet_bot  # noqa: E402
payload = pet_bot.envelope(inner, "OidbSvcTrpcTcp.0x9acb_0", 0)
q = json.loads(script.exports_sync.request("OidbSvcTrpcTcp.0x9acb_0",
                                           base64.b64encode(payload).decode()))
print("queued:", q)

# 2. burst 载体：退出宠物页 → 重新双击进入（开页爆发）
subprocess.run([ADB, "-s", SERIAL, "shell", "input keyevent KEYCODE_BACK"], timeout=15)
time.sleep(2)
print("reopening pet page (burst carrier)...")
r = subprocess.run(["python", r"G:\plugin_qq\find_penguin.py"], capture_output=True, timeout=90)
print(r.stdout.decode("utf-8", "replace").strip()[-80:])

# 轮询结果 + 日志
deadline = time.time() + 25
while time.time() < deadline:
    r = json.loads(script.exports_sync.result())
    if r and (r.get("respB64") or r.get("err")):
        break
    time.sleep(0.5)

print("=== RESULT ===")
r = json.loads(script.exports_sync.result())
for k, v in r.items():
    if isinstance(v, str) and len(v) > 90:
        v = v[:90] + "..."
    print(" ", k, "=", v)
if r.get("respB64"):
    print("--- decoded ---")
    print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2000])

print("=== RESP LOG (last 15) ===")
for e in json.loads(script.exports_sync.resplog())[-15:]:
    b = (e.get("b64") or "")[:40]
    print(" ", e.get("ts"), e.get("who"), "code=", e.get("code"), e.get("sig"), b)
