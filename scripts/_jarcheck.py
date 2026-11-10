# -*- coding: utf-8 -*-
"""产物 jar 的构建期自检（两条构建线共用）。

存在的理由：发布出去的 jar 里，真正决定「装得上装不上」的只有几样东西 ——
版本号、depends（尤其是 meteor-client 的 semver 边界）、Mixin 的 compatibilityLevel、
class 的字节码版本。这些以前全靠肉眼看，而 P2-2（issue #1）指出的正是
「Gradle 产物与离线产物语义不一致、且 validate 不校验 depends」这类静默漂移。

调用方式：
    from _jarcheck import validate
    validate(jar_path, version="1.4.8", minecraft_dep="~1.21.11",
             compatibility_level="JAVA_21", expect_major=65,
             required_entries=(...))
失败直接 SystemExit，成功打印一行摘要。
"""
import json
import zipfile


def validate(path, version, minecraft_dep, compatibility_level, expect_major,
             required_entries=()):
    problems = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())

        for rel in required_entries:
            if rel not in names:
                problems.append("缺少条目 " + rel)

        mod = None
        mixins = None
        for rel in ("fabric.mod.json", "meteor-zh.mixins.json"):
            if rel not in names:
                problems.append("缺少条目 " + rel)
                continue
            try:
                data = json.loads(z.read(rel).decode("utf-8"))
            except Exception as exc:
                problems.append("%s 不是合法 JSON: %s" % (rel, exc))
                continue
            if rel == "fabric.mod.json":
                mod = data
            else:
                mixins = data

        if mod is not None:
            if mod.get("version") != version:
                problems.append("fabric.mod.json 的 version=%r，应为 %r"
                                % (mod.get("version"), version))
            depends = mod.get("depends") or {}
            for key in ("fabricloader", "minecraft", "java", "meteor-client"):
                if key not in depends:
                    problems.append("depends 缺少 %r（装错环境时会退化成静默无翻译）" % key)
            raw = json.dumps(depends, ensure_ascii=False)
            if "${" in raw:
                problems.append("depends 里有未展开的占位符: " + raw)
            if depends.get("minecraft") != minecraft_dep:
                problems.append("depends.minecraft=%r，应为 %r"
                                % (depends.get("minecraft"), minecraft_dep))

        if mixins is not None:
            if mixins.get("compatibilityLevel") != compatibility_level:
                problems.append("mixins compatibilityLevel=%r，应为 %r"
                                % (mixins.get("compatibilityLevel"), compatibility_level))

        classes = 0
        for name in names:
            if not name.endswith(".class"):
                continue
            head = z.read(name)[:8]
            if len(head) < 8 or head[:4] != b"\xca\xfe\xba\xbe":
                problems.append(name + " 不是 class 文件")
                continue
            major = int.from_bytes(head[6:8], "big")
            classes += 1
            if major != expect_major:
                problems.append("%s 的 class major=%d，应为 %d"
                                % (name, major, expect_major))

    if problems:
        for problem in problems:
            print("  [FAIL] " + problem)
        raise SystemExit("jar 校验失败：" + path)

    print("  validated: %d entries, %d classes @ major %d"
          % (len(names), classes, expect_major))
