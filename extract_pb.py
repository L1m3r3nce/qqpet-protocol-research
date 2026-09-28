"""提取所有 sendPbRequest 调用的完整参数（cmd + 载荷）。"""
import re

LOG = r"G:\plugin_qq\phaseA_log.txt"

out = []
with open(LOG, encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "sendPbRequest" not in line or "->" in line:
        continue
    idx = line.find("a=[")
    payload = line[idx + 3:].rstrip("]\r\n") if idx >= 0 else line
    ts = line.strip()[:26]
    out.append(f"REQ  {ts}\n     {payload[:1200]}")
    # 找紧随其前的响应行（-> 开头）
    if i + 1 < len(lines) and "->" in lines[i + 1]:
        out.append(f"RESP {lines[i+1].strip()[:900]}")

print(f"total sendPbRequest: {len([o for o in out if o.startswith('REQ')])}")
print("=" * 80)
for o in out:
    print(o)
