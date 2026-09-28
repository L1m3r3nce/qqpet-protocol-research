"""burst_test.py — 严格顺序：排队 → 开宠物页（爆发流量载搭车）→ 收结果。"""
import base64
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, r"G:\plugin_qq")
from pet_bot import enc_str, enc_int, dec_pb, fmt  # noqa: E402

ADB = r"G:\software\adb\scrcpy-win64-v3.3.3\scrcpy-win64-v3.3.3\adb.exe"
SERIAL = "0A241FDD4005G7"
PET_ID = "MTEyMDYwMjEyNS00LTItMTc4NTE2NzU0MTg2Ng"
CMD_FILE = r"G:\plugin_qq\cmd.json"
RESP_FILE = r"G:\plugin_qq\resp.json"


def sh(cmd):
    subprocess.run([ADB, "-s", SERIAL, "shell", cmd], timeout=15)


mode = sys.argv[1] if len(sys.argv) > 1 else "state"

inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
if mode == "study":
    sinner = enc_int(1, 6100) + enc_str(2, PET_ID) + enc_int(10, 0) + enc_int(11, 3)
    job = {"cmd": "OidbSvcTrpcTcp.0x9ab2_1",
           "inner_b64": base64.b64encode(sinner).decode(), "etype": 1, "wait": 100}
else:
    job = {"cmd": "OidbSvcTrpcTcp.0x9acb_0",
           "inner_b64": base64.b64encode(inner).decode(), "etype": 0, "wait": 100}

if os.path.exists(RESP_FILE):
    os.remove(RESP_FILE)
json.dump(job, open(CMD_FILE, "w"))
print(f"[1] queued {mode} job (wait=100s)")

time.sleep(1.5)
# 先回主页（如果当前在宠物页，先退出再进，保证有开页爆发）
sh("input keyevent KEYCODE_BACK")
time.sleep(2)
print("[2] opening pet page (burst carrier)...")
r = subprocess.run(["python", r"G:\plugin_qq\find_penguin.py"], capture_output=True, timeout=90)
print(r.stdout.decode("utf-8", "replace").strip()[-200:])

print("[3] polling result...")
deadline = time.time() + 100
while time.time() < deadline:
    if os.path.exists(RESP_FILE):
        res = json.load(open(RESP_FILE, encoding="utf-8"))
        for k, v in res.items():
            if isinstance(v, str) and len(v) > 120:
                v = v[:120] + "..."
            print(" ", k, "=", v)
        if res.get("respB64"):
            print("--- decoded ---")
            print(fmt(dec_pb(base64.b64decode(res["respB64"])))[:2500])
        break
    time.sleep(0.5)
else:
    print("no result")
