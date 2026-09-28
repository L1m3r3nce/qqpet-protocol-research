"""按 § 分隔符统计模块调用 + 输出关键模块完整明细。"""
import re
from collections import Counter

LOG = r"G:\plugin_qq\phaseA_log.txt"

pairs = Counter()
details = []
FOCUS = ("AIProductModule", "AICommonModule", "QQPetModule", "EGPetDataModule",
         "VasKuiklyModule", "HRBridgeModule")

with open(LOG, encoding="utf-8") as f:
    for line in f:
        if "[MOD 13:4" not in line and "[MOD 13:5" not in line:
            continue
        if "->" in line:
            continue
        idx = line.find("a=[")
        if idx < 0:
            continue
        payload = line[idx + 3:].rstrip("]\r\n")
        parts = [p.strip() for p in payload.split("§")]
        if len(parts) < 3:
            continue
        call_id, module, method = parts[0], parts[1], parts[2]
        pairs[f"{module}.{method}"] += 1
        if module in FOCUS:
            params = parts[3] if len(parts) > 3 else ""
            details.append((line.strip()[:26], module, method, params[:500]))

print("=== module.method ===")
for k, v in pairs.most_common(60):
    print(f"{v:5d}  {k}")

print(f"\n=== FOCUS details ({len(details)}) ===")
for ts, mod, meth, prm in details[:150]:
    print(f"{ts} {mod}.{meth}  {prm}")
