# -*- coding: utf-8 -*-
"""验证词法兜底引擎（WordTranslator）的合成结果（不启动 Minecraft）。

喂一批词典里没有的标识符，看能否逐词合成出可读中文；再喂已经是中文的名字，
确认返回 null —— 这是「不会把 Miku/Lotus 的中文模块名拉丁化」的关键设计。

用法:
    python scripts/verify_lexical.py
"""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _verify_env import build_classpath, find_java, find_javac  # noqa: E402

TEST_SRC_DIR = os.path.join(HERE, "jvm-test")
TEST_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "meteor-zh-jvm-test")
MAIN_CLASS = "TestLex"


def decode(raw):
    """JVM 在 Windows 上的输出可能是 UTF-8，也可能退回系统代码页，逐个试。"""
    for enc in ("utf-8", "gbk", "cp936"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def main():
    os.makedirs(TEST_DIR, exist_ok=True)
    cp = build_classpath(TEST_DIR, "1.21.11")
    javac = find_javac()
    java = find_java()

    src = os.path.join(TEST_SRC_DIR, MAIN_CLASS + ".java")
    compile_proc = subprocess.run(
        [javac, "-encoding", "UTF-8", "--release", "21", "-d", TEST_DIR, "-cp", cp, src],
        capture_output=True,
    )
    if compile_proc.returncode != 0:
        print("javac failed:\n" + decode(compile_proc.stderr)[:3000])
        return 1

    proc = subprocess.run(
        [java, "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8",
         "-Dstderr.encoding=UTF-8", "-cp", cp, MAIN_CLASS],
        capture_output=True,
        cwd=TEST_DIR,
    )
    print("exit: %d" % proc.returncode)
    print(decode(proc.stdout))
    err = decode(proc.stderr)
    if err.strip():
        print("--- stderr ---\n" + err[:3000])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
