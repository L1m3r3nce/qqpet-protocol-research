"""pet_bot.py — QQ 宠物协议机器人（Frida RPC 驱动活体 QQ 调用宠物接口）

用法:
  python pet_bot.py status          # 查询宠物状态
  python pet_bot.py study           # 自动开始一节最优课
  python pet_bot.py loop            # 常驻循环: 学习到期->续课, 定时好友互动
"""

import base64
import json
import struct
import sys
import time

import frida

# ---------- 配置 ----------
ADB_SERIAL_NOTE = "Frida server: Pixel 上 /data/local/tmp/.sysmond3 -l 127.0.0.1:4779"
FRIDA_ADDR = "127.0.0.1:4779"
PET_ID_B64 = "MTEyMDYwMjEyNS00LTItMTc4NTE2NzU0MTg2Ng"  # 38字符，无=填充
COURSE_ID = 6100          # 星耀夏令营（从抓包确认的当前可选课）
FRIENDS = []              # 好友宠物ID(b64)，留空则自动从列表拉

VERSION_STR = "android 9.3.70"
TRANS_META = "qq-trans\ncompose_version=1.0.0_debug"

# 命令表（从逆向确认）
CMD = {
    "pet_state": "OidbSvcTrpcTcp.0x9acb_0",      # 宠物状态 {petId, bitmask}
    "start_study": "OidbSvcTrpcTcp.0x9b60_1",    # 开始学习 {courseId, petId}
    "study_status": "OidbSvcTrpcTcp.0x9ab2_1",   # 学习状态 {courseId, petId, 10:0, 11:3}
    "course_query": "OidbSvcTrpcTcp.0x975e_1",   # 课程详情/串门
    "academy": "OidbSvcTrpcTcp.0x975c_1",        # 学院信息 {courseId6000, petId}
    "friend_list": "OidbSvcTrpcTcp.0x985d_0",    # 好友列表 {sid, offset}
}
# 每个命令的信封 field1（实测为每命令固定值）
ENVELOPE_ID = {
    CMD["pet_state"]: 39627,
    CMD["start_study"]: 39776,
    CMD["study_status"]: 39602,
    CMD["course_query"]: 38750,
    CMD["academy"]: 38748,
    CMD["friend_list"]: 39005,
}


# ---------- protobuf 编码 ----------
def enc_varint(v):
    out = b""
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out += bytes([b | 0x80])
        else:
            out += bytes([b])
            return out


def enc_tag(field, wt):
    return enc_varint((field << 3) | wt)


def enc_int(field, v):
    return enc_tag(field, 0) + enc_varint(v)


def enc_str(field, s):
    if isinstance(s, str):
        raw = s.encode()
    else:
        raw = s
    return enc_tag(field, 2) + enc_varint(len(raw)) + raw


def envelope(inner: bytes, cmd: str, etype=1) -> bytes:
    """OIDB 信封: {1:id, 2:type, 3:0, 4:inner, 6:version, 11:{1:qq-trans,2:compose_version}}"""
    out = enc_int(1, ENVELOPE_ID[cmd])
    out += enc_int(2, etype)
    out += enc_int(3, 0)
    out += enc_str(4, inner)
    out += enc_str(6, VERSION_STR)
    if etype == 0:
        meta = enc_str(1, "qq-trans") + enc_str(2, "compose_version=1.0.0_debug")
        out += enc_str(11, meta)
    return out


# ---------- protobuf 解码（极简） ----------
def dec_varint(data, i):
    r = 0
    s = 0
    while True:
        b = data[i]
        i += 1
        r |= (b & 0x7F) << s
        if not (b & 0x80):
            return r, i
        s += 7


def dec_pb(data, depth=0):
    out = {}
    i, n = 0, len(data)
    while i < n:
        try:
            tag, i = dec_varint(data, i)
        except IndexError:
            break
        f, wt = tag >> 3, tag & 7
        if f == 0 or f > 200:
            break
        if wt == 0:
            v, i = dec_varint(data, i)
        elif wt == 2:
            ln, i = dec_varint(data, i)
            v = data[i:i + ln]
            i += ln
            if depth < 6 and v:
                try:
                    s = v.decode("utf-8")
                    if sum(1 for c in s if c.isprintable() or c in "\n\t") >= len(s) * 0.9:
                        v = s
                    else:
                        raise ValueError
                except Exception:
                    try:
                        v = dec_pb(v, depth + 1)
                    except Exception:
                        pass
        elif wt == 5:
            v = struct.unpack("<f", data[i:i + 4])[0]
            i += 4
        elif wt == 1:
            v = struct.unpack("<d", data[i:i + 8])[0]
            i += 8
        else:
            break
        out.setdefault(f, []).append(v)
    return out


# ---------- 驱动 ----------
class PetDriver:
    def __init__(self):
        self.dev = frida.get_device_manager().add_remote_device(FRIDA_ADDR)
        pid = None
        for p in self.dev.enumerate_processes():
            if p.name == "QQ":
                pid = p.pid
                break
        if pid is None:
            raise RuntimeError("QQ 未运行（Pixel 上打开 QQ 后重试）")
        self.session = self.dev.attach(pid)
        with open(r"G:\plugin_qq\driver.js", encoding="utf-8") as f:
            src = f.read()
        self.script = self.session.create_script(src)
        self.script.set_log_handler(lambda lvl, msg: print(f"[js][{lvl}] {msg}"))
        self.script.load()
        # 等一次真实心跳过钩（宠物页开着时每3秒一次）
        for i in range(25):
            st = json.loads(self.script.exports_sync.status())
            if st.get("api") and st.get("carrier"):
                print(f"driver ready: {st}")
                break
            if i % 5 == 4:
                print(f"  ...等待宠物页心跳过钩 ({(i+1)*2}s)，请确认宠物页面处于打开状态")
            time.sleep(2)
        else:
            raise RuntimeError("未捕获到 sendPbRequest 通道（请打开宠物页面）")

    def sendpb(self, cmd, inner: bytes, etype=1, wait=25.0):
        """搭车发送：排队→等下一次心跳捎带→轮询结果"""
        payload = envelope(inner, cmd, etype)
        b64 = base64.b64encode(payload).decode()
        self.script.exports_sync.reset()
        q = json.loads(self.script.exports_sync.request(cmd, b64))
        if not q.get("queued"):
            raise RuntimeError(f"queue failed: {q.get('err')}")
        deadline = time.time() + wait
        while time.time() < deadline:
            r = json.loads(self.script.exports_sync.result())
            if r and r.get("err"):
                raise RuntimeError(f"send error: {r['err']}")
            if r and r.get("respB64"):
                r["decoded"] = dec_pb(base64.b64decode(r["respB64"]))
                return r
            time.sleep(0.4)
        # 超时：也许发出去了但响应没回（noRead 模式）
        r = json.loads(self.script.exports_sync.result())
        if r and r.get("sent"):
            return r
        raise RuntimeError(f"timeout waiting carrier/response (sent={r.get('sent') if r else None})")


# ---------- 业务 ----------
def q_pet_state(d: PetDriver):
    bitmask = bytes.fromhex("0103040508090b0f0a0e0d")  # 原始字节，不是ASCII
    inner = enc_str(1, PET_ID_B64) + enc_str(2, bitmask)
    return d.sendpb(CMD["pet_state"], inner, etype=0)


def q_start_study(d: PetDriver, course_id=COURSE_ID):
    inner = enc_int(1, course_id) + enc_str(2, PET_ID_B64)
    return d.sendpb(CMD["start_study"], inner)


def q_study_status(d: PetDriver, course_id=COURSE_ID):
    inner = (enc_int(1, course_id) + enc_str(2, PET_ID_B64)
             + enc_int(10, 0) + enc_int(11, 3))
    return d.sendpb(CMD["study_status"], inner)


def q_academy(d: PetDriver):
    inner = enc_int(1, 6000) + enc_str(2, PET_ID_B64)
    return d.sendpb(CMD["academy"], inner)


def visit_friend(d: PetDriver, friend_pet_b64, friend_uid, name=""):
    inner = (enc_int(1, COURSE_ID) + enc_str(2, PET_ID_B64)
             + enc_str(3, friend_pet_b64))
    return d.sendpb(CMD["study_status"], inner)


def fmt(obj, indent=0):
    pad = " " * indent
    if isinstance(obj, dict):
        lines = []
        for k, vs in obj.items():
            for v in vs:
                lines.append(f"{pad}{k}: {fmt(v, indent + 2)}")
        return "\n".join(lines) if lines else "{}"
    return repr(obj)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    d = PetDriver()
    print("driver ready:", d.script.exports_sync.status())

    if mode == "status":
        r = q_pet_state(d)
        print("== pet state ==")
        print("code:", r.get("respCode"), "msg:", r.get("respStr"),
              "sent@", r.get("sentTs"), "resp@", r.get("respTs"))
        dec = r.get("decoded")
        if dec:
            print(fmt(dec)[:3000])
        else:
            print("(no decoded response)")
    elif mode == "study":
        r = q_study_status(d)
        print("== study status ==")
        if r.get("decoded"):
            print(fmt(r["decoded"])[:2500])
        r2 = q_start_study(d)
        print("== start study ==")
        print("code:", r2.get("respCode"))
        if r2.get("decoded"):
            print(fmt(r2["decoded"])[:2500])
    elif mode == "academy":
        r = q_academy(d)
        print("== academy ==")
        if r.get("decoded"):
            print(fmt(r["decoded"])[:3000])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
