"""枚举 VAS/qqpet 相关类的方法表，找网络请求入口。"""
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
        Java.enumerateClassLoadersSync = null;
        var done = false;
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                if (done) return;
                try {
                    var f = Java.ClassFactory.get(loader);
                    var C = f.use(className);
                    var ms = C.class.getDeclaredMethods();
                    for (var i = 0; i < ms.length; i++) {
                        out.methods.push(ms[i].toString());
                    }
                    done = true;
                } catch (e) { }
            },
            onComplete: function () { }
        });
    });
    return out;
}

var CLASSES = [
    "com.tencent.mobileqq.vas.api.impl.VasKuiklyApiImpl",
    "com.tencent.mobileqq.qqpet.api.impl.QQPetAdapterApiImpl",
    "com.tencent.mobileqq.qqpet.api.impl.TabPetControllerApiImpl",
];
rpc.exports = {
    dump: function () {
        return CLASSES.map(dumpMethods);
    },
    enumvas: function () {
        var names = [];
        Java.perform(function () {
            Java.enumerateLoadedClasses({
                onMatch: function (n) {
                    if (/mobileqq\.vas\.(api|request|sso)/i.test(n)) names.push(n);
                },
                onComplete: function () { }
            });
        });
        return names;
    }
};
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(2)

results = script.exports_sync.dump()
for r in results:
    print("=" * 60)
    print(r["cls"], "->", len(r["methods"]), "methods")
    for m in r["methods"]:
        print("   ", m[:150])

vas = script.exports_sync.enumvas()
print("=" * 60)
print("VAS api/request/sso classes:", len(vas))
for c in vas[:60]:
    print("   ", c)
