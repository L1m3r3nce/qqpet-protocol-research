import json
import os
import time

CMD = r"G:\plugin_qq\cmd.json"
RESP = r"G:\plugin_qq\resp.json"

if os.path.exists(RESP):
    os.remove(RESP)
json.dump({"special": "status"}, open(CMD, "w"))
deadline = time.time() + 15
while time.time() < deadline:
    if os.path.exists(RESP):
        r = json.load(open(RESP, encoding="utf-8"))
        print("status:", r.get("status"))
        print("paths:", r.get("paths"))
        print("resps:", len(r.get("responses") or []))
        break
    time.sleep(0.5)
else:
    print("no resp")
