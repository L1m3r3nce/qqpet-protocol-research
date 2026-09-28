import base64
import json

from pet_bot import dec_pb, fmt

r = json.load(open(r".\resp.json", encoding="utf-8"))
for k, v in r.items():
    if k == "resps":
        continue
    if isinstance(v, str) and len(v) > 100:
        v = v[:100] + "..."
    print(k, "=", v)
print("resps count:", len(r.get("resps") or []))
if r.get("respB64"):
    print("--- decoded response ---")
    print(fmt(dec_pb(base64.b64decode(r["respB64"])))[:2500])
