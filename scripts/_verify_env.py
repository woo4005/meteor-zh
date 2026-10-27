# -*- coding: utf-8 -*-
"""verify_*.py 共用的运行环境探测。

这些校验脚本要在一个普通 JVM 里加载打包好的 jar（不启动 Minecraft），
因此需要三样东西：一个 java 可执行文件、一个 meteor-zh jar、一份包含
Minecraft + Meteor 的 classpath。

早期版本把三样都写死成维护者本机的绝对路径，外部贡献者和 CI 无法使用。
现在统一改成「环境变量覆盖 → 常见位置自动探测 → 打印可操作的报错」：
直接跑通时不需要任何配置，跑不通时提示要设置哪个变量。

可用的环境变量（都可选）：
    JAVA                     java 可执行文件路径
    METEOR_ZH_JAR            meteor-zh 的 jar 路径
    MC_CLASSPATH_FILE        含 Minecraft + Meteor 的 classpath 清单文件
    MC_CLASSPATH             直接给出 classpath（分号或冒号分隔）
    METEOR_CLASS_DIR         放有 meteor-mojmap.jar / client-mojmap.jar / orbit.jar 的目录
"""
import glob
import io
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 离线构建默认使用的 classpath 清单（维护者本机约定，见 README「从源码构建」）
DEFAULT_ARGS_FILE = os.path.join(
    os.path.dirname(ROOT), "miku-villager-mover", "build-offline", "javac.args"
)
#: 离线构建默认的依赖 jar 目录
DEFAULT_METEOR_DIR = os.path.dirname(DEFAULT_ARGS_FILE)

_OFFLINE_JARS = ("meteor-mojmap.jar", "client-mojmap.jar", "orbit.jar")


def _fail(message):
    raise SystemExit(
        message
        + "\n\n提示: 这些校验脚本需要 java + meteor-zh jar + Minecraft/Meteor 的 classpath。\n"
        "      Gradle 构建后可以用 build/libs 下的 jar，并把 MC/Meteor 的 jar 或\n"
        "      classpath 清单通过环境变量 METEOR_ZH_JAR / MC_CLASSPATH(_FILE) 指过来。"
    )


def find_jar():
    """返回要校验的 meteor-zh jar 路径。"""
    env = os.environ.get("METEOR_ZH_JAR")
    if env:
        if not os.path.isfile(env):
            _fail("METEOR_ZH_JAR 指向的文件不存在: %s" % env)
        return os.path.abspath(env)

    dist = os.path.join(ROOT, "dist")
    candidates = [
        p for p in glob.glob(os.path.join(dist, "meteor-zh-*.jar"))
        if not p.endswith(("-dev.jar", "-sources.jar"))
    ]
    if not candidates:
        # Gradle 会把产物放在 build/libs 下，也一并找一下
        candidates = [
            p for p in glob.glob(os.path.join(ROOT, "build", "libs", "meteor-zh-*.jar"))
            if not p.endswith(("-dev.jar", "-sources.jar"))
        ]
    if not candidates:
        _fail("在 dist/ 和 build/libs/ 下都没找到 meteor-zh-*.jar，请先构建（见 README）。")
    # 文件名里带版本号，按修改时间取最新即可
    return os.path.abspath(max(candidates, key=os.path.getmtime))


def _launcher_runtimes():
    """启动器自带运行时（PCL / 官方启动器）里的 java 可执行文件候选，优先带 javac 的。

    维护者本机没有把 java 加进 PATH，这里兜底探测：.minecraft/runtime/<name>/bin/java.exe。
    同一台机器上可能同时存在 JRE 8（jre-legacy，没有 javac）和 JDK 21/25，
    所以把「同目录下有 javac」的候选排在前面，否则会挑到没有编译器的那个。
    """
    exe = "java.exe" if os.name == "nt" else "java"
    found = []
    for base in filter(None, [os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA"),
                              os.environ.get("USERPROFILE")]):
        for pattern in (
            os.path.join(base, ".minecraft", "runtime", "*", "bin", exe),
            os.path.join(base, "AppData", "Roaming", ".minecraft", "runtime", "*", "bin", exe),
        ):
            found.extend(glob.glob(pattern))

    unique, seen = [], set()
    for p in found:
        key = os.path.abspath(p)
        if key not in seen:
            seen.add(key)
            unique.append(key)

    def score(p):
        bindir = os.path.dirname(p)
        has_javac = any(os.path.isfile(os.path.join(bindir, n)) for n in ("javac", "javac.exe"))
        return (0 if has_javac else 1, p)

    return sorted(unique, key=score)


def find_java():
    """返回 java 可执行文件路径。"""
    env = os.environ.get("JAVA")
    if env:
        if not os.path.isfile(env):
            _fail("JAVA 指向的文件不存在: %s" % env)
        return env

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        for name in ("java", "java.exe"):
            p = os.path.join(java_home, "bin", name)
            if os.path.isfile(p):
                return p

    found = shutil.which("java")
    if found:
        return found

    runtimes = _launcher_runtimes()
    if runtimes:
        return runtimes[0]

    _fail("找不到 java，请设置 JAVA_HOME 或 JAVA 环境变量（需要 JDK/JRE 21 及以上）。")


def find_javac():
    """返回 javac 可执行文件路径（只有 verify_lexical.py / verify_dict.py 需要）。"""
    java = find_java()
    bindir = os.path.dirname(java)
    for name in ("javac", "javac.exe"):
        p = os.path.join(bindir, name)
        if os.path.isfile(p):
            return p
    # java 可能来自 JRE，换一个同机的 JDK 运行时
    for candidate in _launcher_runtimes():
        b = os.path.dirname(candidate)
        for name in ("javac", "javac.exe"):
            p = os.path.join(b, name)
            if os.path.isfile(p):
                return p
    _fail("找不到 javac（校验脚本需要先编译一个测试类），请指向一个完整 JDK 的 bin 目录。")


def _read_args_classpath(args_file):
    with io.open(args_file, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    for i, line in enumerate(lines):
        if line.strip() == "-cp" and i + 1 < len(lines):
            return lines[i + 1].strip().strip('"')
        if line.startswith("-cp "):
            return line[4:].strip().strip('"')
    return None


def find_classpath():
    """返回 Minecraft + Meteor 的 classpath 字符串（不含 jar 与测试类目录）。"""
    direct = os.environ.get("MC_CLASSPATH")
    if direct:
        return direct

    args_file = os.environ.get("MC_CLASSPATH_FILE") or DEFAULT_ARGS_FILE
    if not os.path.isfile(args_file):
        _fail("找不到 classpath 清单: %s" % args_file)

    cp = _read_args_classpath(args_file)
    if not cp:
        _fail("清单 %s 里没有 -cp 条目。" % args_file)

    # 离线清单里不包含这三个 jar，需要额外拼上（顺序见 verify 脚本的历史注释）
    meteor_dir = os.environ.get("METEOR_CLASS_DIR") or os.path.dirname(args_file)
    extra = [os.path.join(meteor_dir, n) for n in _OFFLINE_JARS
             if os.path.isfile(os.path.join(meteor_dir, n))]
    if not extra:
        return cp
    sep = ";" if os.name == "nt" else ":"
    return sep.join(extra + [cp])


def build_classpath(test_dir):
    """拼出最终的 classpath：测试类目录 + meteor-zh jar + MC/Meteor 依赖。"""
    sep = ";" if os.name == "nt" else ":"
    parts = [test_dir, find_jar(), find_classpath()]
    return sep.join(parts)
