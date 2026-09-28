import base64
import json

from pet_bot import dec_pb, fmt

r = json.load(open(r".\resp.json", encoding="utf-8"))
for resp in (r.get("responses") or []):
    print("==", resp.get("ts"), "cbId=", resp.get("cbId"))
    if resp.get("b64"):
        try:
            print(fmt(dec_pb(base64.b64decode(resp["b64"])))[:600])
        except Exception as e:
            print("  decode fail", e)
