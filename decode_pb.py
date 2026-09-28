"""极简 protobuf wire-format 解码器 + 解码捕获的宠物请求。"""
import base64
import json


def decode_pb(data, depth=0):
    """递归解码 protobuf wire format -> 嵌套 dict/list。"""
    out = {}
    i = 0
    n = len(data)
    while i < n:
        try:
            tag, i = read_varint(data, i)
        except IndexError:
            break
        field, wt = tag >> 3, tag & 7
        if field == 0:
            break
        if wt == 0:  # varint
            v, i = read_varint(data, i)
            val = v
        elif wt == 2:  # length-delimited
            ln, i = read_varint(data, i)
            raw = data[i:i + ln]
            i += ln
            val = try_decode_nested(raw, depth)
        elif wt == 5:  # 32-bit
            val = int.from_bytes(data[i:i + 4], "little")
            i += 4
        elif wt == 1:  # 64-bit
            val = int.from_bytes(data[i:i + 8], "little")
            i += 8
        else:
            break
        out.setdefault(str(field), []).append(val)
    return out


def read_varint(data, i):
    result = 0
    shift = 0
    while True:
        b = data[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7
        if i >= len(data):
            raise IndexError


def try_decode_nested(raw, depth):
    """尝试把 bytes 解成 utf-8 字符串或嵌套 pb，都不行就给 hex。"""
    if depth > 6 or not raw:
        return raw.hex()
    try:
        s = raw.decode("utf-8")
        # 大部分可打印且没有控制字符才算字符串
        printable = sum(1 for c in s if c.isprintable() or c in "\n\t")
        if printable >= len(s) * 0.9:
            return s
    except UnicodeDecodeError:
        pass
    try:
        nested = decode_pb(raw, depth + 1)
        if nested and valid_nested(nested):
            return nested
    except Exception:
        pass
    return raw.hex()


def valid_nested(obj):
    """粗略判断解出的嵌套是否合理（字段号都小于 64）。"""
    try:
        return all(int(k) < 64 for k in obj.keys())
    except Exception:
        return False


def pretty(obj, indent=0):
    pad = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for k, vs in obj.items():
            for v in vs:
                lines.append(f"{pad}{k}: {pretty(v, indent + 1)}")
        return "\n" + "\n".join(lines) if lines else "{}"
    if isinstance(obj, list):
        return str(obj)
    if isinstance(obj, (int,)) and obj > 0xFFFFFF:
        return f"{obj} (0x{obj:x})"
    return str(obj)


# 解码学习窗口的命令
with open(r".\pb_capture.json", encoding="utf-8") as f:
    entries = json.load(f)

FOCUS_WINDOW = ("14:03:0", "14:03:1", "14:03:2", "14:03:3", "14:03:4", "14:04:")
for e in entries:
    if e["kind"] != "REQ" or not e["cmd"] or not e["b64"]:
        continue
    if not any(e["ts"].startswith(w) for w in FOCUS_WINDOW):
        continue
    if "Qzone" in e["cmd"]:
        continue
    for b in e["b64"][:1]:
        try:
            raw = base64.b64decode(b)
        except Exception:
            continue
        if len(raw) < 8:
            continue
        print(f"===== {e['ts']} {e['cmd']} ({len(raw)}B) =====")
        try:
            print(pretty(decode_pb(raw)))
        except Exception as ex:
            print("  decode fail:", ex)
        print()
