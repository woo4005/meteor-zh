# -*- coding: utf-8 -*-
"""为 Minecraft 26.1.x 构建 meteor-zh（1.6.x 线）。

与 1.21.11 的 build.py 的关键差别：
  1. MC 26.x 起游戏不再混淆，运行时就是官方名，所以 **不需要** mojmap -> intermediary 的 remap。
  2. Meteor 26.1 的 class 文件是 major 69（Java 25），javac 21 读不了，必须用 JDK 25。
  3. fabric.mod.json 的 minecraft 依赖从 ~1.21.11 变成 ~26.1。

关于「一个 jar 覆盖 26.1.1 与 26.1.2」：
  Meteor 官方 26.1 线只发布了 26.1.2-42 一个客户端（它的 fabric.mod.json 声明
  minecraft "~26.1"），26.1.1 玩家用的就是同一个客户端。
  实测对比 26.1.1 与 26.1.2 两个客户端 jar：class 集合完全相同（各 10682 个），
  只有 8 个类有差异（DetectedVersion / SharedConstants / Checkbox 三个 /
  AbstractReportScreen 两个 / ServerGamePacketListenerImpl），
  其中没有一个被 Meteor 的 211 个 mixin 触及，本插件引用的类也逐字节相同。
  所以按 26.1.2 编译出的 jar 可以直接放到 26.1.1 上跑。
  scripts/verify_261_cross.py 会把这一点固化成可重复的检查。

用法：
    python scripts/build_261.py
产物：
    dist/meteor-zh-<版本>-mc26.1.x.jar（同一个 jar 覆盖 26.1 / 26.1.1 / 26.1.2）
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 同目录的 _jarcheck（产物自检，两条构建线共用）。脚本可能从任意 cwd 启动，
# 所以把 scripts/ 插进 sys.path 再 import。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _jarcheck import validate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_props():
    """读 ``gradle.properties`` —— 两条线版本号与依赖表达式的单一事实来源。"""
    path = os.path.join(ROOT, "gradle.properties")
    props = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
    return props


PROPS = _read_props()
VERSION = PROPS.get("mod_version_261") or "0.0.0"
MOD_ID = "meteor-zh"
MC_VERSION = "26.1"
MC_VERSIONS_DEP = "~26.1"

# fabric.mod.json / mixins.json 里能出现的全部占位符（源文件只写占位符）。
DEPS = {
    "version": VERSION,
    "minecraft_dep": MC_VERSIONS_DEP,
    "java_dep": ">=" + (PROPS.get("java_level_261") or "25"),
    "meteor_client_dep": ">=" + MC_VERSION,
    # MC 26.x 的 class 是 Java 25（major 69）编的，Mixin 必须按 JAVA_25 解析；
    # 1.21.11 线走 build.py，那边是 JAVA_21。
    "compatibility_level": "JAVA_25",
}


def expand(text):
    """展开资源里的 ${placeholder}（两条构建路径语义一致，不再靠字符串 replace 猜格式）。"""
    out = text
    for key, value in DEPS.items():
        out = out.replace("${%s}" % key, value)
    return out


DEFAULT_INSTANCE = os.environ.get("MC_INSTANCE") or r"E:\pcl\.minecraft\versions\26.1-Fabric 0.20.1"
INSTANCE = DEFAULT_INSTANCE
LIB_ROOT = os.environ.get("MC_LIB_ROOT") or r"E:\pcl\.minecraft\libraries"


def _require_instance(path):
    """实例目录不存在时给出可操作的报错，而不是一句 FileNotFoundError。"""
    if os.path.isdir(path):
        return path
    parent = os.path.dirname(path.rstrip("\\/"))
    known = []
    if os.path.isdir(parent):
        known = sorted(d for d in os.listdir(parent) if os.path.isdir(os.path.join(parent, d)))
    raise SystemExit(
        "26.1 实例目录不存在：%s\n该目录下的实例有：%s\n用环境变量 MC_INSTANCE 指定一个。"
        % (path, ", ".join(known) or "(空)"))


INSTANCE = _require_instance(INSTANCE)


def _instance_file(ext):
    """在实例目录里找客户端 jar / version json（只看顶层文件，不碰 mods）。"""
    name = os.path.basename(INSTANCE.rstrip("\\/"))
    cand = os.path.join(INSTANCE, name + ext)
    if os.path.exists(cand):
        return cand
    cands = sorted(os.path.join(INSTANCE, f) for f in os.listdir(INSTANCE)
                   if f.lower().endswith(ext) and os.path.isfile(os.path.join(INSTANCE, f)))
    if not cands:
        raise SystemExit("找不到实例文件 %s（目录：%s）" % (ext, INSTANCE))
    return cands[0]


MC_JAR = _instance_file(".jar")
VERSION_JSON = _instance_file(".json")


def _find_meteor_jar():
    """Meteor 的快照文件名带构建时间戳，每次更新都会变，所以按 mtime 取最新的。"""
    cands = [c for c in glob.glob(os.path.join(ROOT, "build-261", "meteor-client-26.1*.jar"))
             if not c.endswith("-sources.jar")]
    if not cands:
        raise SystemExit(
            "找不到 Meteor 26.1 的 jar —— 请把 meteor-client-26.1*.jar 下载到 build-261/ 目录")
    return max(cands, key=os.path.getmtime)


METEOR_JAR = _find_meteor_jar()

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


def wipe(path):
    """尽力删除目录树。

    项目在 OneDrive 里，OneDrive/Defender 偶尔会攥住刚写过的文件夹，导致
    shutil.rmtree 报 WinError 5（拒绝访问）—— 明明文件都能删。这里重试几次，
    再退化成逐个文件删除：残留的旧 class 无害，javac 会覆盖它编译的那部分，
    copy_resources() 也会把资源整份刷新。
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
        print("warning: 目录未完全删除（有文件被占用），继续构建: %s" % path)


def compile_java():
    wipe(CLASSES)
    os.makedirs(CLASSES, exist_ok=True)
    sources = java_sources()
    rel = [os.path.relpath(p, ROOT).replace(os.sep, "/") for p in sources]
    # --release 25 不能省：现在 major=69 只是因为碰巧用 JDK 25 编译，
    # 换一台机器上更高版本的 JDK 就会产出 Java 26 字节码，游戏里直接
    # UnsupportedClassVersionError。
    args = ["-encoding", "UTF-8", "--release", "25", "-nowarn",
            "-d", os.path.relpath(CLASSES, ROOT).replace(os.sep, "/")] + rel
    argfile = os.path.join(BUILD, "javac.args")
    with open(argfile, "w", encoding="utf-8") as fh:
        fh.write("\n".join(args))
    print("compiling %d sources (JDK 25)" % len(sources))
    run([JAVAC, "@" + os.path.relpath(argfile, ROOT).replace(os.sep, "/")],
        env_extra={"CLASSPATH": classpath()})


def copy_resources():
    wipe(STAGE)
    os.makedirs(STAGE, exist_ok=True)
    for base, _dirs, files in os.walk(RES):
        for f in files:
            src = os.path.join(base, f)
            rel = os.path.relpath(src, RES)
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if f.endswith(".json"):
                with open(src, encoding="utf-8") as fh:
                    text = fh.read()
                text = expand(text)
                left = text.find("${")
                if left >= 0:
                    raise SystemExit("资源里还有未展开的占位符：%s -> %s"
                                     % (rel, text[left:left + 40]))
                with open(dst, "w", encoding="utf-8", newline="\n") as fh:
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
    # 1.6.x 线一个 jar 覆盖 26.1 / 26.1.1 / 26.1.2，产物名里的游戏版本写成 26.1.x
    out = os.path.join(DIST, "meteor-zh-%s-mc26.1.x.jar" % VERSION)
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


# 产物里必须存在的东西。少一条就说明资源复制或编译某一步静默失败了 ——
# 之前正是靠肉眼发现这类问题的，现在让构建自己失败。
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


def validate_jar(path):
    """打包后自检：条目齐全、JSON 可解析、版本与依赖正确、class 版本是 Java 25。

    具体规则在 _jarcheck 里，两条构建线共用 —— 以前这里只查「条目 + class major」，
    depends / compatibilityLevel 漂了也不会失败（issue #1 的 P2-2）。
    """
    validate(path, version=VERSION, minecraft_dep=DEPS["minecraft_dep"],
             compatibility_level=DEPS["compatibility_level"], expect_major=69,
             required_entries=REQUIRED_ENTRIES)


def main():
    print("Meteor-ZH %s for Minecraft 26.1" % VERSION)
    compile_java()
    copy_resources()
    out = pack()
    validate_jar(out)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    print("\n%d entries:" % len(names))
    for n in sorted(names):
        print("  " + n)


if __name__ == "__main__":
    main()
