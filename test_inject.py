"""对照实验 v2：spawn 系统设置 App 验证注入。"""
import time

import frida

dev = frida.get_device_manager().add_remote_device("127.0.0.1:4778")
out = []
pid = dev.spawn(["com.android.chrome"])
print("spawned chrome pid:", pid)
s = dev.attach(pid)
sc = s.create_script(
    'Java.perform(function(){ send("inject-ok pkg=" + '
    'Java.use("android.app.ActivityThread").currentApplication().getPackageName()); });'
)
sc.on("message", lambda m, d: out.append(m))
sc.load()
dev.resume(pid)
time.sleep(3)
print("RESULT:", out)
