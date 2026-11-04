# -*- coding: utf-8 -*-
"""把 Lotus / Jefff 官方中文语言文件转换成插件词典的一个数据源。

输入（官方汉化文件，由插件作者维护）:
    ~/OneDrive/桌面/Lotus-i18n-jefff-cn.properties
        jefffmod_<module>            模块名
        jefffmod_<module>_d          模块描述
        jefffmod_<module>_<setting>  设置名
        jefffmod_<module>_<setting>_d 设置描述
        Jefff\\ Mod-<hud>_<setting>    HUD 元素的设置
        Jefff\\ Mod-<hud>_<setting>_d
输出:
    dict/zh_lotus.json
        {"modules": {"<name>": {"title": ..., "desc": ...}},
         "settings": {"<name>": {"title": ..., "desc": ...}},
         "force": ["<setting-name>", ...]}

模块名有两套写法：五个是 CamelCase（AFKVanillaFly / ElytraFlyPlusPlus /
Pitch40Util / VanityESP / TrailFollower），其余是 kebab（auto-exp-plus ...）。
properties 的键没有类型标记，所以切分规则是「先去掉末尾的 _d 描述标记，再按
第一个 _ 切成 模块_设置」—— 模块名里不含下划线，设置名里不含下划线，这个
规则对两种写法都成立。

`force` 里的名字表示「官方译法比我们现有的更好，构建词典时直接覆盖」。
反向的情况（官方那个键根本没翻译，仍是英文）不放进 force，保留我们的译法。
"""
from __future__ import unicode_literals

import io
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "dict")

SOURCE = os.path.join(
    os.path.expanduser("~"), "OneDrive", "\u684c\u9762",
    "Lotus-i18n-jefff-cn.properties",
)

OUT = os.path.join(DICT, "zh_lotus.json")

# 官方译法更好、要覆盖我们现有译法的设置名。
# 只列「官方给了真中文」的；官方留英文的（mode / shape-mode /
# notification-mode）以及含义在本项目里不同的（ping -> 延迟）都不覆盖。
FORCE = [
    "item-frames",
    "exp-slot",
    "blocks-per-tick",
    "minimum-storage-count",
    "storage-blocks",
]


def read_properties(path):
    """返回 [(key, value)]，已剥掉 BOM / 注释 / 空行。"""
    with io.open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8-sig")
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out.append((key.strip(), value.strip()))
    return out


def is_chinese(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def parse(entries):
    modules = {}
    settings = {}

    for key, value in entries:
        if key.startswith("Jefff\\ Mod-"):
            # HUD 元素的键形如 `Jefff\ Mod-EntityList_scale`：`EntityList` 是 HUD
            # 的 name，后面才是它自己的设置。这里只收设置（color / gradient /
            # scale 这些通用名），HUD 的显示名交给词法兜底（EntityList ->
            # 实体 + 列表），不要拿最后一个设置名去当标题。
            body = key[len("Jefff\\ Mod-"):]
            desc = body.endswith("_d")
            if desc:
                body = body[:-2]
            _, _, setting = body.partition("_")
            if not setting or not value:
                continue
            entry = settings.setdefault(setting, {})
            if desc:
                entry.setdefault("desc", value)
            else:
                entry.setdefault("title", value)
            continue

        if not key.startswith("jefffmod_"):
            continue

        body = key[len("jefffmod_"):]
        desc = body.endswith("_d")
        if desc:
            body = body[:-2]

        module, _, setting = body.partition("_")
        if not module or not value:
            continue

        if not setting:
            entry = modules.setdefault(module, {})
            if desc:
                entry["desc"] = value
            else:
                entry["title"] = value
        else:
            entry = settings.setdefault(setting, {})
            if desc:
                entry.setdefault("desc", value)
            else:
                entry.setdefault("title", value)

    return modules, settings


def main():
    if not os.path.exists(SOURCE):
        raise SystemExit("找不到官方汉化文件: %s" % SOURCE)

    entries = read_properties(SOURCE)
    modules, settings = parse(entries)

    result = {
        "modules": dict(sorted(modules.items())),
        "settings": dict(sorted(settings.items())),
        "force": [n for n in FORCE if n in settings],
    }

    os.makedirs(DICT, exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")

    print("source   : %s (%d entries)" % (SOURCE, len(entries)))
    print("modules  : %d (with desc %d)" % (
        len(result["modules"]),
        sum(1 for v in result["modules"].values() if "desc" in v)))
    print("settings : %d (with desc %d)" % (
        len(result["settings"]),
        sum(1 for v in result["settings"].values() if "desc" in v)))
    print("force    : %d %s" % (len(result["force"]), result["force"]))
    missing = [n for n in FORCE if n not in settings]
    if missing:
        print("WARNING: force 里的名字在官方文件里没找到: %s" % missing)
    print("written  : %s (%d bytes)" % (OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
