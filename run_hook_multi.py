"""多进程 hook v2：按 PID 追踪进程存活，死了自动重挂（QQ 反调试会自杀重启）。"""
import datetime
import json
import time

import frida

LOG = r".\hook_log.jsonl"
TARGETS = ("QQ", "com.tencent.mobileqq:MSF", "com.tencent.mobileqq:wxa_container0")

attached = {}  # name -> (pid, session, script)


def make_on_message(proc_label):
    def on_message(message, data):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if message["type"] == "send":
            payload = message["payload"]
            line = {"ts": ts, "proc": proc_label, **payload}
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            print(f"[{ts}][{proc_label}] {payload.get('tag')} {payload.get('cmd')} {str(payload.get('preview'))[:110]}")
        elif message["type"] == "error":
            print(f"[{ts}][{proc_label}] SCRIPT-ERROR {message.get('description')}")
    return on_message


def make_on_console(proc_label):
    def handler(level, message):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}][{proc_label}][{level}] {message}")
    return handler


def main():
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
    with open(r".\hook_pet.js", encoding="utf-8") as f:
        src = f.read()

    def try_attach(name, pid):
        try:
            session = dev.attach(pid)
            script = session.create_script(src)
            script.on("message", make_on_message(name))
            script.set_log_handler(make_on_console(name))
            script.load()
            attached[name] = (pid, session, script)
            print(f"[+] hooked {name} (pid {pid})")
        except Exception as e:
            print(f"[!] attach {name}#{pid} fail: {str(e)[:100]}")

    print("runner v2 (florida@4779) started")
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
            print(f"[!] loop error: {str(e)[:100]}")
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
