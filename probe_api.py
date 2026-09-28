"""dump QQKuiklyPlatformApi 完整方法签名。"""
import time

import frida

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
pid = None
for p in dev.enumerate_processes():
    if p.name == "QQ":
        pid = p.pid
        break
print("QQ pid:", pid)
session = dev.attach(pid)

SCRIPT = r"""
function dumpMethods(className) {
    var out = { cls: className, methods: [] };
    Java.perform(function () {
        var done = false;
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                if (done) return;
                try {
                    var f = Java.ClassFactory.get(loader);
                    var C = f.use(className);
                    var ms = C.class.getDeclaredMethods();
                    for (var i = 0; i < ms.length; i++) out.methods.push(ms[i].toString());
                    done = true;
                } catch (e) { }
            },
            onComplete: function () { }
        });
    });
    return out;
}
rpc.exports = { dump: function () { return dumpMethods("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi"); } };
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(2)
r = script.exports_sync.dump()
print(r["cls"], "->", len(r["methods"]))
for m in r["methods"]:
    print("   ", m[:220])
