# QQ宠物协议逆向

2026年7月腾讯把QQ宠物塞回了手机QQ，一只会在消息页溜达的3D小企鹅。我嫌每天手动点学习太烦，又不想用模拟点击，给它的协议逆了。

**可以用纯协议命令让企鹅开始上课，全程不碰屏幕。**

## 原理

小鹅是个 Kuikly 模块，界面原生渲染，所有请求走 `QQKuiklyPlatformApi.call("sendPbRequest", ...)` 进 QQ 自己的加密通道。外部抓包抓不到明文（TLS 锁死 + 私有传输层），但 Frida 钩进去就是另一回事了。

思路说穿了很简单：既然鉴权在 App 内部完成，那就让 App 替我发请求——把自己构造的 protobuf 塞进真实请求的通道里"搭车"，响应再从回调里捞出来，QQ 本体无感知。

```
排队一条命令 → 重开宠物页制造流量 → 请求搭着真实通道发出去 → 回调里收响应 → 按信封ID认出哪条是我的 → 解码
```

## 已经摸清的东西

- 宠物所有服务器命令都是匿名 OIDB 编号：`0x9b60_1` 是开课，`0x9ab2_1` 是学习状态轮询，`0x9acb_0` 是状态查询……完整命令表、信封格式、protobuf 字段结构都在 [README_逆向档案.md](README_逆向档案.md)
- `pet_bot.py` 里有个零依赖的 protobuf wire-format 编解码器
- 一堆 Frida 在 QQ 上的坑：反调试看门狗隔几分钟杀一次进程、静态方法 hook 里 `ov.apply(null, args)` 会直接 TypeError、Kuikly 的类散落在多个 ClassLoader 得全枚举……踩坑过程都在档案里

## RUN

需要 root 过的安卓机、QQ 登录态、Florida 版 frida-server 16.7.19（版本要和 PC 端严格一致，17.x 注入会挂）。

```bash
pip install frida==16.7.19 frida-tools==13.6.1
# 设备: setenforce 0，启动 frida-server 监听 4779，adb forward tcp:4779 tcp:4779
python bot.py status   # 看宠物状态
python bot.py study    # 开一节课
```

## 现状和坑

- 开课已验证生效；收奖、续课、好友串门的命令也解出来了，还没接完
- QQ 反调试看门狗周期性杀进程，脚本里有自愈逻辑，被杀了会自动重挂
- 移动端单设备在线：bot 占的设备会和你日常手机互踢，所以我基本晚上挂
- QQ 一更新，信封 ID 和字段可能要重新对着抓包校准

## 声明

自用研究，练习Frida和protobuf逆向。自动化宠物大概率违反腾讯用户协议，风险自担。
