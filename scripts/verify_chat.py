# -*- coding: utf-8 -*-
"""离线验证聊天模板反查引擎（TestChat），不启动 Minecraft。

验证点：
  1. chat.json 确实打进了 jar、能被 Gson 读出来；
  2. 「已填好参数」的英文消息能被模板反查翻成中文（正则捕获组顺序正确）；
  3. 中文消息 / 未收录消息 / 超长调试串一律原样放过。

用法:
    python scripts/verify_chat.py
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
MAIN_CLASS = "TestChat"


def decode(raw):
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
    proc = subprocess.run(
        [javac, "-encoding", "UTF-8", "--release", "21", "-d", TEST_DIR, "-cp", cp, src],
        capture_output=True,
    )
    if proc.returncode != 0:
        print("javac failed:\n" + decode(proc.stderr)[:3000])
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
        print("--- stderr ---")
        print(err[:3000])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
