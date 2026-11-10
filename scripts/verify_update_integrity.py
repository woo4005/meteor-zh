# -*- coding: utf-8 -*-
"""离线验证更新器的完整性校验（TestUpdateIntegrity），不启动 Minecraft、不联网。

验证点（对应桌面草稿的验收清单前四条）：
  1. sha256 计算结果与标准向量一致；
  2. asset 的 digest 解析（剥 sha256: 前缀、转小写、缺字段返回 null）；
  3. 下载域名白名单是「精确匹配或子域名」，不能被 github.com.evil.example 骗过；
  4. 资产名的版本表达式匹配（.x / 区间 / 精确）。

用法:
    python scripts/verify_update_integrity.py
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
MAIN_CLASS = "TestUpdateIntegrity"


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
