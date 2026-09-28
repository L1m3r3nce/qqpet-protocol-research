"""解码 final_run 捕获的全部响应，找出我的状态查询结果。"""
import base64
import json
import sys

sys.path.insert(0, r"G:\plugin_qq")
from pet_bot import dec_pb, fmt

r = {"resplog": json.load(open(r"G:\plugin_qq\final_resplog.json", encoding="utf-8"))}
for i, e in enumerate(r.get("resplog") or []):
    if not e.get("b64"):
        continue
    try:
        raw = base64.b64decode(e["b64"])
        d = dec_pb(raw)
        s = fmt(d)
        # 找特征：pet state 的响应含 pkey 或我的宠物ID
        marker = ""
        if "pkey" in s or "MTEyMDYw" in s:
            marker = "  <<<<< 宠物状态候选!"
        print(f"--- [{i}] {e['ts']} {e['who']} code={e.get('code')} {len(raw)}B{marker}")
        print(s[:600])
        print()
    except Exception as ex:
        print(f"--- [{i}] decode fail {ex}")
