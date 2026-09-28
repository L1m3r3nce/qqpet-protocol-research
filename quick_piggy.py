"""quick_piggy.py — 一体化搭车测试（无守护进程，单会话）。"""
import base64
import json
import subprocess
import sys
import time

sys.path.insert(0, r".")
from pet_bot import enc_str, enc_int, dec_pb, fmt  # noqa: E402

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
PET_ID = "MTAwMDAwMDAwMDA="

import frida  # noqa: E402

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
pid = next((p.pid for p in dev.enumerate_processes() if p.name == "QQ"), None)
print("QQ pid:", pid)
session = dev.attach(pid)
with open(r".\driver.js", encoding="utf-8") as f:
    script = session.create_script(f.read())
script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}"))
script.load()
time.sleep(2)

mode = sys.argv[1] if len(sys.argv) > 1 else "state"
if mode == "state":
    inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
    cmd, etype = "OidbSvcTrpcTcp.0x9acb_0", 0
elif mode == "study_status":
    inner = enc_int(1, 6100) + enc_str(2, PET_ID) + enc_int(10, 0) + enc_int(11, 3)
    cmd, etype = "OidbSvcTrpcTcp.0x9ab2_1", 1
elif mode == "start_study":
    inner = enc_int(1, 6100) + enc_str(2, PET_ID)
    cmd, etype = "OidbSvcTrpcTcp.0x9b60_1", 1
else:
    raise SystemExit("unknown mode")

payload_b64 = base64.b64encode(__import__("pet_bot").envelope(inner, cmd, etype)).decode()
q = json.loads(script.exports_sync.request(cmd, payload_b64))
print("queued:", q)

# 载体：点好友按钮（当前应在宠物主页）
subprocess.run([ADB, "-s", SERIAL, "shell", "input tap 1144 1360"], timeout=15)
print("carrier tapped")

deadline = time.time() + 20
while time.time() < deadline:
    r = json.loads(script.exports_sync.result())
    if r and (r.get("sent") or r.get("err")):
        print("RESULT:", json.dumps({k: (v[:60] if isinstance(v, str) else v) for k, v in r.items()}, ensure_ascii=False)[:500])
        if r.get("respB64"):
            print("--- decoded ---")
            print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2000])
        break
    time.sleep(0.5)
else:
    print("no send within 20s")
    paths = json.loads(script.exports_sync.paths())
    print("paths tail:", paths[-6:])
