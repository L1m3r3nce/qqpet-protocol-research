"""full_test.py — 完整链路：排队 state 命令 → 点好友按钮造载体 → 读结果。"""
import base64
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, r".")
from pet_bot import enc_str, dec_pb, fmt  # noqa: E402

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
PET_ID = "MTAwMDAwMDAwMDA="

CMD_FILE = r".\cmd.json"
RESP_FILE = r".\resp.json"

inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
job = {
    "cmd": "OidbSvcTrpcTcp.0x9acb_0",
    "inner_b64": base64.b64encode(inner).decode(),
    "etype": 0,
    "wait": 30,
}

if os.path.exists(RESP_FILE):
    os.remove(RESP_FILE)
json.dump(job, open(CMD_FILE, "w"))
print("queued state job")

time.sleep(1)
subprocess.run([ADB, "-s", SERIAL, "shell", "input tap 1144 1360"], timeout=15)
print("carrier tapped (friend button)")

deadline = time.time() + 35
while time.time() < deadline:
    if os.path.exists(RESP_FILE):
        r = json.load(open(RESP_FILE, encoding="utf-8"))
        for k, v in r.items():
            if isinstance(v, str) and len(v) > 120:
                v = v[:120] + "..."
            if k in ("paths",):
                v = f"[{len(v)} entries]"
            print(k, "=", v)
        if r.get("respB64"):
            print("--- decoded ---")
            print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2500])
        break
    time.sleep(0.5)
else:
    print("timeout waiting resp")
