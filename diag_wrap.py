"""给 makeLogger 包装加诊断。"""
src = open(r".\driver.js", encoding="utf-8").read()

old = '''                if (a0 === "sendPbRequest" && args.length >= 3 && args[2] !== null && args[2] !== undefined) {
                    try {
                        args[2] = makeLogger(args[2]);
                    } catch (e) { }
                }'''
new = '''                if (a0 === "sendPbRequest" && args.length >= 3 && args[2] !== null && args[2] !== undefined) {
                    try {
                        args[2] = makeLogger(args[2]);
                        mark("cb-wrapped#" + loggerSeq);
                    } catch (e) {
                        mark("cb-wrap-ERR " + e);
                    }
                }'''
assert old in src, "anchor not found"
src = src.replace(old, new)
open(r".\driver.js", "w", encoding="utf-8").write(src)
print("diagnostics added")
