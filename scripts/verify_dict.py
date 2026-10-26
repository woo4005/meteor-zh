# -*- coding: utf-8 -*-
"""Run the packaged jar's dictionary in a plain JVM and print the lookups.

This validates, without starting Minecraft: the resource is inside the jar, Gson
parses it, and the lookup fallbacks behave as designed.
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAR = os.path.join(ROOT, "dist", "meteor-zh-1.3.0.jar")
JAVA = r"C:\Users\wang'xiao'ya\AppData\Roaming\.minecraft\runtime\java-runtime-delta\bin\java.exe"
ARGS_FILE = os.path.join(os.path.dirname(ROOT), "miku-villager-mover", "build-offline", "javac.args")

TEST_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "zh_test")
TEST_CLASSES = TEST_DIR


def read_classpath():
    with io.open(ARGS_FILE, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    for i, line in enumerate(lines):
        if line.strip() == "-cp" and i + 1 < len(lines):
            return lines[i + 1].strip().strip('"')
        if line.startswith("-cp "):
            return line[4:].strip().strip('"')
    raise SystemExit("no -cp entry in javac.args")


def main():
    offline = os.path.dirname(ARGS_FILE)
    cp = ";".join([
        TEST_CLASSES,
        JAR,
        os.path.join(offline, "meteor-mojmap.jar"),
        os.path.join(offline, "client-mojmap.jar"),
        os.path.join(offline, "orbit.jar"),
        read_classpath(),
    ])
    proc = subprocess.run([JAVA, "-Dfile.encoding=UTF-8", "-cp", cp, "TestZh"],
                          capture_output=True, cwd=TEST_DIR)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    print("exit: %d" % proc.returncode)
    print("--- stdout ---")
    print(out)
    if err.strip():
        print("--- stderr ---")
        print(err[:3000])


if __name__ == "__main__":
    main()
