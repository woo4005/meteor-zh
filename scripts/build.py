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
VERSION = "1.4.0"


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


def compile_java():
    if os.path.isdir(CLASSES):
        shutil.rmtree(CLASSES)
    os.makedirs(CLASSES)

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


def copy_resources():
    """Copy resources into the class output dir.

    ``fabric.mod.json`` declares ``"version": "${version}"`` so that the Gradle build can
    expand it through processResources. This offline build has no Gradle, so substitute the
    same placeholder here — the two build paths then produce identical metadata.
    """
    res = os.path.join(ROOT, "src", "main", "resources")
    for base, _, files in os.walk(res):
        for name in files:
            src = os.path.join(base, name)
            rel = os.path.relpath(src, res)
            dst = os.path.join(CLASSES, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if name == "fabric.mod.json":
                with io.open(src, "r", encoding="utf-8") as f:
                    text = f.read().replace("${version}", VERSION)
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
    if not os.path.exists(os.path.join(tool_classes, "RemapJar.class")):
        if os.path.isdir(tool_classes):
            shutil.rmtree(tool_classes)
        os.makedirs(tool_classes)
        env = dict(os.environ)
        env["CLASSPATH"] = read_classpath()  # provides the ASM jars RemapJar needs
        run([JAVAC, "-encoding", "UTF-8", "-d", tool_classes, remap_tool], env=env)

    run([JAVA, "-cp", tool_classes + ";" + read_classpath(), "RemapJar",
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

    final = os.path.join(DIST, "%s-%s.jar" % (MOD_ID, VERSION))
    shutil.copy2(inter_jar, final)
    print("output: %s (%d bytes)" % (final, os.path.getsize(final)))


if __name__ == "__main__":
    main()
