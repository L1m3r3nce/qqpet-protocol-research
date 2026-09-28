"""探查 Reqable LMDB: 子库、非数字键、值格式。"""
import lmdb

env = lmdb.open(r".\reqable_data\box\data.mdb",
                readonly=True, lock=False, subdir=False, max_dbs=16)

for name in [b"records", b"record", b"captures", b"capture", b"req", b"http",
             b"main", b"data", b"box", b"entries", b"meta", b"index"]:
    try:
        db = env.open_db(name)
        stat = env.begin(db=db).stat()
        if stat["entries"]:
            print("SUBDB", name, stat["entries"], "entries")
    except Exception:
        pass

txn = env.begin()
cur = txn.cursor()
shown = 0
total = 0
if cur.first():
    while True:
        total += 1
        k = cur.key()
        # 数字型键是 8 字节递增/计数器；其余可能是记录键
        if len(k) != 8:
            print("KEY:", repr(k[:60]), "VAL:", repr(cur.value()[:50]))
            shown += 1
            if shown >= 20:
                break
        if not cur.next():
            break
print("total scanned:", total, "non-8byte keys shown:", shown)
