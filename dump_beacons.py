import pathlib

for f in sorted(pathlib.Path(r"G:\plugin_qq\reqable_data\capture").glob("*req_raw*")):
    print("=====", f.name)
    print(f.read_bytes().decode("utf-8", errors="replace"))
    print()
