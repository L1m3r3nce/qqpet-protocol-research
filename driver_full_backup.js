/**
 * driver.js v5 — 全路径观测 + 多层搭车
 * - call()/y()/v() 全部记录触发（paths 环），call 级 carrier
 * - 搭车：优先 y() 层（换bytes重放），否则 call 层同步重放
 * - P() 响应环 + 请求级回调代理捕获
 */

var pending = null;
var yArgs = null, yOv = null;
var seenLoaders = {};
var carrier = false;
var paths = [];   // {ts, tag}
var respBuf = []; // P() 响应

function ts() { return new Date().toISOString().slice(11, 23); }

function mark(tag) {
    paths.push(ts() + " " + tag);
    if (paths.length > 60) paths.shift();
}

function b64e(bytesObj) {
    try { return "" + Java.use("android.util.Base64").encodeToString(bytesObj, 2); }
    catch (e) { return null; }
}

var proxySeq = 0;
function makeProxy(delegate) {
    // 捕获响应并透传给原始回调（App 不受影响）
    var F1 = Java.use("kotlin.jvm.functions.Function1");
    var P = Java.registerClass({
        name: "com.hook.v5cb" + (++proxySeq),
        implements: [F1],
        methods: {
            invoke: function (arg) {
                try {
                    if (pending) {
                        var ArrayCls = Java.use("java.lang.reflect.Array");
                        var ObjCls = Java.use("java.lang.Object");
                        var A = Java.cast(arg, ObjCls);
                        var cn0 = "" + A.getClass().getName();
                        var got = false;
                        var sig = [];
                        var n = ArrayCls.getLength(A);
                        for (var i = 0; i < n; i++) {
                            var el = ArrayCls.get(A, i);
                            if (el === null || el === undefined) { sig.push("null"); continue; }
                            var cn = "" + Java.cast(el, ObjCls).getClass().getName();
                            sig.push(cn.split(".").pop());
                            if (cn === "[B") { pending.respB64 = b64e(el); got = true; }
                            else if (cn === "java.lang.Integer") { pending.respCode = el.intValue(); got = true; }
                            else if (cn === "java.lang.String") { pending.respStr = ("" + el).substring(0, 150); got = true; }
                        }
                        if (!pending.invocations) pending.invocations = [];
                        pending.invocations.push(cn0.split(".").pop() + "[" + sig.join(",") + "]");
                        if (!got) pending.respRaw = cn0 + " :: " + ("" + A).substring(0, 150);
                        pending.respTs = ts();
                    }
                } catch (e) { }
                return delegate ? delegate.invoke(arg) : null;
            }
        }
    });
    return P.$new();
}

function buildCallArgs(ovArgsTemplate, myB64) {
    // 以真实 call 参数为模板：[method, params(list), callback]
    var JInt = Java.use("java.lang.Integer");
    var JHM = Java.use("java.util.HashMap");
    var B64 = Java.use("android.util.Base64");
    var AC = Java.use("java.util.Arrays");
    var bytes = B64.decode(myB64, 0);
    var arr = Java.array("java.lang.Object", [
        pending.cmdStr, bytes, null, JInt.valueOf(0), JHM.$new()
    ]);
    return AC.asList(arr);
}

var yCallCount = 0;
var lastSkip = "none";

function installAll(factory) {
    var Api;
    try {
        Api = factory.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
    } catch (e) { return; }

    // ---- call() ----
    try {
        Api.call.overloads.forEach(function (ov) {
            ov.implementation = function () {
                var args = [];
                for (var i = 0; i < arguments.length; i++) args.push(arguments[i]);
                var a0 = "" + args[0];
                if (a0.indexOf("Pb") >= 0 || a0.indexOf("SSO") >= 0 || a0.indexOf("Request") >= 0) {
                    mark("call:" + a0);
                    carrier = true;
                }
                // 包装真实回调：记录所有到达的响应（搭车响应也流到这里）
                if (a0 === "sendPbRequest" && args.length >= 3 && args[2] !== null && args[2] !== undefined) {
                    try {
                        args[2] = makeLogger(args[2]);
                        mark("cb-wrapped#" + loggerSeq);
                    } catch (e) {
                        mark("cb-wrap-ERR " + e);
                    }
                }
                var r = ov.apply(this, args);
                // call 层搭车（重测：null-bug 修复后）
                if (pending && !pending.sent && !pending.err && a0 === "sendPbRequest") {
                    try {
                        pending.cmdStr = args[0];
                        var JInt2 = Java.use("java.lang.Integer");
                        var JHM2 = Java.use("java.util.HashMap");
                        var AC2 = Java.use("java.util.Arrays");
                        var myBytes = Java.use("android.util.Base64").decode(pending.b64, 0);
                        var arr2 = Java.array("java.lang.Object", [
                            pending.cmdStr, myBytes, null, JInt2.valueOf(0), JHM2.$new()
                        ]);
                        var params2 = AC2.asList(arr2);
                        var cb2 = makeProxy(args[2] && args[2] !== null ? null : null);
                        ov.apply(this, [args[0], params2, cb2]);
                        pending.sent = true;
                        pending.via = "call";
                        pending.sentTs = ts();
                        mark("piggy:call-sent");
                    } catch (e) {
                        pending.err = "" + e;
                        mark("piggy:call-err");
                    }
                }
                return r;
            };
        });
    } catch (e) { }

    // ---- y() ----
    try {
        Api.y.overloads.forEach(function (ov) {
            if (yOv !== null) return;
            yOv = ov;
            ov.implementation = function () {
                var args = [];
                for (var i = 0; i < arguments.length; i++) args.push(arguments[i]);
                yCallCount++;
                mark("y:len" + args.length);
                var r;
                try {
                    r = ov.apply(this, args);
                } catch (applyErr) {
                    mark("y:APPLY-ERR " + applyErr);
                    lastSkip = "y#" + yCallCount + ":apply-err";
                    throw applyErr;
                }
                yArgs = args;
                if (!pending) {
                    lastSkip = "y#" + yCallCount + ":pending-null";
                } else if (pending.sent) {
                    lastSkip = "y#" + yCallCount + ":already-sent";
                } else if (pending.err) {
                    lastSkip = "y#" + yCallCount + ":err=" + pending.err;
                } else {
                    lastSkip = "y#" + yCallCount + ":FIRE";
                    try {
                        var B64 = Java.use("android.util.Base64");
                        var JStrCls = Java.use("java.lang.String");
                        var c2 = args.slice(0);
                        c2[1] = JStrCls.$new(pending.cmd);           // 命令名换成我的
                        c2[3] = B64.decode(pending.b64, 0);           // byte[] 载荷换成我的
                        if (args.length > 10 && args[10]) {
                            c2[10] = makeProxy(args[10]);              // 捕获+透传代理
                        }
                        yOv.apply(this, c2);
                        pending.sent = true;
                        pending.via = "y";
                        pending.sentTs = ts();
                        mark("piggy:y-sent");
                    } catch (e) {
                        pending.err = "" + e;
                        mark("piggy:y-err");
                    }
                }
                return r;
            };
        });
    } catch (e) { }

    // ---- v() 记录 ----
    try {
        Api.v.overloads.forEach(function (ov) {
            ov.implementation = function () {
                mark("v");
                return ov.apply(this, arguments);
            };
        });
    } catch (e) { }

    // ---- P() 响应 ----
    try {
        var Core = factory.use("com.tencent.kuikly.core.render.android.core.KuiklyRenderCore");
        Core.P.overloads.forEach(function (ov) {
            ov.implementation = function (cbId, result) {
                try {
                    var b = null;
                    try { b = b64e(result); } catch (e) { }
                    respBuf.push({ ts: ts(), cbId: "" + cbId, b64: b });
                    if (respBuf.length > 60) respBuf.shift();
                } catch (e) { }
                return ov.apply(this, arguments);
            };
        });
    } catch (e) { }
}


var loggerSeq = 0;
var respLog = [];   // 所有经包装回调到达的响应

function makeLogger(delegate) {
    var F1 = Java.use("kotlin.jvm.functions.Function1");
    var P = Java.registerClass({
        name: "com.hook.v5log" + (++loggerSeq),
        implements: [F1],
        methods: {
            invoke: function (arg) {
                try {
                    var entry = { ts: ts(), n: loggerSeq, b64: null, code: null, msg: null };
                    var ArrayCls = Java.use("java.lang.reflect.Array");
                    var ObjCls = Java.use("java.lang.Object");
                    var A = Java.cast(arg, ObjCls);
                    var cn0 = "" + A.getClass().getName();
                    if (cn0 === "[Ljava.lang.Object;") {
                        var n = ArrayCls.getLength(A);
                        for (var i = 0; i < n; i++) {
                            var el = ArrayCls.get(A, i);
                            if (el === null || el === undefined) continue;
                            var cn = "" + Java.cast(el, ObjCls).getClass().getName();
                            if (cn === "[B") entry.b64 = b64e(el);
                            else if (cn === "java.lang.Integer") entry.code = el.intValue();
                            else if (cn === "java.lang.String") entry.msg = ("" + el).substring(0, 100);
                        }
                    }
                    respLog.push(entry);
                    if (respLog.length > 80) respLog.shift();
                } catch (e) { }
                return delegate.invoke(arg);
            }
        }
    });
    return P.$new();
}

function bootstrap() {
    Java.perform(function () {
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                var key = "" + loader;
                if (seenLoaders[key]) return;
                seenLoaders[key] = 1;
                try { installAll(Java.ClassFactory.get(loader)); } catch (e) { }
            },
            onComplete: function () { console.log("[*] driver v5 installed"); }
        });
    });
}

rpc.exports = {
    status: function () {
        return JSON.stringify({ carrier: carrier, pending: pending !== null, yCalls: yCallCount, lastSkip: lastSkip });
    },
    paths: function () { return JSON.stringify(paths.slice(-40)); },
    request: function (cmd, b64payload) {
        if (pending && !pending.sent && !pending.err) return JSON.stringify({ queued: false, err: "busy" });
        pending = { cmd: cmd, b64: b64payload, sent: false, err: null, respB64: null, respCode: null, respStr: null, respRaw: null, via: null };
        return JSON.stringify({ queued: true });
    },
    result: function () { return JSON.stringify(pending); },
    responses: function () { return JSON.stringify(respBuf.slice(-20)); },
    clearresps: function () { respBuf = []; return "ok"; },
    resplog: function () { return JSON.stringify(respLog.slice(-25)); },
    clearlog: function () { respLog = []; return "ok"; },
    reset: function () { pending = null; return "ok"; }
};

Java.perform(function () {
    console.log("[*] pet driver v5 loaded");
    bootstrap();
});
