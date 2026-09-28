"""loop_test.py — 排队命令后循环制造载体流量（好友页开关），等待搭车。"""
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


def sh(cmd):
    subprocess.run([ADB, "-s", SERIAL, "shell", cmd], timeout=15)


inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
job = {
    "cmd": "OidbSvcTrpcTcp.0x9acb_0",
    "inner_b64": base64.b64encode(inner).decode(),
    "etype": 0,
    "wait": 100,
}
if os.path.exists(RESP_FILE):
    os.remove(RESP_FILE)
json.dump(job, open(CMD_FILE, "w"))
print("queued; pumping carrier for up to 110s")

start = time.time()
pump = True
while time.time() - start < 110:
    if pump:
        sh("input tap 1144 1360")   # 好友按钮
        time.sleep(4)
        sh("input keyevent KEYCODE_BACK")  # 回宠物主页
        time.sleep(3)
    if os.path.exists(RESP_FILE):
        r = json.load(open(RESP_FILE, encoding="utf-8"))
        print("GOT RESULT:")
        for k, v in r.items():
            if isinstance(v, str) and len(v) > 120:
                v = v[:120] + "..."
            print(" ", k, "=", v)
        if r.get("respB64"):
            print("--- decoded ---")
            print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2500])
        break
else:
    print("still no result after pumping")
