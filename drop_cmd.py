"""drop_cmd.py — 往守护进程投递协议命令并等待结果。"""
import base64
import json
import os
import sys
import time

CMD_FILE = r"G:\plugin_qq\cmd.json"
RESP_FILE = r"G:\plugin_qq\resp.json"

PET_ID_B64 = "MTEyMDYwMjEyNS00LTItMTc4NTE2NzU0MTg2Ng"

from pet_bot import enc_str, enc_int, envelope  # noqa: E402

jobs = {
    "state": ("OidbSvcTrpcTcp.0x9acb_0",
              enc_str(1, PET_ID_B64) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d")), 0),
    "academy": ("OidbSvcTrpcTcp.0x975c_1", enc_int(1, 6000) + enc_str(2, PET_ID_B64), 1),
    "study_status": ("OidbSvcTrpcTcp.0x9ab2_1", enc_int(1, 6100) + enc_str(2, PET_ID_B64) + enc_int(10, 0) + enc_int(11, 3), 1),
}

name = sys.argv[1] if len(sys.argv) > 1 else "state"

if name == "carrier":
    # 自造载体：点好友按钮触发请求流
    import subprocess
    subprocess.run([r"G:\software\adb\scrcpy-win64-v3.3.3\scrcpy-win64-v3.3.3\adb.exe", "-s",
                    "0A241FDD4005G7", "shell", "input tap 1144 1360"], timeout=15)
    print("carrier tapped (friend button)")
    sys.exit(0)

cmd, inner, etype = jobs[name]

if os.path.exists(RESP_FILE):
    os.remove(RESP_FILE)
with open(CMD_FILE, "w", encoding="utf-8") as f:
    json.dump({"cmd": cmd, "inner_b64": base64.b64encode(inner).decode(), "etype": etype, "wait": 30}, f)
print(f"dropped job: {name} ({cmd}), waiting...")

deadline = time.time() + 40
while time.time() < deadline:
    if os.path.exists(RESP_FILE):
        with open(RESP_FILE, encoding="utf-8") as f:
            r = json.load(f)
        if r.get("respB64"):
            from pet_bot import dec_pb, fmt
            print("code:", r.get("respCode"), "msg:", r.get("respStr"))
            print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:3000])
        else:
            print("result:", json.dumps(r, ensure_ascii=False)[:500])
        break
    time.sleep(0.5)
else:
    print("no response within 40s")
