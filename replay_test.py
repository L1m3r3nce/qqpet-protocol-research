"""replay_test.py — 逐字节重放捕获的真实心跳请求，验证调用机制。"""
import base64
import json
import time

import frida

# 从录制数据取一条真实的 0x9875_1 心跳
CAP = r".\pb_capture.json"
with open(CAP, encoding="utf-8") as f:
    entries = json.load(f)
hb = None
for e in entries:
    if e["kind"] == "REQ" and (e["cmd"] or "").endswith("0x9875_1") and e["b64"]:
        hb = e["b64"][0]
        break
print("heartbeat payload:", hb[:60], "...")

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4779")
pid = None
for p in dev.enumerate_processes():
    if p.name == "QQ":
        pid = p.pid
        break
print("QQ pid:", pid)
session = dev.attach(pid)

SCRIPT = r"""
var lastApi = null, lastOv = null, lastCb = null;

function bytesToB64(a) { try { return Java.use("android.util.Base64").encodeToString(a, 2); } catch(e){ return null; } }

Java.perform(function () {
    var seenLoaders = {};
    Java.enumerateClassLoaders({
        onMatch: function (loader) {
            var key = "" + loader;
            if (seenLoaders[key]) return;
            seenLoaders[key] = 1;
            try {
                var f = Java.ClassFactory.get(loader);
                var Api = f.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
                Api.call.overloads.forEach(function (ov) {
                    ov.implementation = function () {
                        var args = [];
                        for (var i = 0; i < arguments.length; i++) args.push(arguments[i]);
                        if ("" + args[0] === "sendPbRequest" && args.length >= 3) {
                            lastApi = this; lastOv = ov;
                            if (args[args.length-1]) lastCb = args[args.length-1];
                            console.log("[hook] captured api, args=" + args.length);
                        }
                        return ov.apply(this, args);
                    };
                });
                console.log("[*] hooks in @" + key.substring(0, 40));
            } catch (e) { }
        },
        onComplete: function () { }
    });
});

rpc.exports = {
    status: function () { return JSON.stringify({api: lastApi !== null, cb: lastCb !== null}); },
    replay: function (cmd, b64payload) {
        return new Promise(function (resolve) {
            var done = false;
            var fin = function (o) { if (!done) { done = true; resolve(JSON.stringify(o)); } };
            setTimeout(function () { fin({ sent: false, err: "timeout" }); }, 5000);
            Java.perform(function () {
                try {
                    if (!lastApi) { fin({ sent: false, err: "no api" }); return; }
                    var bytes = Java.use("android.util.Base64").decode(b64payload, 0);
                    var JStr = Java.use("java.lang.String");
                    var JInt = Java.use("java.lang.Integer");
                    var HM = Java.use("java.util.HashMap");
                    var AC = Java.use("java.util.Arrays");
                    var arr = Java.array("java.lang.Object", [JStr.$new(cmd), bytes, null, JInt.valueOf(0), HM.$new()]);
                    var params = AC.asList(arr);
                    var api = lastApi, ov = lastOv, cb = lastCb;
                    var ms = JStr.$new("sendPbRequest");
                    // 直接在当前线程调用（与真实调用同线程模型由 Kotlin 自身处理）
                    try {
                        ov.apply(api, [ms, params, cb]);
                        fin({ sent: true });
                    } catch (e) {
                        fin({ sent: false, err: "call: " + e });
                    }
                } catch (e) {
                    fin({ sent: false, err: "pre: " + e });
                }
            });
        });
    }
};
"""

script = session.create_script(SCRIPT)
script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}"))
script.load()

# 等捕获
for i in range(20):
    st = json.loads(script.exports_sync.status())
    if st.get("api"):
        break
    time.sleep(2)
print("status:", st)
if not st.get("api"):
    raise SystemExit("no api — open pet page")

r = json.loads(script.exports_sync.replay("OidbSvcTrpcTcp.0x9875_1", hb))
print("replay result:", r)
time.sleep(2)
# QQ 还活着吗
try:
    alive = any(p.name == "QQ" for p in dev.enumerate_processes())
    print("QQ alive:", alive)
except Exception as ex:
    print("check fail:", ex)
