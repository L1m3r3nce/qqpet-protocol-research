import urllib.request

for path in ["/", "/api", "/records", "/doc", "/status"]:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:12312" + path, timeout=3)
        print(path, r.status, r.read()[:200])
    except Exception as e:
        print(path, "ERR", str(e)[:100])
