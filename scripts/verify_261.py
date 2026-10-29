# -*- coding: utf-8 -*-
"""在不启动游戏的前提下，用 Minecraft 26.1 的真实 classpath 验证插件能加载：

  1. 词典能从 jar 里读出来
  2. Translator.init() 里那 9 个反射字段在 26.1 的类里**全都存在**
     （这一步最关键——Meteor 改字段名的话，翻译会静默失效）
  3. 几个代表性查找有正确的中文结果

用法：
    python scripts/verify_261.py
"""
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_261 as b  # noqa: E402

ROOT = b.ROOT
TEST_SRC = os.path.join(ROOT, "scripts", "jvm-test", "Test261.java")
TEST_DIR = os.path.join(b.BUILD, "test-classes")
JAVA = os.path.join(b.JDK, "java.exe")
PLUGIN_JAR = os.path.join(b.DIST, "meteor-zh-%s-mc26.1.jar" % b.VERSION)


def _newest_source_mtime():
    newest = 0.0
    for base, _dirs, files in os.walk(os.path.join(ROOT, "src", "main")):
        for f in files:
            newest = max(newest, os.path.getmtime(os.path.join(base, f)))
    return newest


def ensure_fresh():
    """jar 比源码旧就自动重建一次。

    老版本只判断「jar 存在」，改了 Java 却忘了重新构建时，验证跑的是旧 jar，
    照样打印 ALL OK —— 这正是「假绿」的来源之一。
    """
    if os.path.exists(PLUGIN_JAR) and os.path.getmtime(PLUGIN_JAR) >= _newest_source_mtime():
        return
    print("源码比 jar 新（或 jar 不存在），先重建 26.1 产物 ...\n")
    import build_261
    build_261.main()
    print()


def main():
    ensure_fresh()
    if not os.path.exists(PLUGIN_JAR):
        raise SystemExit("先跑 scripts/build_261.py 生成 " + PLUGIN_JAR)
    if os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)

    cp_libs = b.classpath()
    env = os.environ.copy()
    env["JAVA_HOME"] = os.path.dirname(b.JDK).rstrip(os.sep)
    env["CLASSPATH"] = PLUGIN_JAR + os.pathsep + cp_libs

    print("编译测试类 ...")
    r = subprocess.run([b.JAVAC, "-encoding", "UTF-8", "-nowarn", "-d", TEST_DIR, TEST_SRC],
                       capture_output=True, env=env, cwd=ROOT)
    if r.returncode != 0:
        print((r.stdout + r.stderr).decode("utf-8", "replace"))
        raise SystemExit("测试类编译失败")

    env["CLASSPATH"] = TEST_DIR + os.pathsep + PLUGIN_JAR + os.pathsep + cp_libs
    print("运行 ...\n")
    r = subprocess.run([JAVA, "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8",
                        "Test261"], capture_output=True, env=env, cwd=ROOT)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    print(out)
    if err.strip():
        print("--- stderr ---")
        print(err[-3000:])
    print("exit:", r.returncode)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
