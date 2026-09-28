"""driver_daemon.py — 常驻驱动守护进程

- attach QQ + 加载 driver.js（会话永不主动断开，避免 hook 卸载把 QQ 搞崩）
- 监视命令文件 ./cmd.json，出现即执行搭车请求
- 结果写入 ./resp.json，然后删除 cmd.json

cmd.json 格式: {"cmd": "OidbSvcTrpcTcp.0x9b60_1", "inner_b64": "...", "etype": 1}
"""
import base64
import json
import os
import subprocess
import time

import frida

CMD_FILE = r".\cmd.json"
RESP_FILE = r".\resp.json"
ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
LOG = r".\daemon_log.txt"

logfile = open(LOG, "a", encoding="utf-8")


def w(line):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {line}")
    logfile.write(f"[{ts}] {line}\n")
    logfile.flush()


def build_envelope(inner_b64, cmd):
    """用 pet_bot 的信封逻辑（这里简化引入）"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pb", r".\pet_bot.py")
    pb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb)
    return pb


def main():
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
    w("daemon starting, waiting for QQ...")
    while True:
        pid = None
        for p in dev.enumerate_processes():
            if p.name == "QQ":
                pid = p.pid
                break
        if pid:
            break
        time.sleep(3)

    session = dev.attach(pid)
    w(f"attached QQ pid={pid}")
    with open(r".\driver_lite.js", encoding="utf-8") as f:
        src = f.read()
    script = session.create_script(src)
    script.set_log_handler(lambda lvl, msg: w(f"[js][{lvl}] {msg}"))
    script.on("message", lambda message, data: w(f"[js-ERR] {json.dumps(message, ensure_ascii=False)[:400]}"))
    script.load()
    w("driver loaded (carrier wait happens per-job)")

    lastPid = pid
    while True:
        try:
            # QQ 重启检测 → 重挂
            cur = None
            for p in dev.enumerate_processes():
                if p.name == "QQ":
                    cur = p.pid
                    break
            if cur != lastPid:
                w(f"QQ restarted {lastPid}->{cur}, reattaching...")
                if cur is None:
                    time.sleep(5)
                    continue
                session = dev.attach(cur)
                script = session.create_script(src)
                script.set_log_handler(lambda lvl, msg: w(f"[js][{lvl}] {msg}"))
                script.load()
                lastPid = cur
                w("reattached, auto-opening pet page...")
                # QQ 重启后宠物页会关：自动打开（带保险丝）；不阻塞等待——
                # 命令处理循环自己会泵载体（好友按钮开关）
                try:
                    subprocess.run(["python", r".\find_penguin.py"], timeout=90)
                except Exception as ex:
                    w(f"open_pet fail: {ex}")
                w("recovery done (non-blocking)")

            if os.path.exists(CMD_FILE):
                try:
                    with open(CMD_FILE, encoding="utf-8") as f:
                        job = json.load(f)
                except Exception as ex:
                    w(f"bad cmd file: {ex}")
                    os.remove(CMD_FILE)
                    continue
                os.remove(CMD_FILE)

                # 特殊任务：查询状态和路径
                if job.get("special") in ("status", "result"):
                    st = json.loads(script.exports_sync.status())
                    paths = json.loads(script.exports_sync.paths())
                    resps = json.loads(script.exports_sync.responses())
                    out = {"status": st, "paths": paths, "responses": resps}
                    if job.get("special") == "result":
                        out["pending"] = json.loads(script.exports_sync.result())
                    with open(RESP_FILE, "w", encoding="utf-8") as f:
                        json.dump(out, f, ensure_ascii=False)
                    w(f"special dumped: {st}")
                    continue

                w(f"job: {job.get('cmd')}")

                # raw 模式：直接发送完整信封字节（重放实验用）
                if job.get("raw_b64"):
                    b64 = job["raw_b64"]
                    cmd_name = job.get("cmd", "raw")
                else:
                    # 构造信封
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("pb", r".\pet_bot.py")
                    pb = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(pb)
                    inner = base64.b64decode(job["inner_b64"])
                    payload = pb.envelope(inner, job["cmd"], job.get("etype", 1))
                    b64 = base64.b64encode(payload).decode()

                script.exports_sync.reset()
                script.exports_sync.clearresps()
                q = json.loads(script.exports_sync.request(job["cmd"], b64))
                if not q.get("queued"):
                    with open(RESP_FILE, "w", encoding="utf-8") as f:
                        json.dump({"error": q.get("err")}, f)
                    w(f"queue failed: {q}")
                    continue

                deadline = time.time() + job.get("wait", 30)
                result = None
                next_pump = time.time() + 4   # 4秒没载体就自己泵
                pumped = 0
                while time.time() < deadline:
                    r = json.loads(script.exports_sync.result())
                    if r and r.get("err"):
                        result = {"error": r["err"]}
                        break
                    if r and r.get("sent"):
                        # 已发出：等待响应回填（最多10秒）
                        t1 = time.time() + 10
                        while time.time() < t1:
                            r = json.loads(script.exports_sync.result())
                            if r.get("respB64") or r.get("err"):
                                break
                            time.sleep(0.5)
                        resps = json.loads(script.exports_sync.responses())
                        r["resps"] = resps
                        try:
                            r["resplog"] = json.loads(script.exports_sync.resplog())
                        except Exception:
                            r["resplog"] = []
                        result = r
                        break
                    # 无载体 → 泵：好友按钮开关（仅QQ前台时）
                    if time.time() >= next_pump and pumped < 8:
                        try:
                            out = subprocess.run([ADB, "-s", SERIAL, "shell",
                                                  "dumpsys window | grep mCurrentFocus"],
                                                 capture_output=True, timeout=10)
                            focus = out.stdout.decode("utf-8", "replace")
                            if "com.tencent.mobileqq" in focus:
                                pumped += 1
                                if pumped % 2 == 1:
                                    # 奇数次：好友按钮开关（宠物主页时有效）
                                    subprocess.run([ADB, "-s", SERIAL, "shell", "input tap 1144 1360"],
                                                   capture_output=True, timeout=10)
                                    time.sleep(3)
                                    subprocess.run([ADB, "-s", SERIAL, "shell", "input keyevent KEYCODE_BACK"],
                                                   capture_output=True, timeout=10)
                                    w(f"carrier pump #{pumped} (friend-btn)")
                                else:
                                    # 偶数次：find_penguin 开页爆发（带保险丝）
                                    subprocess.run(["python", r".\find_penguin.py"],
                                                   capture_output=True, timeout=90)
                                    w(f"carrier pump #{pumped} (page-open)")
                            elif "launcher" in focus.lower() or "nexu" in focus.lower():
                                subprocess.run([ADB, "-s", SERIAL, "shell",
                                                "am start -n com.tencent.mobileqq/.activity.SplashActivity"],
                                               capture_output=True, timeout=10)
                                w("pump: relaunched QQ")
                                w(f"carrier pump #{pumped}")
                            else:
                                w(f"skip pump, focus: {focus.strip()[:60]}")
                        except Exception as ex:
                            w(f"pump fail: {ex}")
                        next_pump = time.time() + 6
                    time.sleep(0.4)
                if result is None:
                    r = json.loads(script.exports_sync.result())
                    result = r if r and r.get("sent") else {"error": "timeout", "detail": r}

                with open(RESP_FILE, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False)
                w(f"resp: sent={result.get('sent')} resps={len(result.get('resps') or [])}")
            time.sleep(0.5)
        except Exception as ex:
            w(f"loop error: {ex}")
            time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
