"""修复 driver_daemon.py 的 subprocess 作用域问题。"""
src = open(r".\driver_daemon.py", encoding="utf-8").read()

# 1. 顶部 import 确保
if "\nimport subprocess\n" not in src[:600]:
    src = src.replace("import os\nimport time", "import os\nimport subprocess\nimport time", 1)

# 2. 删除函数内的 import subprocess
needle = "try:\n                    import subprocess\n                    subprocess.run"
if needle in src:
    src = src.replace(needle, "try:\n                    subprocess.run")

open(r".\driver_daemon.py", "w", encoding="utf-8").write(src)

head = src[:600]
body = src[src.find("def main"):]
print("top import:", "import subprocess" in head)
print("inline in main():", "import subprocess" in body)
