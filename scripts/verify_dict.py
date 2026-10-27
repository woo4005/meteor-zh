# -*- coding: utf-8 -*-
"""在普通 JVM 里加载打包好的 jar 词典并打印若干查找结果（不启动 Minecraft）。

验证三件事：
  1. 词典资源确实被打进了 jar（assets/meteorzh/lang/zh.json）；
  2. Gson 能解析它，条目数与预期一致；
  3. 查找的回落顺序符合设计（模块表 → 设置表 → 描述表 → 原样返回）。

用法:
    python scripts/verify_dict.py

需要 java 与 Minecraft/Meteor 的 classpath，自动探测规则见 scripts/_verify_env.py；
探测不到时脚本会打印具体要设置哪个环境变量。
"""
import os
import subprocess
import sys

# Windows 控制台默认 GBK，词典内容全是中文，不改成 UTF-8 会 UnicodeEncodeError。
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _verify_env import build_classpath, find_java, find_javac  # noqa: E402

TEST_SRC_DIR = os.path.join(HERE, "jvm-test")
TEST_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "meteor-zh-jvm-test")
MAIN_CLASS = "TestZh"


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
    cp = build_classpath(TEST_DIR)
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
    print("--- stdout ---")
    print(decode(proc.stdout))
    err = decode(proc.stderr)
    if err.strip():
        print("--- stderr ---")
        print(err[:3000])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
