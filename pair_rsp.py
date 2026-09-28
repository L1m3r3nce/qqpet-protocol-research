"""按顺序配对 REQ/RSP，解码关键命令的响应。"""
import base64
import json

from decode_pb import decode_pb, pretty


def deep_fix(obj):
    if isinstance(obj, dict):
        return {k: [deep_fix(v) for v in vs] for k, vs in obj.items()}
    if isinstance(obj, list):
        return [deep_fix(v) for v in obj]
    if isinstance(obj, (bytes,)):
        return obj.hex()
    if isinstance(obj, str):
        return obj
    return obj


with open(r".\pb_capture.json", encoding="utf-8") as f:
    entries = json.load(f)

# RSP 的 b64 存在 entries 里；按时间配对最近的同序 REQ
FOCUS = {"0x9b60_1": "START_STUDY", "0x9ab2_1": "STATUS_POLL", "0x975e_1": "COURSE_QUERY",
         "0x985d_0": "FRIEND_LIST", "0x9acb_0": "PET_STATE"}

reqs = [e for e in entries if e["kind"] == "REQ" and e.get("b64")]
rsps = [e for e in entries if e["kind"] == "RSP" and e.get("b64")]

# 打印每个 FOCUS 命令的第一个 REQ 和紧跟其后的 RSP
used = set()
for i, r in enumerate(reqs):
    short = (r["cmd"] or "").split(".")[-1]
    if short not in FOCUS or id(r) in used:
        continue
    # 找时间上第一个晚于该 REQ 且未使用的 RSP
    cand = None
    for j, s in enumerate(rsps):
        if id(s) not in used and s["ts"] >= r["ts"]:
            cand = s
            break
    if not cand:
        continue
    used.add(id(r))
    used.add(id(cand))
    print(f"########## {FOCUS[short]} {short} REQ@{r['ts']} RSP@{cand['ts']} ##########")
    raw = base64.b64decode(r["b64"][0])
    print("--- REQ ---")
    print(pretty(decode_pb(raw))[:800])
    raw2 = base64.b64decode(cand["b64"][0])
    print("--- RSP (%dB) ---" % len(raw2))
    try:
        print(pretty(decode_pb(raw2))[:2500])
    except Exception as ex:
        print("fail", ex)
    print()
