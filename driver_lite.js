/**
 * driver_lite2.js — 修正版：
 * - Java.retain 固定 delegate/arg 引用（解决 Wrapper disposed）
 * - 回调解析直接在 invoke 内完成（避免跨上下文）
 * - 搭车回调独立记录
 */

var pending = null;
var seenLoaders = {};
var carrier = false;
var respLog = [];
var loggerSeq = 0;
var proxySeq = 0;

function ts() { return new Date().toISOString().slice(11, 23); }
function mark(m) { console.log("[M] " + ts() + " " + m); }

function parseInto(entry, arg) {
    // 用 reflect.Array 反射访问（录制时代验证过的方法）
    try {
        var A = Java.retain(arg);
        var cls = A.getClass();
        var cn0 = "" + cls.getName();
        if (cn0 !== "[Ljava.lang.Object;") {
            entry.sig = cn0;
            return;
        }
        var ArrayCls = Java.use("java.lang.reflect.Array");
        var n = ArrayCls.getLength(A);
        var sig = [];
        for (var i = 0; i < n; i++) {
            var el = ArrayCls.get(A, i);
            if (el === null || el === undefined) { sig.push("null"); continue; }
            var cn = "" + el.getClass().getName();
            sig.push(cn.split(".").pop());
            if (cn === "[B") {
                try { entry.b64 = "" + Java.use("android.util.Base64").encodeToString(el, 2); }
                catch (b64err) {
                    try {
                        // 逐字节兜底（反射读每个字节）
                        var ArrayCls2 = Java.use("java.lang.reflect.Array");
                        var len2 = ArrayCls2.getLength(el);
                        var nums = [];
                        for (var j = 0; j < len2 && j < 8192; j++) {
                            var bj = ArrayCls2.get(el, j);
                            try { nums.push(bj.byteValue()); }
                            catch (be) { nums.push((bj & 0xff)); }
                        }
                        var jb = Java.array("byte", nums);
                        entry.b64 = "" + Java.use("android.util.Base64").encodeToString(jb, 2);
                    } catch (b64err2) { entry.b64 = "<b64err2:" + b64err2 + ">"; }
                }
            } else if (cn === "java.lang.Integer") {
                try { entry.code = Java.cast(el, Java.use("java.lang.Integer")).intValue(); }
                catch (ie) { entry.code = null; }
            } else if (cn === "java.lang.String") {
                try { entry.msg = ("" + el).substring(0, 120); }
                catch (se) { }
            }
        }
        entry.sig = "[" + sig.join(",") + "]";
    } catch (err) {
        var st1 = (err && err.stack) ? ("" + err.stack).split("\n").slice(0, 2).join(" | ") : "";
        entry.sig = "err:" + err + " @" + st1;
    }
}

function makeLogger(delegateRaw) {
    var delegate = Java.retain(delegateRaw);
    var F1 = Java.use("kotlin.jvm.functions.Function1");
    var P = Java.registerClass({
        name: "com.lite2.log" + (++loggerSeq),
        implements: [F1],
        methods: {
            invoke: function (arg) {
                var entry = { who: "real", ts: ts(), b64: null, code: null, msg: null };
                try {
                    Java.perform(function () {
                        parseInto(entry, arg);
                    });
                } catch (e) {
                    entry.sig = "outer:" + e;
                }
                respLog.push(entry);
                if (respLog.length > 60) respLog.shift();
                return delegate.invoke(arg);
            }
        }
    });
    return P.$new();
}

function makePiggyCb() {
    var F1 = Java.use("kotlin.jvm.functions.Function1");
    var P = Java.registerClass({
        name: "com.lite2.cb" + (++proxySeq),
        implements: [F1],
        methods: {
            invoke: function (arg) {
                var entry = { who: "PIGGY", ts: ts(), b64: null, code: null, msg: null };
                try {
                    Java.perform(function () {
                        parseInto(entry, arg);
                    });
                } catch (e) {
                    entry.sig = "outer:" + e;
                }
                if (pending) {
                    pending.respB64 = entry.b64;
                    pending.respCode = entry.code;
                    pending.respStr = entry.msg;
                    pending.respSig = entry.sig;
                    pending.respTs = entry.ts;
                    if (!pending.invocations) pending.invocations = [];
                    pending.invocations.push(JSON.stringify(entry));
                }
                respLog.push(entry);
                return null;
            }
        }
    });
    return P.$new();
}

function install(factory) {
    var Api;
    try {
        Api = factory.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
    } catch (e) { return; }
    Api.call.overloads.forEach(function (ov) {
        ov.implementation = function () {
            var args = [];
            for (var i = 0; i < arguments.length; i++) args.push(arguments[i]);
            var a0 = "" + args[0];
            if (a0 === "sendPbRequest") {
                carrier = true;
                if (args.length >= 3 && args[2] !== null && args[2] !== undefined) {
                    try {
                        args[2] = makeLogger(args[2]);
                    } catch (e) { mark("wrap-err " + e); }
                }
            }
            var r = ov.apply(this, args);
            if (a0 === "sendPbRequest") {
                mark("CHK pending=" + (pending !== null) +
                     (pending ? " sent=" + pending.sent + " err=" + (pending.err ? "Y" : "N") : "") +
                     " len=" + args.length);
            }
            if (pending && !pending.sent && !pending.err && a0 === "sendPbRequest") {
                try {
                    var JInt = Java.use("java.lang.Integer");
                    var JHM = Java.use("java.util.HashMap");
                    var JStr = Java.use("java.lang.String");
                    var AC = Java.use("java.util.Arrays");
                    var myBytes = Java.use("android.util.Base64").decode(pending.b64, 0);
                    var arr = Java.array("java.lang.Object", [
                        JStr.$new(pending.cmd), myBytes, JStr.$new(""), JInt.valueOf(0), JHM.$new()
                    ]);
                    var params = AC.asList(arr);
                    ov.apply(this, [args[0], params, makePiggyCb()]);
                    pending.sent = true;
                    pending.via = "call";
                    pending.sentTs = ts();
                    mark("PIGGY-SENT");
                } catch (e) {
                    pending.err = "" + e;
                    mark("piggy-err " + e);
                }
            }
            return r;
        };
    });
}

function bootstrap() {
    Java.perform(function () {
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                var key = "" + loader;
                if (seenLoaders[key]) return;
                seenLoaders[key] = 1;
                try { install(Java.ClassFactory.get(loader)); } catch (e) { }
            },
            onComplete: function () { console.log("[*] driver-lite2 installed"); }
        });
    });
}

rpc.exports = {
    status: function () { return JSON.stringify({ carrier: carrier, pending: pending !== null, logN: respLog.length }); },
    request: function (cmd, b64payload) {
        if (pending && !pending.sent && !pending.err) return JSON.stringify({ queued: false, err: "busy" });
        pending = { cmd: cmd, b64: b64payload, sent: false, err: null, respB64: null, invocations: null };
        return JSON.stringify({ queued: true });
    },
    result: function () { return JSON.stringify(pending); },
    resplog: function () { return JSON.stringify(respLog.slice(-25)); },
    reset: function () { pending = null; return "ok"; },
    // daemon 兼容桩
    paths: function () { return JSON.stringify([]); },
    responses: function () { return JSON.stringify([]); },
    clearresps: function () { return "ok"; }
};

Java.perform(function () {
    console.log("[*] driver-lite2 loaded");
    bootstrap();
});
