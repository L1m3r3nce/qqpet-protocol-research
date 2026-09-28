"""轻足迹 runner：把 console 输出也存盘，attach 按进程 PID 存活追踪。"""
import datetime
import json
import time

import frida

LOG = r"G:\plugin_qq\phaseA_log.txt"
TARGETS = ("QQ", "com.tencent.mobileqq:MSF")

attached = {}
logfile = open(LOG, "a", encoding="utf-8")


def w(line):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    out = f"[{ts}] {line}"
    print(out)
    logfile.write(out + "\n")
    logfile.flush()


def make_on_message(proc_label):
    def on_message(message, data):
        if message["type"] == "send":
            w(f"[{proc_label}] SEND {json.dumps(message['payload'], ensure_ascii=False)[:200]}")
        elif message["type"] == "error":
            w(f"[{proc_label}] SCRIPT-ERROR {message.get('description')}")
    return on_message


def make_on_console(proc_label):
    def handler(level, message):
        w(f"[{proc_label}][{level}] {message}")
    return handler


def main():
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
    with open(r"G:\plugin_qq\hook_pet.js", encoding="utf-8") as f:
        src = f.read()

    def try_attach(name, pid):
        try:
            session = dev.attach(pid)
            script = session.create_script(src)
            script.on("message", make_on_message(name))
            script.set_log_handler(make_on_console(name))
            script.load()
            attached[name] = (pid, session, script)
            w(f"[+] hooked {name} (pid {pid})")
        except Exception as e:
            w(f"[!] attach {name}#{pid} fail: {str(e)[:100]}")

    w("phase-A runner started")
    while True:
        try:
            procs = {p.name: p.pid for p in dev.enumerate_processes()}
            for name in TARGETS:
                pid = procs.get(name)
                if pid is None:
                    continue
                cur = attached.get(name)
                if cur is None or cur[0] != pid:
                    try_attach(name, pid)
        except Exception as e:
            w(f"[!] loop error: {str(e)[:100]}")
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
