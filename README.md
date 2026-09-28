# QQ宠物协议逆向研究 (qqpet-protocol-research)

对 2026-07 回归手机 QQ 的新版宠物（小鹅/Kuikly 模块）的协议层逆向研究。
**已验证：纯协议命令驱动企鹅开始学习（无界面模拟点击）。**

> ⚠️ 免责声明：本研究仅供学习交流（协议分析/Frida/protobuf 逆向技术）。
> 自动化操作可能违反腾讯用户协议，存在账号风控风险，后果自负。
> 数据已脱敏，请勿用于他人账号。

## 核心发现

**架构**：宠物 = Kuikly 原生模块，所有请求经
`QQKuiklyPlatformApi.call("sendPbRequest", [cmd, protobuf, ...], callback)`
走 QQ 私有加密通道（匿名 OIDB 编号命令，TLS 证书锁定，外部抓包不可解）。

**已解明命令表**（详见 `README_逆向档案.md`）：

| cmd | 语义 |
|---|---|
| `OidbSvcTrpcTcp.0x9b60_1` | 开始学习 {courseId, petId} |
| `OidbSvcTrpcTcp.0x9ab2_1` | 学习状态轮询 |
| `OidbSvcTrpcTcp.0x9acb_0` | 宠物状态查询 |
| `OidbSvcTrpcTcp.0x975e_1` | 课程详情/好友串门 |
| `OidbSvcTrpcTcp.0x985d_0` | 好友列表分页 |
| ... | 信封格式/protobuf 字段见档案 |

**搭车架构**（鉴权不可外部重放 → 活体内调用）：
```
queue 命令 → 重开宠物页(流量爆发载体) → 同线程搭车 sendPbRequest
→ 包装回调捕获响应 → 信封ID匹配 → protobuf 解码
```

## 环境

- root 安卓设备 + Florida frida-server 16.7.19（github.com/Ylarod/Florida）
- PC: Python 3.12 + frida==16.7.19 + frida-tools==13.6.1（版本严格匹配）
- QQ 9.3.70 (Android)

## 快速上手

```bash
# 设备: setenforce 0 + 启动 frida-server(4779) + adb forward tcp:4779
python bot.py status    # 查宠物状态
python bot.py study     # 协议开课（已验证生效）
```

## 已知限制

- QQ 反调试看门狗周期杀进程（自愈守护已实现）
- 移动端单登录槽位：bot 设备与你日常手机互踢（夜校模式可绕开大半）
- QQ 版本更新后 ENVELOPE_ID/字段可能需重新录制校准

## 致谢

mitmproxy / Reqable / Frida + Florida / qq-pet-copilot（同类 UI 自动化方案）

## License

MIT
