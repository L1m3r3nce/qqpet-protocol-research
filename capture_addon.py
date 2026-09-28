"""mitmproxy addon: 把经过代理的 HTTP(S) 流量记录成 JSONL，便于离线分析 QQ 宠物接口。

用法: mitmdump -s capture_addon.py --listen-host 0.0.0.0 --listen-port 8080
输出: ./capture_flows.jsonl
"""
import json
import time
from pathlib import Path

OUT = Path(r".\capture_flows.jsonl")
MAX_BODY = 20000  # 每条请求/响应体最多记录的字符数

# 噪音域名直接跳过（系统服务、广告、统计等），让抓包文件干净些
SKIP_HOSTS = (
    "msa.baidu.com", "mis.hicloud.com", "nds.mtk.com", "connectivitycheck",
    "gmsorg.baidu.com", "sugar.a1.petal.com", "metrics", "report", "logs.",
    "ot.gdhtqh.com", "data.flurry.com", "app-measurement.com", "crashlytics",
)


def _clip(text):
    if not text:
        return ""
    return text[:MAX_BODY]


def response(flow):
    host = flow.request.pretty_host
    if any(s in host for s in SKIP_HOSTS):
        return
    try:
        resp_body = flow.response.get_text(strict=False) or ""
    except Exception:
        resp_body = "<binary %d bytes>" % len(flow.response.content)
    rec = {
        "ts": time.time(),
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": host,
        "req_headers": dict(flow.request.headers),
        "req_body": _clip(flow.request.get_text(strict=False) or ""),
        "status": flow.response.status_code,
        "resp_headers": dict(flow.response.headers),
        "resp_body": _clip(resp_body),
    }
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def error(flow):
    host = getattr(flow, "server_conn", None)
    hname = host.address[0] if host and host.address else ""
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.time(),
            "method": "?",
            "url": getattr(flow, "client_conn", None) and "" or "",
            "host": hname,
            "error": str(getattr(flow, "error", "")),
        }, ensure_ascii=False) + "\n")
