"""探明 sendPbRequest 的内部路径：call/y/v 哪个在心跳时触发。"""
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
var seen = {};
function logCall(tag, extra) {
    var k = tag + "|" + (extra || "");
    if (!seen[k]) { seen[k] = 1; console.log("[PATH] " + k); }
}

Java.perform(function () {
    Java.enumerateClassLoaders({
        onMatch: function (loader) {
            try {
                var f = Java.ClassFactory.get(loader);
                var Api = f.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
                try {
                    Api.call.overloads.forEach(function (ov) {
                        ov.implementation = function () {
                            var a0 = "" + arguments[0];
                            logCall("call", a0);
                            return ov.apply(this, arguments);
                        };
                    });
                    console.log("[*] call hooked");
                } catch (e) { console.log("call fail " + e); }
                try {
                    Api.y.overloads.forEach(function (ov) {
                        ov.implementation = function () {
                            logCall("y", "len=" + arguments.length);
                            return ov.apply(null, arguments);
                        };
                    });
                    console.log("[*] y hooked");
                } catch (e) { console.log("y fail " + e); }
                try {
                    Api.v.overloads.forEach(function (ov) {
                        ov.implementation = function () {
                            logCall("v", "VSBaseRequest");
                            return ov.apply(null, arguments);
                        };
                    });
                    console.log("[*] v hooked");
                } catch (e) { console.log("v fail " + e); }
            } catch (e) { }
        },
        onComplete: function () { }
    });
});
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
print("watching for 12s (pet page should heartbeat)...")
time.sleep(12)
print("done")
