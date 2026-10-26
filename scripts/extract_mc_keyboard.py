# -*- coding: utf-8 -*-
"""Extract Minecraft's official keyboard key names from the vanilla asset index.

Minecraft ships `assets/minecraft/lang/en_us.json` and `zh_cn.json` with a
`key.keyboard.*` entry per GLFW key. Pairing the two files gives us the official
localised name of every key, which is exactly what Meteor renders next to
"Bind: ".
"""
import io
import json
import os
import sys

BASE = r"E:\pcl\.minecraft"
INDEX_ID = "29"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dict", "mc_keyboard.json")


def load_obj(index, rel):
    entry = (index.get("objects") or {}).get(rel)
    if not entry:
        return None
    h = entry["hash"]
    path = os.path.join(BASE, "assets", "objects", h[:2], h)
    if not os.path.exists(path):
        print("missing object: %s" % path)
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    idx_path = os.path.join(BASE, "assets", "indexes", INDEX_ID + ".json")
    with io.open(idx_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    en = load_obj(index, "minecraft/lang/en_us.json")
    zh = load_obj(index, "minecraft/lang/zh_cn.json")
    if not en or not zh:
        sys.exit("could not load vanilla language files")

    mapping = {}
    for key, en_name in en.items():
        if not key.startswith("key.keyboard."):
            continue
        zh_name = zh.get(key)
        if not zh_name or zh_name == en_name:
            continue
        mapping[en_name] = zh_name

    # Meteor renders unbound keys as "None".
    mapping.setdefault("None", "无")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(mapping.items())), f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("vanilla lang entries : en=%d zh=%d" % (len(en), len(zh)))
    print("keyboard names mapped: %d" % len(mapping))
    print("written              : %s" % OUT)
    for probe in ("Left Shift", "Space", "Enter", "Escape", "F1", "Left Mouse", "None"):
        print("  %-12s -> %s" % (probe, mapping.get(probe)))


if __name__ == "__main__":
    main()
