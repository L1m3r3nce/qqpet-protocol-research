"""最小实验：验证 setTimeout 回调里 send/console.log 是否工作。"""
import time

import frida

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4778")
pid = None
for p in dev.enumerate_processes():
    if p.name == "QQ":
        pid = p.pid
        break
print("QQ pid:", pid)
session = dev.attach(pid)

SCRIPT = r"""
function test() {
    console.log("[T0] sync console.log works");

    // 实验1: 纯 JS 定时器
    setTimeout(function () {
        console.log("[T1] timer fired, sending...");
        send({ tag: "T1", ok: true });
    }, 1000);

    // 实验2: 定时器里调用 Java
    setTimeout(function () {
        try {
            var B = Java.use("android.util.Base64");
            console.log("[T2] Java.use outside perform ok");
            send({ tag: "T2", ok: true });
        } catch (e) {
            console.log("[T2] Java.use fail: " + e);
            send({ tag: "T2", ok: false, err: "" + e });
        }
    }, 1200);

    // 实验3: Java.perform 包裹
    setTimeout(function () {
        Java.perform(function () {
            try {
                var B = Java.use("android.util.Base64");
                send({ tag: "T3", ok: true });
            } catch (e) {
                send({ tag: "T3", ok: false, err: "" + e });
            }
        });
    }, 1400);
}
test();
"""

got = []
script = session.create_script(SCRIPT)
script.on("message", lambda m, d: (got.append(m), print("MSG:", m)))
script.set_log_handler(lambda lvl, msg: print(f"[{lvl}] {msg}"))
script.load()
time.sleep(4)
print("received:", len(got))
