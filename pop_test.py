"""pop_test.py — 最小验证：attach → 排队 → 点好友按钮 → 读结果和日志。"""
import base64
import json
import subprocess
import sys
import time

sys.path.insert(0, r".")
from pet_bot import enc_str, dec_pb, fmt  # noqa: E402
import pet_bot  # noqa: E402
import frida  # noqa: E402

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
PET_ID = "MTAwMDAwMDAwMDA="

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
pid = next((p.pid for p in dev.enumerate_processes() if p.name == "QQ"), None)
print("QQ pid:", pid)
session = dev.attach(pid)
with open(r".\driver_lite.js", encoding="utf-8") as f:
    script = session.create_script(f.read())
script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}"))
script.on("message", lambda m, d: print(f"[js-ERR] {json.dumps(m, ensure_ascii=False)[:200]}"))
script.load()
time.sleep(2)

inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
payload = pet_bot.envelope(inner, "OidbSvcTrpcTcp.0x9acb_0", 0)
q = json.loads(script.exports_sync.request("OidbSvcTrpcTcp.0x9acb_0",
                                           base64.b64encode(payload).decode()))
print("queued:", q)

# 点好友按钮（宠物主页）
subprocess.run([ADB, "-s", SERIAL, "shell", "input tap 1144 1360"], timeout=15)
print("tapped friend btn")

deadline = time.time() + 15
while time.time() < deadline:
    r = json.loads(script.exports_sync.result())
    if r and (r.get("sent") or r.get("err")):
        break
    time.sleep(0.4)

# 等响应
time.sleep(3)
r = json.loads(script.exports_sync.result())
print("=== RESULT ===")
for k, v in r.items():
    if isinstance(v, str) and len(v) > 90:
        v = v[:90] + "..."
    print(" ", k, "=", v)
if r.get("respB64"):
    print("--- decoded ---")
    print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2000])

print("=== RESP LOG ===")
for e in json.loads(script.exports_sync.resplog())[-12:]:
    b = (e.get("b64") or "")[:36]
    print(" ", e.get("ts"), e.get("who"), "code=", e.get("code"), e.get("sig"), b)
# 回宠物主页
subprocess.run([ADB, "-s", SERIAL, "shell", "input keyevent KEYCODE_BACK"], timeout=15)
