"""二次解码：把 hex 字段串再递归解 protobuf，聚焦学习/好友命令。"""
import base64
import json
import re

from decode_pb import decode_pb, pretty  # 复用解码器


def deep_fix(obj):
    """把输出里的 hex 串再试着解一次 pb / utf-8 / base64。"""
    if isinstance(obj, dict):
        return {k: [deep_fix(v) for v in vs] for k, vs in obj.items()}
    if isinstance(obj, list):
        return [deep_fix(v) for v in obj]
    if isinstance(obj, str) and re.fullmatch(r"(?:[0-9a-f]{2}){4,}", obj or ""):
        raw = bytes.fromhex(obj)
        # 试 utf-8
        try:
            s = raw.decode("utf-8")
            if sum(1 for c in s if c.isprintable()) >= len(s) * 0.9:
                return s
        except UnicodeDecodeError:
            pass
        # 试 pb
        try:
            d = decode_pb(raw)
            if d and all(int(k) < 64 for k in d):
                return deep_fix(d)
        except Exception:
            pass
        return obj
    return obj


def b64try(s):
    """字符串像是 base64 就尝试解。"""
    if isinstance(s, str) and len(s) >= 20 and re.fullmatch(r"[A-Za-z0-9+/_=-]+", s):
        pad = s.replace("-", "+").replace("_", "/")
        pad += "=" * (-len(pad) % 4)
        try:
            raw = base64.b64decode(pad)
            t = raw.decode("utf-8")
            if sum(1 for c in t if c.isprintable()) >= len(t) * 0.8:
                return f"{s} => b64:{t}"
        except Exception:
            pass
    return s


def annotate(obj):
    if isinstance(obj, dict):
        return {k: [annotate(v) for v in vs] for k, vs in obj.items()}
    if isinstance(obj, list):
        return [annotate(v) for v in obj]
    if isinstance(obj, str):
        return b64try(obj)
    return obj


with open(r".\pb_capture.json", encoding="utf-8") as f:
    entries = json.load(f)

FOCUS = ("0x9b60_1", "0x9ab2_1", "0x975e_1", "0x985d_0", "0x975c_1", "0x975f_1", "0x9760_1", "0x96a6_1")
for e in entries:
    if e["kind"] != "REQ" or not e["cmd"] or not e["b64"]:
        continue
    short = e["cmd"].split(".")[-1]
    if short not in FOCUS:
        continue
    if not (e["ts"] >= "14:03:00" and e["ts"] <= "14:05:00"):
        continue
    raw = base64.b64decode(e["b64"][0])
    try:
        d = annotate(deep_fix(decode_pb(raw)))
        print(f"===== {e['ts']} {short} ({len(raw)}B) =====")
        print(pretty(d))
        print()
    except Exception as ex:
        print(f"===== {e['ts']} {short} FAIL: {ex}")
