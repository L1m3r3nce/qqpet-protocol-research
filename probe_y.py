"""dump QQKuiklyPlatformApi.y 的完整签名。"""
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
rpc.exports = {
    dump: function () {
        var out = [];
        Java.perform(function () {
            var seen = {};
            Java.enumerateClassLoaders({
                onMatch: function (loader) {
                    try {
                        var f = Java.ClassFactory.get(loader);
                        var C = f.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
                        var ms = C.class.getDeclaredMethods();
                        for (var i = 0; i < ms.length; i++) {
                            var s = "" + ms[i];
                            if (s.indexOf(".y(") > 0 || s.indexOf(".v(") > 0 || s.indexOf("sendWebSSO") >= 0) {
                                if (!seen[s]) { seen[s] = 1; out.push(s); }
                            }
                        }
                    } catch (e) { }
                },
                onComplete: function () { }
            });
        });
        return out;
    }
};
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(2)
for m in script.exports_sync.dump():
    print(m)
