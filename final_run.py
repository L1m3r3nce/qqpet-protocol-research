"""final_run.py — 一体化最后一击（严格时序，无守护进程依赖）：
force-stop QQ → 冷启动 → 等登录 → find_penguin 开宠物页 → 排队 → 收下/学习载体 → 读结果。
"""
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


def sh(cmd, t=20):
    subprocess.run([ADB, "-s", SERIAL, "shell", cmd], capture_output=True, timeout=t)


def run_py(script, t=120):
    r = subprocess.run(["python", script], capture_output=True, timeout=t)
    return r.stdout.decode("utf-8", "replace").strip()


# 1. 干净重启 QQ
sh("am force-stop com.tencent.mobileqq")
time.sleep(4)
sh("am start -n com.tencent.mobileqq/.activity.SplashActivity")
print("QQ launched, waiting for load...")
time.sleep(18)

# 2. attach + 装钩（本次会话全程保持到读出结果）
dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
pid = next((p.pid for p in dev.enumerate_processes() if p.name == "QQ"), None)
print("QQ pid:", pid)
session = dev.attach(pid)
with open(r".\driver_lite.js", encoding="utf-8") as f:
    script = session.create_script(f.read())
script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}"))
script.on("message", lambda m, d: print(f"[js-ERR] {json.dumps(m, ensure_ascii=False)[:150]}"))
script.load()
time.sleep(2)

# 3. 先排队（页面爆发之前！）
inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
payload = pet_bot.envelope(inner, "OidbSvcTrpcTcp.0x9acb_0", 0)
q = json.loads(script.exports_sync.request("OidbSvcTrpcTcp.0x9acb_0",
                                           base64.b64encode(payload).decode()))
print("queued:", q)

# 4. 开宠物页（爆发即载体）
print(run_py(r".\find_penguin.py")[-60:])
time.sleep(3)

# 6. 等
deadline = time.time() + 20
while time.time() < deadline:
    r = json.loads(script.exports_sync.result())
    if r and (r.get("respB64") or r.get("err")):
        break
    time.sleep(0.5)
time.sleep(3)

# 7. 结果
r = json.loads(script.exports_sync.result())
print("=== RESULT ===")
for k, v in r.items():
    if isinstance(v, str) and len(v) > 100:
        v = v[:100] + "..."
    print(" ", k, "=", v)
if r.get("respB64"):
    print("=== !!! DECODED RESPONSE !!! ===")
    print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:3000])

print("=== RESP LOG (tail) ===")
log = json.loads(script.exports_sync.resplog())
with open(r".\final_resplog.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=1)
for e in log[-14:]:
    b = (e.get("b64") or "")[:60]
    print(" ", e.get("ts"), e.get("who"), "code=", e.get("code"), e.get("sig"), b)
print(f"full log saved: {len(log)} entries")
