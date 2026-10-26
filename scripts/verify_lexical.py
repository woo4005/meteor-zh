# -*- coding: utf-8 -*-
"""在纯 JVM 里验证词法兜底翻译（不启动 Minecraft）。"""
import io
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAR = os.path.join(ROOT, "dist", "meteor-zh-1.3.0.jar")
JAVA = r"C:\Users\wang'xiao'ya\AppData\Roaming\.minecraft\runtime\java-runtime-delta\bin\java.exe"
JAVAC = r"C:\Users\wang'xiao'ya\AppData\Roaming\.minecraft\runtime\java-runtime-delta\bin\javac.exe"
ARGS_FILE = os.path.join(os.path.dirname(ROOT), "miku-villager-mover", "build-offline", "javac.args")
TEST_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "zh_test")


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
        TEST_DIR, JAR,
        os.path.join(offline, "meteor-mojmap.jar"),
        os.path.join(offline, "client-mojmap.jar"),
        os.path.join(offline, "orbit.jar"),
        read_classpath(),
    ])

    src = os.path.join(TEST_DIR, "TestLex.java")
    c = subprocess.run([JAVAC, "-encoding", "UTF-8", "--release", "21", "-d", TEST_DIR, src],
                       capture_output=True, env=dict(os.environ, CLASSPATH=cp))
    if c.returncode != 0:
        print("javac failed:\n" + c.stderr.decode("utf-8", errors="replace")[:2000])
        return 1

    p = subprocess.run([JAVA, "-Dfile.encoding=UTF-8", "-cp", cp, "TestLex"],
                       capture_output=True, cwd=TEST_DIR)
    print("exit: %d" % p.returncode)
    print(p.stdout.decode("utf-8", errors="replace"))
    err = p.stderr.decode("utf-8", errors="replace")
    if err.strip():
        print("--- stderr ---\n" + err[:2000])
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
