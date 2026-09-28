"""bot.py — QQ宠物协议机器人（基于已验证的搭车管线）

一次会话内执行多命令（每命令一次载体=重开宠物页）：
  python bot.py status     # 查宠物状态
  python bot.py study      # 查状态 + 开课 + 验证
  python bot.py loop       # 常驻：每30分钟一轮（状态→补课）

流程（每命令）：queue → BACK回主页 → 双击企鹅重开页(爆发载体) → 搭车发射
              → respLog 里按信封ID匹配我的响应 → 解码
"""
import base64
import json
import subprocess
import sys
import time

sys.path.insert(0, r".")
from pet_bot import enc_str, enc_int, dec_pb, fmt, envelope  # noqa: E402

ADB = r"adb"
SERIAL = "YOUR_DEVICE_SERIAL"
PET_ID = "MTAwMDAwMDAwMDA="
COURSE_ID = 6100

import frida  # noqa: E402

ENVELOPE_ID = {
    "OidbSvcTrpcTcp.0x9acb_0": 39627,
    "OidbSvcTrpcTcp.0x9b60_1": 39776,
    "OidbSvcTrpcTcp.0x9ab2_1": 39602,
    "OidbSvcTrpcTcp.0x975e_1": 38750,
    "OidbSvcTrpcTcp.0x975c_1": 38748,
}


def sh(cmd, t=20):
    return subprocess.run([ADB, "-s", SERIAL, "shell", cmd], capture_output=True, timeout=t)


def run_py(script, t=120):
    r = subprocess.run(["python", script], capture_output=True, timeout=t)
    return r.stdout.decode("utf-8", "replace").strip()


class Bot:
    def __init__(self):
        self.script = None
        self.log_cursor = 0

    def bootstrap(self):
        """冷启动 QQ + attach + 装钩"""
        sh("am force-stop com.tencent.mobileqq")
        time.sleep(4)
        sh("am start -n com.tencent.mobileqq/.activity.SplashActivity")
        print("QQ 启动中...")
        time.sleep(25)
        dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
        pid = next((p.pid for p in dev.enumerate_processes() if p.name == "QQ"), None)
        if pid is None:
            raise RuntimeError("QQ 未运行")
        session = dev.attach(pid)
        with open(r".\driver_lite.js", encoding="utf-8") as f:
            self.script = session.create_script(f.read())
        self.script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}") if "PIGGY" in msg or "CHK pending=true" in msg else None)
        self.script.on("message", lambda m, d: None)
        self.script.load()
        time.sleep(2)
        self.log_cursor = 0
        print(f"会话就绪 (pid={pid})")

    def carrier(self, retries=3):
        """载体：重开宠物页（爆发流量）。
        策略：若当前在宠物页→BACK回主页；然后等待 Q宠 悬浮件出现并双击。
        注意：绝不在主页按 BACK（会收起企鹅/退出）。"""
        # 判断当前页
        dump = sh("uiautomator dump /sdcard/ui.xml 2>&1").stdout.decode("utf-8", "replace")
        xml = sh("cat /sdcard/ui.xml").stdout.decode("utf-8", "replace")
        on_main = 'content-desc="Q宠' in xml
        if not on_main:
            # 可能在宠物页或其他页：BACK 一次回主页
            sh("input keyevent KEYCODE_BACK")
            time.sleep(2)
        for i in range(retries):
            out = run_py(r".\find_penguin.py")
            tail = out.splitlines()[-1] if out else "(no output)"
            print(f"  carrier[{i+1}]: {tail}")
            if "PET PAGE OPENED" in out:
                time.sleep(1)
                return True
            if "NOT on QQ main page" in out:
                # 企鹅还没加载：等它出现
                print("  等待企鹅悬浮件加载...")
                time.sleep(8)
            else:
                time.sleep(2)
        return False

    def exec_cmd(self, cmd, inner, etype, wait=15):
        """执行一条协议命令并返回解码响应"""
        payload = envelope(inner, cmd, etype)
        q = json.loads(self.script.exports_sync.request(cmd, base64.b64encode(payload).decode()))
        if not q.get("queued"):
            self.script.exports_sync.reset()
            q = json.loads(self.script.exports_sync.request(cmd, base64.b64encode(payload).decode()))
            if not q.get("queued"):
                raise RuntimeError(f"queue fail: {q}")
        # 载体（以 result.sent 为准，不信 find_penguin 自检）
        for i in range(3):
            self._try_carrier_once(i)
            r = json.loads(self.script.exports_sync.result())
            if r and (r.get("sent") or r.get("err")):
                break
        deadline = time.time() + wait
        while time.time() < deadline:
            r = json.loads(self.script.exports_sync.result())
            if r and (r.get("sent") or r.get("err")):
                break
            time.sleep(0.5)
        time.sleep(3)
        r = json.loads(self.script.exports_sync.result())
        if not r.get("sent"):
            raise RuntimeError(f"not sent: {r.get('err')}")
        # 从 respLog 找我的响应（信封ID匹配，取最新）
        log = json.loads(self.script.exports_sync.resplog())
        want = ENVELOPE_ID.get(cmd)
        mine = None
        for e in log:
            if e.get("b64") and e.get("code") == 0:
                try:
                    d = dec_pb(base64.b64decode(e["b64"]))
                    f1 = d.get(1, [None])[0]
                    if f1 == want:
                        mine = d
                except Exception:
                    pass
        self.script.exports_sync.reset()
        return mine

    def _try_carrier_once(self, i):
        """单次载体尝试：判断页面→导航→双击"""
        dump = sh("uiautomator dump /sdcard/ui.xml 2>&1").stdout.decode("utf-8", "replace")
        xml = sh("cat /sdcard/ui.xml").stdout.decode("utf-8", "replace")
        on_main = 'content-desc="Q宠' in xml
        if not on_main:
            sh("input keyevent KEYCODE_BACK")
            time.sleep(2)
        out = run_py(r".\find_penguin.py")
        tail = out.splitlines()[-1] if out else "(no output)"
        print(f"  carrier[{i+1}]: {tail}")
        if "NOT on QQ main page" in out:
            time.sleep(6)

    # ---- 业务命令 ----
    def q_state(self):
        inner = enc_str(1, PET_ID) + enc_str(2, bytes.fromhex("0103040508090b0f0a0e0d"))
        return self.exec_cmd("OidbSvcTrpcTcp.0x9acb_0", inner, 0)

    def q_start_study(self):
        inner = enc_int(1, COURSE_ID) + enc_str(2, PET_ID)
        return self.exec_cmd("OidbSvcTrpcTcp.0x9b60_1", inner, 1)

    def q_study_status(self):
        inner = enc_int(1, COURSE_ID) + enc_str(2, PET_ID) + enc_int(10, 0) + enc_int(11, 3)
        return self.exec_cmd("OidbSvcTrpcTcp.0x9ab2_1", inner, 1)


def show_state(d):
    if not d:
        print("(无状态数据)")
        return
    print(fmt(d)[:1800])


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    bot = Bot()
    bot.bootstrap()

    if mode == "status":
        d = bot.q_state()
        print("=== 宠物状态 ===")
        show_state(d)
    elif mode == "study":
        d = bot.q_state()
        print("=== 当前状态 ===")
        show_state(d)
        d2 = bot.q_study_status()
        print("=== 学习状态 ===")
        show_state(d2)
        d3 = bot.q_start_study()
        print("=== 开课结果 ===")
        show_state(d3)
    elif mode == "night":
        # 夜校模式：通宵循环，被踢（槽位被vivo收回）则优雅退出
        cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 999
        interval_min = 20
        done = 0
        while done < cycles:
            try:
                print(time.strftime("\n[%H:%M] === 夜校周期 ==="))
                # 1. 学习状态 → 完成则自动续课；空闲则开课
                d = bot.q_study_status()
                print("学习状态:", "查询中..." if d else "(无响应)")
                d3 = bot.q_start_study()
                print("开课/续课:", "OK" if d3 else "(无响应——可能在学中)")
                if d3:
                    show_state(d3)
                done += 1
                if done < cycles:
                    print(f"休眠 {interval_min} 分钟...")
                    time.sleep(interval_min * 60)
            except RuntimeError as ex:
                msg = str(ex)
                if "not sent" in msg or "carrier fail" in msg:
                    # 可能被踢下线：检查QQ登录态
                    dump = sh("dumpsys window | grep mCurrentFocus").stdout.decode("utf-8", "replace")
                    print("发送失败，当前焦点:", dump.strip()[:60])
                    print("→ 槽位可能已被你收回（登了vivo）。夜校结束，晚安。")
                    break
                else:
                    print("周期异常:", ex, "→ 重建会话")
                    try:
                        bot.bootstrap()
                    except Exception as ex2:
                        print("重建失败:", ex2, "→ 退出")
                        break
            except Exception as ex:
                print("周期异常:", ex, "→ 重建会话")
                try:
                    bot.bootstrap()
                except Exception as ex2:
                    print("重建失败:", ex2, "→ 退出")
                    break
        print(f"夜校结束：完成 {done} 个周期")
    elif mode == "loop":
        while True:
            try:
                print(time.strftime("\n[%H:%M] === 周期开始 ==="))
                d = bot.q_state()
                show_state(d)
                d3 = bot.q_start_study()
                print("开课:", "OK" if d3 else "(无响应——可能在学中)")
                show_state(d3)
            except Exception as ex:
                print("周期异常:", ex, "→ 重建会话")
                try:
                    bot.bootstrap()
                except Exception as ex2:
                    print("重建失败:", ex2)
                    time.sleep(30)
            time.sleep(30 * 60)


if __name__ == "__main__":
    main()
