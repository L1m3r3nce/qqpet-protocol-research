"""读取 Reqable 的 LMDB 元数据库，列出抓包记录的 URL/方法/状态。

Reqable 的 box/data.mdb: LMDB 格式，值大概率是 msgpack 编码的记录元数据。
"""
import json
import sys

import lmdb
import msgpack

DB = r".\reqable_data\box\data.mdb"

env = lmdb.open(DB, readonly=True, lock=False, subdir=False, max_dbs=8)
txn = env.begin()

n_decoded = 0
n_raw = 0
records = []

with txn.cursor() as cur:
    if not cur.first():
        print("EMPTY DB")
        sys.exit(0)
    while True:
        key = cur.key()
        val = cur.value()
        try:
            obj = msgpack.unpackb(val, raw=False, strict_map_key=False)
            n_decoded += 1
            if isinstance(obj, dict):
                records.append((key, obj))
        except Exception:
            n_raw += 1
        if not cur.next():
            break

print(f"decoded={n_decoded} raw={n_raw}")

def deep_find(obj, keys, depth=0):
    """在嵌套结构中找指定键名的值。"""
    out = {}
    if depth > 6 or not isinstance(obj, (dict, list)):
        return out
    items = obj.items() if isinstance(obj, dict) else enumerate(obj)
    for k, v in items:
        if isinstance(k, str):
            for want in keys:
                if want in k.lower():
                    out.setdefault(k, v if not isinstance(v, (dict, list)) else type(v).__name__)
        out.update(deep_find(v, keys, depth + 1))
    return out

for key, obj in records:
    hits = deep_find(obj, ("host", "path", "url", "method", "status", "scheme"))
    print("KEY:", key[:40], "|", json.dumps(hits, ensure_ascii=False, default=str)[:400])
