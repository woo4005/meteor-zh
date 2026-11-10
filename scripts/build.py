# -*- coding: utf-8 -*-
"""Compile the addon against the offline mojmap classpath, remap to intermediary and package."""
import io
import json
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 同目录的 _jarcheck（产物自检，两条构建线共用）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _jarcheck import validate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIKU = os.path.abspath(os.path.join(ROOT, "..", "miku-villager-mover"))
BO = os.path.join(MIKU, "build-offline")
JDK = r"C:\Users\wang'xiao'ya\AppData\Roaming\.minecraft\runtime\java-runtime-delta\bin"
JAVA = os.path.join(JDK, "java.exe")
JAVAC = os.path.join(JDK, "javac.exe")

BUILD = os.path.join(ROOT, "build")
CLASSES = os.path.join(BUILD, "classes")
DIST = os.path.join(ROOT, "dist")
MOD_ID = "meteor-zh"


def _read_props():
    """读 ``gradle.properties`` —— 两条线版本号与依赖表达式的单一事实来源。

    以前 ``VERSION`` 在这里和 ``build_261.py`` 各写一份，发版时两处必须手动对齐，
    出现过「dist 里是 1.4.7、脚本里写 1.4.3」的情况。现在两边都从这里读。
    """
    path = os.path.join(ROOT, "gradle.properties")
    props = {}
    if os.path.exists(path):
        with io.open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
    return props


PROPS = _read_props()

# 1.21.11 线的版本号。26.1 线用 mod_version_261，见 build_261.py。
VERSION = PROPS.get("mod_version") or "0.0.0"
# 两条线共用一份源码，靠文件名区分：1.21.11 线 -mc1.21.11.jar，26.1 线 -mc26.1.x.jar。
MC_VERSION = "1.21.11"

# fabric.mod.json 与 meteor-zh.mixins.json 里的 depends / compatibilityLevel 都只写占位符，
# 两条构建路径各自展开（Gradle 走 processResources.expand，这里走 expand()）。
DEPS = {
    "version": VERSION,
    "minecraft_dep": "~" + MC_VERSION,
    "java_dep": ">=" + (PROPS.get("java_level") or "21"),
    # 注意 ">=1.21.11-0" 而不是 ">=1.21.11"：Fabric 的 semver 把 meteor-client 的
    # "1.21.11-86" 当成 1.21.11 的预发布版，预发布版 < 正式版，于是 ">=1.21.11"
    # 反而不满足，启动时报 HARD_DEP_NO_CANDIDATE。加 -0 后正好落在区间内。
    "meteor_client_dep": ">=" + MC_VERSION + "-0",
    # MC 1.21.11 的 class 是 major 65（Java 21），Mixin 按 JAVA_21 解析。
    "compatibility_level": "JAVA_21",
}

# 产物里必须存在的东西（少一条说明资源复制或编译某步静默失败了）。
REQUIRED_ENTRIES = (
    "fabric.mod.json",
    "meteor-zh.mixins.json",
    "assets/meteorzh/lang/zh.json",
    "assets/meteorzh/lang/chat.json",
    "assets/meteorzh/lang/words.json",
    "assets/meteorzh/icon.png",
    "com/meteorzh/MeteorZh.class",
    "com/meteorzh/FontFixer.class",
    "com/meteorzh/Translator.class",
    "com/meteorzh/ZhDict.class",
    "com/meteorzh/ChatDict.class",
    "com/meteorzh/Dumper.class",
    "com/meteorzh/AboutModule.class",
    "com/meteorzh/UpdateChecker.class",
    "com/meteorzh/ZhCommand.class",
    "com/meteorzh/WordTranslator.class",
    "com/meteorzh/mixin/GuiRendererMixin.class",
    "com/meteorzh/mixin/ChatUtilsMixin.class",
)


def read_classpath():
    with io.open(os.path.join(BO, "javac.args"), "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    for i, line in enumerate(lines):
        if line == "-cp" and i + 1 < len(lines):
            return lines[i + 1]
    raise SystemExit("cannot find -cp in javac.args")


def run(cmd, **kw):
    print("+ " + " ".join(cmd[:2] if len(cmd) > 2 else cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit("command failed: %s" % cmd[0])
    return r


def sources():
    out = []
    src = os.path.join(ROOT, "src", "main", "java")
    for base, _, files in os.walk(src):
        for name in files:
            if name.endswith(".java"):
                out.append(os.path.join(base, name))
    return out


def wipe(path):
    """Best-effort delete of a directory tree.

    The project lives inside OneDrive, and OneDrive/Defender sometimes keep a handle on
    a freshly written folder — shutil.rmtree then dies with WinError 5 even though every
    file is removable. Retry a few times, then fall back to deleting file by file and
    carrying on: stale class files are harmless because javac overwrites whatever it
    compiles and copy_resources() refreshes every resource.
    """
    import time
    for attempt in range(5):
        if not os.path.isdir(path):
            return
        try:
            shutil.rmtree(path)
            return
        except OSError:
            time.sleep(0.3 * (attempt + 1))

    for base, dirs, files in os.walk(path, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(base, name))
            except OSError:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(base, name))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        print("warning: could not fully remove %s (a file is locked); continuing" % path)


def compile_java():
    wipe(CLASSES)
    os.makedirs(CLASSES, exist_ok=True)

    files = sources()

    # A classpath this long (230 entries, ~21 KB) does not survive javac argument
    # files reliably, so hand it over through the CLASSPATH environment variable and
    # put only the source files in the argument file.
    env = dict(os.environ)
    env["CLASSPATH"] = read_classpath()

    # Run from the project root and use relative paths: absolute Windows paths with
    # single quotes are fragile inside javac argument files.
    argfile = os.path.join(BUILD, "javac.args")
    with io.open(argfile, "w", encoding="utf-8") as f:
        f.write("-encoding\nUTF-8\n")
        f.write("--release\n21\n")
        f.write("-d\nbuild/classes\n")
        f.write("-nowarn\n")
        for s in files:
            f.write('"%s"\n' % os.path.relpath(s, ROOT).replace("\\", "/"))

    r = subprocess.run([JAVAC, "@" + argfile], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, cwd=ROOT)
    print(r.stdout, end="")
    print(r.stderr, end="")
    if r.returncode != 0:
        raise SystemExit("javac failed")
    print("compiled %d sources" % len(files))


def expand(text):
    """把资源里的 ${placeholder} 展开成实际值。

    源文件只写占位符，Gradle 与离线脚本各自展开 —— 两条构建路径因此产出同一份语义。
    以前是「匹配到某个精确字面量再 replace」，源文件一改格式（重排、加空格）替换就
    静默失效，而产物校验又只看 JSON 能否解析，于是 Gradle 产物缺 java/meteor-client
    依赖也一直没人发现。
    """
    out = text
    for key, value in DEPS.items():
        out = out.replace("${%s}" % key, value)
    return out


def copy_resources():
    """Copy resources into the class output dir, expanding placeholders."""
    res = os.path.join(ROOT, "src", "main", "resources")
    for base, _, files in os.walk(res):
        for name in files:
            src = os.path.join(base, name)
            rel = os.path.relpath(src, res)
            dst = os.path.join(CLASSES, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if name.endswith(".json"):
                with io.open(src, "r", encoding="utf-8") as f:
                    text = expand(f.read())
                left = text.find("${")
                if left >= 0:
                    raise SystemExit("资源里还有未展开的占位符：%s -> %s"
                                     % (rel, text[left:left + 40]))
                with io.open(dst, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            else:
                shutil.copy2(src, dst)


def jar_dir(out_path):
    import zipfile
    if os.path.exists(out_path):
        os.remove(out_path)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(CLASSES):
            for name in files:
                full = os.path.join(base, name)
                rel = os.path.relpath(full, CLASSES).replace(os.sep, "/")
                z.write(full, rel)
    return out_path


def remap(src_jar, out_jar):
    mappings = os.path.join(MIKU, "mappings", "mojmap_to_intermediary.txt")
    remap_tool = os.path.join(MIKU, "tools", "RemapJar.java")
    tool_classes = os.path.join(BUILD, "tool-classes")
    tool_class = os.path.join(tool_classes, "RemapJar.class")

    # Compare timestamps instead of "class file exists" — otherwise an edited
    # RemapJar.java keeps being ignored forever.
    needs_build = True
    if os.path.exists(tool_class):
        needs_build = os.path.getmtime(remap_tool) > os.path.getmtime(tool_class)
    if needs_build:
        if os.path.isdir(tool_classes):
            shutil.rmtree(tool_classes)
        os.makedirs(tool_classes)
        env = dict(os.environ)
        env["CLASSPATH"] = read_classpath()  # provides the ASM jars RemapJar needs
        run([JAVAC, "-encoding", "UTF-8", "-d", tool_classes, remap_tool], env=env)

    run([JAVA, "-cp", tool_classes + os.pathsep + read_classpath(), "RemapJar",
         mappings, src_jar, out_jar], cwd=BUILD)


def main():
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    compile_java()
    copy_resources()

    mojmap_jar = os.path.join(BUILD, "addon-mojmap.jar")
    jar_dir(mojmap_jar)
    print("packed mojmap jar: %d bytes" % os.path.getsize(mojmap_jar))

    inter_jar = os.path.join(BUILD, "addon-intermediary.jar")
    remap(mojmap_jar, inter_jar)
    print("remapped: %d bytes" % os.path.getsize(inter_jar))

    final = os.path.join(DIST, "%s-%s-mc%s.jar" % (MOD_ID, VERSION, MC_VERSION))
    shutil.copy2(inter_jar, final)
    print("output: %s (%d bytes)" % (final, os.path.getsize(final)))

    # 产物自检（与 26.1 线共用 scripts/_jarcheck.py）。MC 1.21.11 的 class 是 major 65。
    validate(final, version=VERSION, minecraft_dep=DEPS["minecraft_dep"],
             compatibility_level=DEPS["compatibility_level"], expect_major=65,
             required_entries=REQUIRED_ENTRIES)


if __name__ == "__main__":
    main()
