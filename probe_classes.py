"""枚举 QQ 进程内已加载的类，验证 ToServiceMsg/qphonebase/kuikly 是否存在。"""
import sys
import time

import frida

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4778")

# 附加到正在运行的 QQ（不杀进程）
pid = None
for p in dev.enumerate_processes():
    if p.name == "QQ":
        pid = p.pid
        break
print("attaching to QQ pid", pid)
session = dev.attach(pid)

SCRIPT = r"""
function probe() {
    var result = { qphone: [], tosvc: [], kuikly: [], msf: [], nt: [] };
    Java.perform(function () {
        Java.enumerateLoadedClassesSync = Java.enumerateLoadedClassesSync || null;
        var classes = [];
        try {
            Java.enumerateLoadedClasses({
                onMatch: function (name) {
                    if (/qphonebase/i.test(name)) result.qphone.push(name);
                    else if (/ToServiceMsg|FromServiceMsg/i.test(name)) result.tosvc.push(name);
                    else if (/mobileqq\.qqpet/i.test(name)) result.kuikly.push(name);
                },
                onComplete: function () { }
            });
        } catch (e) {
            result.error = "" + e;
        }
    });
    return result;
}
rpc.exports = { probe: probe };
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(1)
r = script.exports_sync.probe() if hasattr(script, "exports_sync") else script.exports.probe()
print("qphonebase classes:", len(r.get("qphone", [])))
for c in r.get("qphone", [])[:20]:
    print("  ", c)
print("To/FromServiceMsg:", len(r.get("tosvc", [])))
for c in r.get("tosvc", [])[:10]:
    print("  ", c)
print("kuikly classes:", len(r.get("kuikly", [])))
for c in r.get("kuikly", [])[:30]:
    print("  ", c)
print("msf classes:", len(r.get("msf", [])))
for c in r.get("msf", [])[:15]:
    print("  ", c)
if "error" in r:
    print("ERROR:", r["error"])
