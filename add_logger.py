"""给 driver.js 加回调包装（makeLogger）。"""
src = open(r"G:\plugin_qq\driver.js", encoding="utf-8").read()

anchor = 'var r = ov.apply(this, args);\n                // call 层搭车（重测：null-bug 修复后）'
wrap_code = '''// 包装真实回调：记录所有到达的响应（搭车响应也流到这里）
                if (a0 === "sendPbRequest" && args.length >= 3 && args[2] !== null && args[2] !== undefined) {
                    try {
                        args[2] = makeLogger(args[2]);
                    } catch (e) { }
                }
                var r = ov.apply(this, args);
                // call 层搭车（重测：null-bug 修复后）'''

if "makeLogger" not in src:
    src = src.replace(anchor, wrap_code, 1)

# makeLogger 函数体（放在 makeProxy 之后）
if "function makeLogger" not in src:
    logger_fn = '''
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
'''
    # 插入在 makeProxy 函数结束之后（找 var cbSeq = 0; 或 rpc.exports 之前）
    idx = src.find("function bootstrap()")
    src = src[:idx] + logger_fn + "\n" + src[idx:]

# rpc 增加 resplog 读取
if "resplog" not in src:
    src = src.replace(
        '    clearresps: function () { respBuf = []; return "ok"; },',
        '    clearresps: function () { respBuf = []; return "ok"; },\n'
        '    resplog: function () { return JSON.stringify(respLog.slice(-25)); },\n'
        '    clearlog: function () { respLog = []; return "ok"; },'
    )

open(r"G:\plugin_qq\driver.js", "w", encoding="utf-8").write(src)
print("makeLogger added:", "function makeLogger" in src)
print("resplog rpc:", "resplog:" in src)
print("wrap in call:", "makeLogger(args[2])" in src)
