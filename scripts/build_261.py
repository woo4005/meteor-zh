# -*- coding: utf-8 -*-
"""为 Minecraft 26.1 构建 meteor-zh。

与 1.21.11 的 build.py 的关键差别：
  1. MC 26.x 起游戏不再混淆，运行时就是官方名，所以 **不需要** mojmap -> intermediary 的 remap。
  2. Meteor 26.1 的 class 文件是 major 69（Java 25），javac 21 读不了，必须用 JDK 25。
  3. fabric.mod.json 的 minecraft 依赖从 ~1.21.11 变成 ~26.1。

用法：
    python scripts/build_261.py
产物：
    dist/meteor-zh-1.5.0-mc26.1.jar
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.5.0"
MOD_ID = "meteor-zh"

INSTANCE = r"E:\pcl\.minecraft\versions\26.1-Fabric 0.20.1"
MC_JAR = os.path.join(INSTANCE, "26.1-Fabric 0.20.1.jar")
VERSION_JSON = os.path.join(INSTANCE, "26.1-Fabric 0.20.1.json")
LIB_ROOT = r"E:\pcl\.minecraft\libraries"
METEOR_JAR = os.path.join(ROOT, "build-261", "meteor-client-26.1.2-20260810.135545-42.jar")

BUILD = os.path.join(ROOT, "build-261")
CLASSES = os.path.join(BUILD, "classes")
STAGE = os.path.join(BUILD, "stage")
JAR_OUT = os.path.join(BUILD, "addon-261.jar")
DIST = os.path.join(ROOT, "dist")
SRC = os.path.join(ROOT, "src", "main", "java")
RES = os.path.join(ROOT, "src", "main", "resources")

RT = os.path.join(os.environ["APPDATA"], ".minecraft", "runtime")
JDK = os.path.join(RT, "java-runtime-epsilon", "bin")
JAVAC = os.path.join(JDK, "javac.exe")
JAR = os.path.join(JDK, "jar.exe")


def _from_coord(name):
    """net.fabricmc:fabric-loader:0.20.1 -> net/fabricmc/fabric-loader/0.20.1/fabric-loader-0.20.1.jar
    fabric-loader / sponge-mixin 这几个库在 PCL 的 version json 里没有 downloads.artifact，
    但 jar 确实躺在 libraries 下，所以要用坐标自己拼路径。"""
    parts = name.split(":")
    if len(parts) < 3:
        return None
    group, artifact, version = parts[0], parts[1], parts[2]
    return "%s/%s/%s/%s-%s.jar" % (group.replace(".", "/"), artifact, version, artifact, version)


def library_jars():
    with open(VERSION_JSON, encoding="utf-8") as fh:
        meta = json.load(fh)
    out, skipped = [], []
    for lib in meta.get("libraries", []):
        path = (lib.get("downloads") or {}).get("artifact", {}).get("path")
        cands = []
        if path:
            cands.append(path)
        guess = _from_coord(lib.get("name", ""))
        if guess and guess not in cands:
            cands.append(guess)
        found = None
        for c in cands:
            full = os.path.join(LIB_ROOT, c.replace("/", os.sep))
            if os.path.exists(full):
                found = full
                break
        if found:
            out.append(found)
        else:
            skipped.append(lib.get("name"))
    if skipped:
        print("  (跳过 %d 个本机没有的库)" % len(skipped))
        for s in skipped[:6]:
            print("     -", s)
    return out


def nested_jars():
    """Meteor 自己把 orbit / gson / starscript 等打进 META-INF/jars/ 里，
    javac 不能直接读嵌套 jar，必须先解出来才拿得到 meteordevelopment.orbit.EventHandler。"""
    out_dir = os.path.join(BUILD, "libs")
    os.makedirs(out_dir, exist_ok=True)
    out = []
    with zipfile.ZipFile(METEOR_JAR) as z:
        names = z.namelist()
        mod = json.loads(z.read("fabric.mod.json").decode("utf-8"))
        for entry in mod.get("jars", []):
            path = entry.get("file")
            if not path or path not in names:
                continue
            dst = os.path.join(out_dir, os.path.basename(path))
            with z.open(path) as src, open(dst, "wb") as fh:
                shutil.copyfileobj(src, fh)
            out.append(dst)
    print("  meteor 内嵌 jar: %d 个（orbit/gson/... 已解出）" % len(out))
    return out


def classpath():
    parts = [MC_JAR, METEOR_JAR] + library_jars() + nested_jars()
    missing = [p for p in parts[:2] if not os.path.exists(p)]
    if missing:
        raise SystemExit("关键 jar 不存在: " + ", ".join(missing))
    return os.pathsep.join(parts)


def java_sources():
    out = []
    for base, _dirs, files in os.walk(SRC):
        for f in files:
            if f.endswith(".java"):
                out.append(os.path.join(base, f))
    return sorted(out)


def run(cmd, env_extra=None, cwd=None):
    env = os.environ.copy()
    env["JAVA_HOME"] = os.path.dirname(JDK).rstrip(os.sep)
    if env_extra:
        env.update(env_extra)
    print("  $", os.path.basename(cmd[0]), " ".join(os.path.basename(a) for a in cmd[1:6]), "...")
    r = subprocess.run(cmd, capture_output=True, env=env, cwd=cwd or ROOT)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    if r.returncode != 0:
        print(out[-6000:])
        raise SystemExit("命令失败: %s" % cmd[0])
    return out


def compile_java():
    if os.path.isdir(CLASSES):
        shutil.rmtree(CLASSES)
    os.makedirs(CLASSES, exist_ok=True)
    sources = java_sources()
    rel = [os.path.relpath(p, ROOT).replace(os.sep, "/") for p in sources]
    args = ["-encoding", "UTF-8", "-nowarn", "-d", os.path.relpath(CLASSES, ROOT).replace(os.sep, "/")] + rel
    argfile = os.path.join(BUILD, "javac.args")
    with open(argfile, "w", encoding="utf-8") as fh:
        fh.write("\n".join(args))
    print("compiling %d sources (JDK 25)" % len(sources))
    run([JAVAC, "@" + os.path.relpath(argfile, ROOT).replace(os.sep, "/")],
        env_extra={"CLASSPATH": classpath()})


def copy_resources():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE, exist_ok=True)
    for base, _dirs, files in os.walk(RES):
        for f in files:
            src = os.path.join(base, f)
            rel = os.path.relpath(src, RES)
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if rel.replace(os.sep, "/") == "fabric.mod.json":
                with open(src, encoding="utf-8") as fh:
                    text = fh.read()
                text = text.replace("${version}", VERSION)
                text = text.replace('"minecraft": "~1.21.11"', '"minecraft": "~26.1"')
                text = text.replace('"minecraft": ">=1.21.9"', '"minecraft": "~26.1"')
                # MC 26.x 的 class 是 Java 25 编的，必须声明 java 依赖，否则低版本 JVM 会拿到
                # UnsupportedClassVersionError 而不是一条清楚的「需要 Java 25」。
                if '"java"' not in text:
                    text = text.replace('"minecraft": "~26.1"',
                                        '"minecraft": "~26.1",\n    "java": ">=25"')
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            else:
                shutil.copy2(src, dst)

    for base, _dirs, files in os.walk(CLASSES):
        for f in files:
            src = os.path.join(base, f)
            rel = os.path.relpath(src, CLASSES)
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def pack():
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "meteor-zh-%s-mc26.1.jar" % VERSION)
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, _dirs, files in os.walk(STAGE):
            for f in files:
                full = os.path.join(base, f)
                arc = os.path.relpath(full, STAGE).replace(os.sep, "/")
                z.write(full, arc)
    print("jar: %s (%d bytes)" % (out, os.path.getsize(out)))
    return out


def main():
    print("Meteor-ZH %s for Minecraft 26.1" % VERSION)
    compile_java()
    copy_resources()
    out = pack()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    print("\n%d entries:" % len(names))
    for n in sorted(names):
        print("  " + n)


if __name__ == "__main__":
    main()
