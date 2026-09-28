/**
 * 最终捕获：钩 QQKuiklyPlatformApi.call(method, params, callback)
 * - sendPbRequest 请求：cmd + protobuf(base64)
 * - 用动态代理包装 Function1 回调：响应内容也落盘
 */

function stamp() {
    return new Date().toISOString().slice(11, 23);
}

function safeStr(x, max) {
    try {
        if (x === null || x === undefined) return "null";
        var s = "" + x;
        return s.length > (max || 300) ? s.substring(0, max || 300) + "..." : s;
    } catch (e) {
        return "<err>";
    }
}

function b64Of(e) {
    try {
        var ArrayCls = Java.use("java.lang.reflect.Array");
        var ObjCls2 = Java.use("java.lang.Object");
        var E = Java.cast(e, ObjCls2);
        var cn = "" + E.getClass().getName();
        if (cn !== "[B") return null;
        var n = ArrayCls.getLength(E);
        var nums = [];
        for (var j = 0; j < n && j < 16384; j++) {
            var b = ArrayCls.get(E, j);
            try { nums.push(b.byteValue()); } catch (e2) { nums.push(b & 0xff); }
        }
        var jb = Java.array("byte", nums);
        var B64d = Java.use("android.util.Base64");
        return "B64:" + B64d.encodeToString(jb, 2);
    } catch (err) {
        return null;
    }
}

function dumpVal(e) {
    var u = unwrapArg(e);
    if (u !== null && u !== "null") return u;
    return safeStr(e, 800);
}

function unwrapArg(e) {
    try {
        if (e === null || e === undefined) return "null";
        var ObjCls = Java.use("java.lang.Object");
        var E = Java.cast(e, ObjCls);
        var cn = "" + E.getClass().getName();
        if (cn === "[B") return b64Of(E);
        if (cn.startsWith("[L")) {
            var ArrayCls = Java.use("java.lang.reflect.Array");
            var n = ArrayCls.getLength(E);
            var parts = [];
            for (var j = 0; j < Math.min(n, 12); j++) {
                var el = ArrayCls.get(E, j);
                var eb = b64Of(el);
                parts.push(eb !== null ? eb : safeStr(el, 900));
            }
            return "[" + parts.join(" § ") + "]";
        }
        return safeStr(E, 900);
    } catch (err) {
        return safeStr(e, 150);
    }
}

var cbSeq = 0;

function makeProxy(origCb) {
    var F1 = Java.use("kotlin.jvm.functions.Function1");
    var seq = ++cbSeq;
    var Proxy = Java.registerClass({
        name: "com.hook.pbcb" + seq,
        implements: [F1],
        methods: {
            invoke: function (arg) {
                try {
                    console.log("[RSP " + stamp() + "] cb#" + seq + " " + dumpVal(arg));
                } catch (e) { }
                return origCb.invoke(arg);
            }
        }
    });
    return Proxy.$new();
}

function install(factory) {
    var Api;
    try {
        Api = factory.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
    } catch (e) {
        return false;
    }
    try {
        var overloads = Api.call.overloads;
        overloads.forEach(function (ov) {
            ov.implementation = function () {
                var args = [];
                for (var i = 0; i < arguments.length; i++) args.push(arguments[i]);
                var methodName = "" + args[0];
                var interesting = /sendPbRequest|sendWebSSORequest|sendRequest/i.test(methodName);
                if (interesting) {
                    var detail = "";
                    for (var i = 1; i < args.length; i++) {
                        detail += unwrapArg(args[i]);
                        if (i < args.length - 1) detail += " ## ";
                    }
                    console.log("[REQ " + stamp() + "] " + methodName + " :: " + detail);
                    // 包装最后一个 Function1 参数
                    for (var i = args.length - 1; i >= 1; i--) {
                        var a = args[i];
                        if (a !== null && a !== undefined) {
                            try {
                                var F1c = Java.use("kotlin.jvm.functions.Function1");
                                var casted = Java.cast(a, F1c);
                                if (casted !== null) {
                                    args[i] = makeProxy(casted);
                                    break;
                                }
                            } catch (e) { }
                        }
                    }
                }
                return ov.apply(this, args);
            };
        });
        console.log("[*] QQKuiklyPlatformApi.call hooked (" + overloads.length + " overloads)");
        return true;
    } catch (e) {
        console.log("[!] hook call fail: " + e);
        return false;
    }
}

function bootstrap() {
    Java.perform(function () {
        var done = false;
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                if (done) return;
                try {
                    var f = Java.ClassFactory.get(loader);
                    f.use("com.tencent.mobileqq.ntcompose.export.modules.QQKuiklyPlatformApi");
                    install(f);
                    done = true;
                } catch (e) { }
            },
            onComplete: function () {
                if (!done) setTimeout(function () { Java.perform(bootstrap); }, 2000);
            }
        });
    });
}

Java.perform(function () {
    console.log("[*] final-capture script loaded");
    setTimeout(function () { send({ tag: "SELFTEST", preview: "send-ok-final" }); }, 2000);
    bootstrap();
});
