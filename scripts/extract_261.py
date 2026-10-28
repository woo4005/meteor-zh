# -*- coding: utf-8 -*-
"""从 Meteor 26.1.2 的 sources jar 里提取全部模块名 / 设置名 / 分组名 / 描述，
用于和现有词典比对、找出 26.1 新增或改名的条目。

产物：dict/raw_261.json
    {"modules": {"<name>": "<description>"},
     "settings": {"<name>": "<description>"},
     "groups": ["<name>", ...]}
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build-261", "src-ref", "meteordevelopment", "meteorclient", "systems", "modules")
OUT = os.path.join(ROOT, "dict", "raw_261.json")

RE_SUPER = re.compile(r'super\(\s*Categories\.\w+\s*,\s*"([^"]+)"\s*,\s*"((?:[^"\\]|\\.)*)"', re.S)
RE_NAME = re.compile(r'\.name\(\s*"([^"]+)"\s*\)')
RE_DESC = re.compile(r'\.description\(\s*"((?:[^"\\]|\\.)*)"')
RE_GROUP = re.compile(r'createGroup\(\s*"([^"]+)"')


def unescape(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


def main():
    modules, settings, groups = {}, {}, set()
    files = 0
    for base, _dirs, names in os.walk(SRC):
        for fn in names:
            if not fn.endswith(".java"):
                continue
            files += 1
            path = os.path.join(base, fn)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()

            for m in RE_SUPER.finditer(text):
                modules[m.group(1)] = unescape(m.group(2))

            # .name("x") 和紧随其后的 .description("y") 配对：
            # meteor 的设置写法是 builder 链，description 总在 name 后面几行，
            # 中间不会插进第二个 .name()，所以按出现顺序配对即可。
            pending = None
            for m in re.finditer(r'\.name\(\s*"([^"]+)"\s*\)|\.description\(\s*"((?:[^"\\]|\\.)*)"',
                                 text):
                if m.group(1) is not None:
                    pending = m.group(1)
                elif pending is not None:
                    settings.setdefault(pending, unescape(m.group(2)))
                    pending = None

            for m in RE_GROUP.finditer(text):
                groups.add(m.group(1))

    data = {
        "modules": dict(sorted(modules.items())),
        "settings": dict(sorted(settings.items())),
        "groups": sorted(groups),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)

    print("扫描 %d 个文件" % files)
    print("模块 %d / 设置 %d / 分组 %d" % (len(modules), len(settings), len(groups)))
    print("-> %s" % OUT)


if __name__ == "__main__":
    main()
