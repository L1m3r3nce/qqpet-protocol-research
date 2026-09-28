"""按时间排序所有 REQ/RSP，输出 cmd 时间线 + B64 存档。"""
import base64
import json
import re

LOG = r"G:\plugin_qq\phaseA_log.txt"

entries = []
with open(LOG, encoding="utf-8") as f:
    for line in f:
        m = re.search(r"\[(REQ|RSP) ([\d:.]+)\]", line)
        if not m:
            continue
        ts, kind = m.group(2), m.group(1)
        if not (ts.startswith("14:0") or ts.startswith("14:1")):
            continue
        cmd = None
        b64s = re.findall(r"B64:([A-Za-z0-9+/=]+)", line)
        m2 = re.search(r"\[(OidbSvcTrpcTcp\.0x[0-9a-f_]+|[A-Za-z0-9_.]+trpc[A-Za-z0-9_.]*)", line)
        if m2:
            cmd = m2.group(1)
        entries.append({"ts": ts, "kind": kind, "cmd": cmd, "b64": b64s})

# 时间线
print("=== timeline ===")
for e in entries:
    if e["kind"] == "REQ":
        sizes = [len(b) * 3 // 4 for b in e["b64"]]
        print(f"{e['ts']} REQ {e['cmd']}  pb_sizes={sizes}")

# 存档完整数据
with open(r"G:\plugin_qq\pb_capture.json", "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=1)
print("\nsaved", len(entries), "entries -> pb_capture.json")

# 唯一 cmd 列表
cmds = {}
for e in entries:
    if e["kind"] == "REQ" and e["cmd"]:
        cmds.setdefault(e["cmd"], 0)
        cmds[e["cmd"]] += 1
print("\n=== distinct REQ cmds ===")
for c, n in sorted(cmds.items(), key=lambda x: -x[1]):
    print(f"{n:4d}  {c}")
