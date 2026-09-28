"""解析 Reqable 导出的 HAR：域名分布、URL 列表、找出 API 类请求。"""
import json
from collections import Counter
from urllib.parse import urlparse

with open(r"G:\plugin_qq\pet.har", encoding="utf-8") as f:
    har = json.load(f)

entries = har["log"]["entries"]
print("total entries:", len(entries))

hosts = Counter()
for e in entries:
    hosts[urlparse(e["request"]["url"]).netloc] += 1
print("--- hosts ---")
for h, c in hosts.most_common(40):
    print(f"{c:4d}  {h}")

print("--- entries (idx | method status | host | path | mime) ---")
for i, e in enumerate(entries):
    req = e["request"]
    res = e.get("response", {})
    u = urlparse(req["url"])
    mime = ""
    for h in res.get("headers", []):
        if h["name"].lower() == "content-type":
            mime = h["value"]
            break
    print(f"{i:3d} | {req['method']:4s} {res.get('status','-'):>3} | {u.netloc:35s} | {u.path[:80]:80s} | {mime[:40]}")
