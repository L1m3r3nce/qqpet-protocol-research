"""raw_replay.py — 用 raw 模式重放抓包的原始心跳信封。"""
import json
import os
import time

CMD_FILE = r".\cmd.json"
RESP_FILE = r".\resp.json"

with open(r".\pb_capture.json", encoding="utf-8") as f:
    entries = json.load(f)
hb = None
for e in entries:
    if e["kind"] == "REQ" and (e["cmd"] or "").endswith("0x9875_1") and e["b64"]:
        hb = e["b64"][0]
        break
print("replaying captured heartbeat:", hb[:50], "...")

if os.path.exists(RESP_FILE):
    os.remove(RESP_FILE)
json.dump({"cmd": "OidbSvcTrpcTcp.0x9875_1", "raw_b64": hb, "wait": 60}, open(CMD_FILE, "w"))

deadline = time.time() + 70
while time.time() < deadline:
    if os.path.exists(RESP_FILE):
        r = json.load(open(RESP_FILE, encoding="utf-8"))
        for k, v in r.items():
            if isinstance(v, str) and len(v) > 100:
                v = v[:100] + "..."
            if k == "resps":
                v = f"[{len(v)} events]"
            print(" ", k, "=", v)
        if r.get("respB64"):
            import base64
            import sys
            sys.path.insert(0, r".")
            from pet_bot import dec_pb, fmt
            print("--- decoded response ---")
            print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2000])
        break
    time.sleep(0.5)
else:
    print("no result in 70s")
