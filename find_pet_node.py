"""从 uiautomator dump 里找企鹅节点。"""
import re

xml = open(r".\ui.xml", encoding="utf-8").read()
print("size:", len(xml))

hits = 0
for m in re.finditer(r"<node[^>]*?>", xml):
    s = m.group(0)
    low = s.lower()
    if any(k in low for k in ("pet", "鹅", "qie", "goose")):
        b = re.search(r'bounds="\[[^\]]+\]\[[^\]]+\]"', s)
        d = re.search(r'(?:content-desc|text|resource-id)="[^"]*"', s)
        print("PET-NODE:", d.group(0) if d else "?", b.group(0) if b else "?")
        hits += 1
print("pet hits:", hits)

print("--- all content-desc nodes (first 30) ---")
n = 0
for m in re.finditer(r'<node[^>]*content-desc="([^"]{1,50})"[^>]*bounds="(\[[^\]]+\]\[[^\]]+\])"', xml):
    print(m.group(1), m.group(2))
    n += 1
    if n > 30:
        break
