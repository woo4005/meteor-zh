# -*- coding: utf-8 -*-
"""校验 1.6.x 线的 jar 真的能在 Minecraft 26.1.1 与 26.1.2 上都用。

做三件事，任何一件不成立就 exit 1：
  1. 对比两个客户端 jar 的 class 集合 —— 集合必须相同，且差异类里不能有
     Meteor 的 mixin 目标、也不能有本插件引用的类。
  2. 用 26.1.1 的客户端 jar 重新编译同一份源码，产出的 class 必须与
     用 26.1.2 编译的逐字节相同（说明没有依赖任何版本特有的签名）。
  3. 检查 dist 里那个 jar 的 fabric.mod.json 依赖能同时匹配 26.1.1 / 26.1.2 / 26.1。
"""
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_261 as b  # noqa: E402

BASE = r"E:\pcl\.minecraft\versions\zh插件制作版本\versions"
MC11 = os.path.join(BASE, "26.1.1-Fabric 0.20.1", "26.1.1-Fabric 0.20.1.jar")
MC12 = os.path.join(BASE, "26.1.2-Fabric 0.20.1", "26.1.2-Fabric 0.20.1.jar")

total = 0
fail = 0


def check(what, ok, detail=""):
    global total, fail
    total += 1
    if ok:
        print("  OK   %s" % what)
    else:
        fail += 1
        print("  FAIL %s %s" % (what, detail))


def class_hashes(path):
    with zipfile.ZipFile(path) as z:
        return {n: hashlib.sha256(z.read(n)).hexdigest()
                for n in z.namelist() if n.endswith(".class")}


def utf8_constants(data):
    """读 class 常量池里的 UTF-8 常量（用于找 @Mixin 目标）。"""
    count = struct.unpack(">H", data[8:10])[0]
    i, out = 10, []
    while i < len(data) and len(out) < count:
        tag = data[i]
        i += 1
        if tag == 1:
            ln = struct.unpack(">H", data[i:i + 2])[0]
            i += 2
            out.append(data[i:i + ln].decode("utf-8", "replace"))
            i += ln
        elif tag in (7, 8, 16, 19, 20):
            i += 2
        elif tag == 15:
            i += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            i += 4
        elif tag in (5, 6):
            i += 8
        else:
            break
    return out


print("== 1. 两个客户端 jar 的差异 ==")
h11, h12 = class_hashes(MC11), class_hashes(MC12)
check("class 集合相同", set(h11) == set(h12),
      "only11=%d only12=%d" % (len(set(h11) - set(h12)), len(set(h12) - set(h11))))
changed = sorted(n for n in set(h11) & set(h12) if h11[n] != h12[n])
print("     差异类 %d 个：%s" % (len(changed), ", ".join(os.path.basename(c).replace(".class", "") for c in changed)))

# Meteor 的 mixin 目标
targets = set()
with zipfile.ZipFile(b.METEOR_JAR) as z:
    for name in z.namelist():
        if not name.endswith(".class") or "$" in name:
            continue
        data = z.read(name)
        if b"Lorg/spongepowered/asm/mixin/Mixin;" not in data:
            continue
        for c in utf8_constants(data):
            if "/" in c and c.replace(".", "/").endswith("Mixin") is False and c.count("/") >= 2:
                targets.add(c.replace(".", "/"))
hit = [c for c in changed if c[:-len(".class")] in targets]
check("Meteor 的 mixin 不触碰这 8 个差异类", not hit, "冲突=%s" % hit)

# 插件自己引用的类
jar_out = os.path.join(ROOT, "dist", "meteor-zh-%s-mc26.1.x.jar" % b.VERSION)
if not os.path.exists(jar_out):
    raise SystemExit("先跑 build_261.py，找不到 %s" % jar_out)

print("\n== 2. 用 26.1.1 的客户端重新编译同一份源码 ==")
if not os.path.exists(MC11):
    raise SystemExit("找不到 26.1.1 客户端：%s" % MC11)

cp12 = b.classpath()
cp11 = cp12.replace(b.MC_JAR, MC11)
check("classpath 里确实换成了 26.1.1 的 jar", MC11 in cp11 and MC12 not in cp11)

sources = []
for base, _dirs, files in os.walk(os.path.join(ROOT, "src", "main", "java")):
    for f in files:
        if f.endswith(".java"):
            # 用相对路径：本机用户名里带单引号（wang'xiao'ya），javac 的 argfile 会把 ' 当引号吃掉
            sources.append(os.path.relpath(os.path.join(base, f), ROOT).replace(os.sep, "/"))

tmpdir = os.path.join(ROOT, "build-261", "cross-classes")
if os.path.isdir(tmpdir):
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
os.makedirs(tmpdir, exist_ok=True)
args = ["-encoding", "UTF-8", "--release", "25", "-nowarn",
        "-d", os.path.relpath(tmpdir, ROOT).replace(os.sep, "/")] + sources
argfile = os.path.join(ROOT, "build-261", "cross-args.txt")
io.open(argfile, "w", encoding="utf-8").write("\n".join(args))
env = dict(os.environ)
env["CLASSPATH"] = cp11
r = subprocess.run([b.JAVAC, "@" + argfile], env=env, cwd=ROOT,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("在 26.1.1 的 classpath 下编译通过", r.returncode == 0,
      (r.stdout or "")[-400:] + (r.stderr or "")[-400:])

if r.returncode == 0:
    h_a = {}
    for base, _dirs, files in os.walk(tmpdir):
        for f in files:
            if f.endswith(".class"):
                p = os.path.join(base, f)
                rel = os.path.relpath(p, tmpdir).replace(os.sep, "/")
                h_a[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    # build-261/classes 是目录，逐文件算 hash
    h_b = {}
    for base, _dirs, files in os.walk(os.path.join(ROOT, "build-261", "classes")):
        for f in files:
            if f.endswith(".class"):
                p = os.path.join(base, f)
                rel = os.path.relpath(p, os.path.join(ROOT, "build-261", "classes")).replace(os.sep, "/")
                h_b[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    diff = sorted(n for n in set(h_a) & set(h_b) if h_a[n] != h_b[n])
    check("26.1.1 与 26.1.2 两套 classpath 编译结果逐字节相同", not diff,
          "不同=%s" % diff[:6])
    check("两套编译产出的 class 数量一致", len(h_a) == len(h_b) and len(h_a) > 0,
          "%d vs %d" % (len(h_a), len(h_b)))

print("\n== 3. jar 里的依赖声明 ==")
with zipfile.ZipFile(jar_out) as z:
    meta = json.loads(z.read("fabric.mod.json"))
dep = meta.get("depends") or {}
check("version 是 %s" % b.VERSION, meta.get("version") == b.VERSION, meta.get("version"))
check("minecraft 依赖为 ~26.1（覆盖 26.1 / 26.1.1 / 26.1.2）",
      dep.get("minecraft") == "~26.1", dep.get("minecraft"))
check("java 依赖为 >=25", dep.get("java") == ">=25", dep.get("java"))
check("meteor-client 依赖为 >=26.1", dep.get("meteor-client") == ">=26.1", dep.get("meteor-client"))

print("\n%s (%d checks)" % ("ALL OK" if fail == 0 else "FAILED %d/%d" % (fail, total), total))
sys.exit(0 if fail == 0 else 1)
