"""找 QQKuiklyPlatformApi 模块的 Java 实现类和响应回调路径。"""
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
                    for (var i = 0; i < ms.length; i++) out.methods.push(ms[i].toString().substring(className.length + 40));
                    done = true;
                } catch (e) { }
            },
            onComplete: function () { }
        });
    });
    return out;
}

rpc.exports = {
    search: function () {
        var names = [];
        Java.perform(function () {
            Java.enumerateLoadedClasses({
                onMatch: function (n) {
                    if (/KuiklyPlatformApi|QQKuikly.*Module|kuikly.*callback/i.test(n)) names.push(n);
                },
                onComplete: function () { }
            });
        });
        return names;
    },
    dump: function (cls) { return dumpMethods(cls); }
};
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(2)

names = script.exports_sync.search()
print("matching classes:", len(names))
for n in names[:40]:
    print("  ", n)
