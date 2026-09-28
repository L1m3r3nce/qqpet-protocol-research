# QQ宠物（新版小鹅）协议逆向工程 — 项目档案

> **最终状态：🟢 FULL MISSION COMPLETE（2026-09-27 第三回合）**
> **协议开课成功**：`bot.py study` → 企鹅开始学习（书本+计时器验证），纯协议驱动零点击
> 全链路：构造命令→搭车发送→服务器处理→响应捕获→解码（性格四维/状态全出）
> 目标：自动化让企鹅「外出学习」+「与好友互动」（协议级，非模拟点击）
> 设备：Pixel 5 (root, Magisk 30.4) + PC (Windows, Python 3.12)

## 🚀 使用（bot.py 已可用）

```
环境：setenforce 0 + .sysmond3 + adb forward 4779（见第三节）
python bot.py status    # 查宠物状态（性格四维/心情/干劲）
python bot.py study     # 查状态 + 学习状态 + 协议开课 ✅已验证生效
python bot.py loop      # 常驻：每30分钟自动补课（含会话自愈）
```

每命令流程：queue → 重开宠物页(载体爆发) → PIGGY-SENT → respLog
按信封ID匹配响应 → 解码。`0x9b60_1`(开课) 已验证服务器接受并生效。

---

## ⭐ 完整可用配方（final_run.py 已验证）

```
1. force-stop QQ → 冷启动（清残留钩子）
2. attach + 加载 driver_lite.js（call钩+回调包装+搭车）
3. 排队协议命令 rpc.request(cmd, envelope_b64)   ← 必须先排队！
4. find_penguin.py 双击开宠物页（爆发流量=载体）
5. 搭车自动发射（PIGGY-SENT），响应经包装回调进入 respLog
6. resplog() 读出 → b64 → dec_pb() 解码 → 业务数据
```

**关键修复链（每一个都曾卡死全局）**：
| # | Bug | 修复 |
|---|---|---|
| 1 | 静态方法 hook `ov.apply(null,args)` → TypeError | `ov.apply(this,args)` |
| 2 | 搭车只换字节没换命令名 | c2[1]=我的cmd |
| 3 | retain 后 Integer.intValue() 不存在 | Java.cast 后再调 |
| 4 | byte[] b64 编码失败 | 逐字节反射读取兜底 |
| 5 | 时序：先开页后排队=浪费爆发 | 先排队后开页 |
| 6 | 单发脚本退出撕会话杀QQ | 只用常驻守护进程 |


## 一、架构结论（逆向成果）

QQ宠物 = **Kuikly 原生模块**（腾讯 Kotlin 跨端框架）：

```
宠物UI(Kotlin/Kuikly bundle: ai_pet_home/ai_pet_play/ai_pet_friend)
        │  模块调用
        ▼
QQKuiklyPlatformApi.call("sendPbRequest", [cmd, protobuf, null, 0, {}], callback)
        │  Java 层
        ▼
com.tencent.qphone.base.remote.ToServiceMsg (QQ MSF RPC 信封)
        │  QQ 私有加密传输（证书锁定，外部抓包不可解）
        ▼
服务器（OidbSvcTrpcTcp 匿名编号命令）
```

**关键事实：**
1. 宠物所有服务器请求走 `QQKuiklyPlatformApi.sendPbRequest(cmd, protobuf_bytes)`
2. cmd 是匿名 OIDB 编号（无 "pet" 字样），已确认映射见下表
3. 鉴权在 QQ 传输层完成，protobuf 里无 token → **纯外部重放不可行**，
   但**活体内调用可行**（App 自己处理签名）
4. 响应通过 Kotlin Function1 回调返回 `[code, msg, bytes]`

## 二、已确认的命令表

| cmd | 语义 | 内层 protobuf 字段 |
|---|---|---|
| `OidbSvcTrpcTcp.0x9acb_0` | 宠物状态查询 | {1: petId_b64, 2: "0103040508090b0f0a0e0d"} |
| `OidbSvcTrpcTcp.0x9b60_1` | **开始学习** | {1: courseId(6100=星耀夏令营), 2: petId_b64} |
| `OidbSvcTrpcTcp.0x9ab2_1` | **学习状态轮询** | {1: courseId, 2: petId_b64, 10:0, 11:3}；带字段3=好友petId时查好友状态 |
| `OidbSvcTrpcTcp.0x975e_1` | 课程详情/串门 | {1: courseId, 2: petId_b64, 6: 课程名, 7: 数字}；好友串门变体带好友petId+好友UID+昵称 |
| `OidbSvcTrpcTcp.0x975c_1` | 学院信息 | {1: 6000, 2: petId_b64} |
| `OidbSvcTrpcTcp.0x975f_1` | 会话查询 | {1: "6400_<uuid>", 2: petId_b64} |
| `OidbSvcTrpcTcp.0x9760_1` | 进入学院 | {1: 会话串, 2: 6000, 3: petId_b64, 4: 3} |
| `OidbSvcTrpcTcp.0x985d_0` | 好友列表分页 | JSON: {"sid":"...","offset":10} |
| `OidbSvcTrpcTcp.0x9875_1` | 心跳(3秒/次) | — |

**OIDB 信封**（所有请求外层）：
```
{1: 每命令固定ID(见pet_bot.py ENVELOPE_ID), 2: type(0/1), 3: 0,
 4: 内层protobuf, 6: "android 9.3.70", 11: "qq-trans\ncompose_version=1.0.0_debug"(type=0时)}
```

**身份参数**：petId = base64("1120602125-4-2-1785167541866")（QQ号-物种4-2-时间戳）

## 三、环境与工具链（已搭好）

| 组件 | 位置 | 说明 |
|---|---|---|
| Frida server | Pixel `/data/local/tmp/.sysmond3` (Florida 16.7.19 反检测版) | 启动: `su -c 'setsid /data/local/tmp/.sysmond3 -l 127.0.0.1:4779 ...'` |
| 端口转发 | `adb forward tcp:4779 tcp:4779` | 每次USB连接后执行 |
| SELinux | 需 Permissive | `su -c 'setenforce 0'`（重启后失效需重设）|
| PC frida | frida==16.7.19 + frida-tools==13.6.1 | 与 server 版本严格匹配 |
| frida 17.x | ✗ 在此设备注入失败 | 不要升级 |

**坑与对策：**
- QQ 反调试看门狗会杀进程（约钩住核心类后1-2分钟）→ Florida版+只钩业务类可长期存活
- 钩 `ToServiceMsg`（核心类）必被杀；钩 `QQKuiklyPlatformApi`/Kuikly 分发器（业务类）稳定
- QQ 的 Kuikly 类可能来自多个 ClassLoader，**必须对所有 loader 都装钩**
- frida 断开时卸载热路径钩子可能把 QQ 搞崩（重启自愈，登录态不丢）
- `pm compile` 全量 dexopt 会把手机卡死，别用

## 四、项目文件

| 文件 | 用途 |
|---|---|
| `hook_pet.js` | 最终捕获钩（call+代理回调，请求/响应 base64 落盘）★稳定 |
| `run_phaseA.py` | 捕获 runner（多进程+存活追踪，日志→phaseA_log.txt）★稳定 |
| `driver.js` | 协议驱动器 v2（sendpb RPC，复用真实回调）— 调用时序待打磨 |
| `pet_bot.py` | 机器人 CLI（status/study/academy；含 pb 编解码器+命令表）|
| `decode_pb.py` | protobuf wire-format 解码器（零依赖）|
| `pb_capture.json` | 已捕获的 200+ 请求/响应（base64，含学习/好友动作全程）|
| `timeline.py` / `stat_modules.py` / `pair_rsp.py` | 分析工具 |
| `replay_test.py` | 逐字节重放实验（对照用）|

## 五、使用流程（录制模式，已验证稳定）

```
1. Pixel: setenforce 0 + 启动 .sysmond3 + adb forward
2. PC:    python run_phaseA.py   （后台常驻）
3. 手机:  打开宠物页操作
4. 分析:  python timeline.py / pair_rsp.py
```

## 五B、主动调用链路（本轮战果）

**已验证成功**（`burst_test.py state` → `sent=true via=call`，QQ 存活）：

```
pet_bot.py 命令表/信封构造（含修正：petId无填充、bitmask原始字节、field11嵌套）
   ↓ cmd.json
driver_daemon.py（常驻，唯一会话，防卸载崩溃；QQ重启自动重挂+自动开宠物页）
   ↓ rpc.request()
driver.js v5：钩 QQKuiklyPlatformApi.call → 真实请求过钩后
   【搭车】同线程重放 call("sendPbRequest",[cmd,myBytes,null,0,{}],代理回调)
   ↓
QQ 真实通道发出（鉴权由App处理）→ 代理回调收响应
```

**载体（carrier）问题与解法**：宠物主页静默时无请求流。
- 开页瞬间有 17 连发爆发（最佳载体）→ `burst_test.py`：先排队→再开页
- 学习进行中每 5 秒轮询（天然载体）→ 学业进行时最稳
- `find_penguin.py`：像素定位企鹅+**双击**开页（注意：必须带页面验证保险丝，
  否则会在桌面/其他页面乱点蓝色图标——已出过事故并修复）

**已知不稳定因素**：
- QQ 反调试看门狗周期性杀进程（每 4-6 分钟），daemon 自动恢复
- daemon 重启/退出时 hook 卸载偶发把 QQ 带崩（重启自愈，登录态不丢）
- 响应回调参数结构尚未完全解析（invocations 签名日志已就位待验证）

## 五C、事故记录（2026-09-27 晚）

守护进程自动恢复在非QQ页面用蓝色像素找企鹅，误双击了搜索/相机图标。
**修复**：find_penguin 增加保险丝——uiautomator 确认存在 Q宠 节点才允许点击。

## 六、剩余工作（拿到全自动 bot 还差）

### 已验证 vs 未完成
| 项 | 状态 |
|---|---|
| 协议逆向（cmd/protobuf/信封） | ✅ 完成 |
| 搭车发送（y层/call层，QQ存活） | ✅ **已验证 sent=true** |
| 响应读取 | ⏳ 代理回调只收到空数组ack；y层"捕获+透传"代理代码已就位未及验证 |
| 业务循环（状态→开课→串门） | ⏳ 未开始（依赖响应读取） |

### 环境敌对性（重要）
QQ 反调试看门狗会周期性杀进程（4-6分钟，恶化时1-2分钟）；
frida 会话 attach/detach 本身就可能触发进程死亡。
**下一步战术**：单守护进程常驻（已实现），QQ重启→自动重挂→自动开宠物页（find_penguin
带保险丝）→ 开页爆发流量当载体（burst_test 的先排队后开页时序）。
响应读取验证：在稳定窗口内跑一次 `burst_test.py state`，观察 `invocations` 签名——
若出现 `Integer,String,[B` 组合即成功，pet_bot 解析即可闭环。

### 响应回调线索
- 真实流的响应格式：`[code(Integer), msg(String), bytes([B)]`（录制已证）
- 我方 call 层搭车的回调只收到 `Object;[]`（空数组同步ack）→ 响应路由不在该回调
- y 层（index 3=bytes, index 10=Function1回调）搭车 + makeProxy(捕获+透传) 是当前最优解

### 2026-09-27 深夜最终状态（第二回合）

**关键修复（第二回合）**：
1. **null-this 根因**：静态方法 hook 里 `ov.apply(null,args)` → frida 桥 TypeError
   （`$borrowClassHandle of null`），曾让所有 y() 调用在钩内抛异常。修复=`ov.apply(this,args)`
2. y 层搭车补上**命令名替换**（c2[1]=我的cmd，之前只换了字节）
3. `v()` 通道（richframework）确认存在于 sendPbRequest 流程
4. daemon 修复：subprocess 作用域、非阻塞恢复、双模式载体泵、QQ 前台检测+自动拉起

**差分实验新发现（lite 驱动，无 y/P/v 钩）**：
- `args[2]` 回调包装成功且**确实被调用**（real#N 多次触发）！
- 但解析报 `Wrapper is disposed`（需 Java.retain）与 `TypeError: not a function`
- **下一手**：driver_lite2.js 已写好（Java.retain + 直接解析），差一次稳定窗口运行
- 载体结论：好友按钮点击不一定触发请求（缓存）；**页面重开爆发**最可靠；
  拜访好友必发请求（待验证）；打工/学习期间 App 自动轮询是持续载体

**教训（环境纪律）**：
- QQ 反调试 + frida 会话 attach/detach 本身就会杀 QQ → **只允许一个常驻会话**
  （daemon），禁止任何一次性 attach 测试脚本
- 单发测试每次退出=撕会话=QQ 崩溃 → 今晚后期环境恶化主因

## 七、风险提示

- 协议自动化可能违反腾讯用户协议，存在账号风控/封禁风险，自担
- QQ 版本更新（9.3.70 → x）后 ENVELOPE_ID/字段可能变化，需重新录制校准
