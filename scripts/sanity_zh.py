# -*- coding: utf-8 -*-
"""检查词典膨胀后有没有引入垃圾条目（保守过滤，只删明显错的）。"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "dict")
ZH = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "zh.json")

# 只匹配真正的"未翻译"哨兵。**不要**把「占位」「placeholder」「None」加进来：
# 「占位符」是正常术语（placeholder-color = 占位符文本的颜色），加进来会把合法词条删掉。
BAD_MARK = re.compile(r"暂未翻译|TODO|待翻译|未翻译")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, o):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(o, f, ensure_ascii=False, indent=1, sort_keys=True)


def main():
    zh = load(ZH)
    mods = zh.get("modules", {})
    sets = zh.get("settings", {})
    descs = zh.get("descriptions", {})

    # 1. 值里带「未翻译」之类占位语的
    garbage = 0
    for bucket in (mods, sets):
        for k, v in list(bucket.items()):
            t = v.get("title", "")
            if BAD_MARK.search(t):
                del bucket[k]
                garbage += 1
    for k, v in list(descs.items()):
        if BAD_MARK.search(v):
            del descs[k]
            garbage += 1
    print("removed placeholder entries:", garbage)

    # 2. 值其实还是英文原句（跟 key 一模一样，或完全没中文）—— 这些没意义
    same = 0
    for k, v in list(descs.items()):
        if v.strip() == k.strip():
            del descs[k]
            same += 1
    print("removed untranslated descs:", same)

    # 3. 模块表里没有任何中文的值（纯拉丁），说明来源是英文原样
    latin = 0
    for k, v in list(mods.items()):
        t = v.get("title", "")
        if t and not re.search(r"[\u4e00-\u9fff]", t):
            del mods[k]
            latin += 1
    print("removed non-chinese module titles:", latin)

    dump(ZH, zh)
    print("modules  :", len(mods))
    print("settings :", len(sets))
    print("descs    :", len(descs))


if __name__ == "__main__":
    main()
