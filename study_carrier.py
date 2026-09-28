"""study_carrier.py — 排队 → 点学习面板 → 读结果。"""
import base64
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, r".")
from pet_bot import enc_str  # noqa: E402
import pet_bot  # noqa: E402

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
PET_ID = "MTAwMDAwMDAwMDA="

inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
job = {
    "cmd": "OidbSvcTrpcTcp.0x9acb_0",
    "inner_b64": base64.b64encode(inner).decode(),
    "etype": 0,
    "wait": 40,
}
if os.path.exists(r".\resp.json"):
    os.remove(r".\resp.json")
json.dump(job, open(r".\cmd.json", "w"))
print("queued")
time.sleep(1)

# 点学习面板（宠物主页底部）
subprocess.run([ADB, "-s", SERIAL, "shell", "input tap 245 1890"], timeout=15)
print("tapped study panel")

deadline = time.time() + 45
while time.time() < deadline:
    if os.path.exists(r".\resp.json"):
        r = json.load(open(r".\resp.json", encoding="utf-8"))
        for k, v in r.items():
            if isinstance(v, str) and len(v) > 90:
                v = v[:90] + "..."
            print(" ", k, "=", v)
        if r.get("respB64"):
            from pet_bot import dec_pb, fmt
            print("--- decoded ---")
            print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2500])
        break
    time.sleep(0.5)
else:
    print("timeout")
