"""dump KuiklyRenderNativeMethodCallModuleMethod 的字段结构。"""
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
function dumpFields(className) {
    var out = { cls: className, fields: [], methods: [] };
    Java.perform(function () {
        var done = false;
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                if (done) return;
                try {
                    var f = Java.ClassFactory.get(loader);
                    var C = f.use(className);
                    var fs = C.class.getDeclaredFields();
                    for (var i = 0; i < fs.length; i++) out.fields.push(fs[i].toString());
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
rpc.exports = {
    dump: function () {
        return [
            "com.tencent.kuikly.core.render.android.context.KuiklyRenderNativeMethodCallModuleMethod",
            "com.tencent.kuikly.core.render.android.context.KuiklyRenderNativeMethod",
        ].map(dumpFields);
    }
};
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(2)
for r in script.exports_sync.dump():
    print("=" * 60)
    print(r["cls"])
    print("fields:")
    for f_ in r["fields"]:
        print("   ", f_[:150])
    print("methods:")
    for m in r["methods"]:
        print("   ", m[:150])
