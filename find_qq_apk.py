"""从 QQ 官网的 JS 资源里挖安卓 APK 直链。"""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

pages = [
    "https://im.qq.com/mobileqq/",
]
js_links = set()
apk_links = set()

for url in pages:
    try:
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    except Exception as e:
        print("fetch fail", url, e)
        continue
    for m in re.finditer(r'src="([^"]+\.js)"', html):
        link = m.group(1)
        if link.startswith("//"):
            link = "https:" + link
        elif link.startswith("/"):
            link = "https://im.qq.com" + link
        js_links.add(link)
    for m in re.finditer(r'https?://[^\s"\'<>]+?\.apk', html):
        apk_links.add(m.group(0))

print("js files:", len(js_links))
for link in sorted(js_links):
    print("JS:", link)

for link in sorted(js_links)[:15]:
    try:
        req = urllib.request.Request(link, headers=UA)
        js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        for m in re.finditer(r'https?://[^\s"\'\\]+?\.apk', js):
            apk_links.add(m.group(0))
        # 也抓 dldir 链接附近的版本号形态
        for m in re.finditer(r'["\']([^"\']*dldir[^"\']*\.(?:apk|ipa))["\']', js):
            apk_links.add(m.group(1))
    except Exception as e:
        print("js fetch fail", link, str(e)[:60])

print("--- APK links ---")
for a in sorted(apk_links):
    print(a)
