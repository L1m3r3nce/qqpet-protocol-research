"""对比：我构造的信封 vs 真实捕获的信封。"""
import base64
import json

from pet_bot import dec_pb, fmt, envelope, enc_str, enc_int, PET_ID_B64

MY_B64 = "CMu1AhAAGAAiQgooTVRFeU1EWXdNakV5TlMwMExUSXRNVGM0TlRFMk56VTBNVGcyTmc9PRIWMDEwMzA0MDUwODA5MGIwZjBhMGUwZDIOYW5kcm9pZCA5LjMuNzBaJHFxLXRyYW5zCmNvbXBvc2VfdmVyc2lvbj0xLjAuMF9kZWJ1Zw=="

with open(r"G:\plugin_qq\pb_capture.json", encoding="utf-8") as f:
    entries = json.load(f)
real = None
for e in entries:
    if e["kind"] == "REQ" and (e["cmd"] or "").endswith("0x9acb_0") and e["b64"]:
        real = e["b64"][0]
        break

mine = base64.b64decode(MY_B64)
realb = base64.b64decode(real)

print("== MINE (%dB) ==" % len(mine))
print(mine.hex())
print(fmt(dec_pb(mine)))
print()
print("== REAL (%dB) ==" % len(realb))
print(realb.hex())
print(fmt(dec_pb(realb)))
