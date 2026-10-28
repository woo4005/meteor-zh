# -*- coding: utf-8 -*-
"""把队友从其它 Meteor 汉化项目收集来的词条，**安全地**并入本项目的词典。

安全策略（宁可少收，不可乱译）：
  1. 模块名/设置名只补「Meteor 26.1 真实存在」的条目——用 extract_261.py 产出的
     raw_261.json 做白名单，避免收进别的版本/别的项目的垃圾键。
  2. key 先规范化（小写、空格与下划线转连字符）再比对。
  3. 已经有的中文绝不覆盖。
  4. 描述句按英文原文匹配，这类 key 是完整句子、不会误匹配，收益最大。
  5. 词表只收不含奇怪词的条目（纯字母，长度 2~40）。

输出：dict/zh_external_merged.json（build_dict.py 追加读这个文件）+ 统计打印。
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "dict")
ZH = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "zh.json")


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    """把 '1st line' / 'Anti Bot' / 'auto_accept' 统一成 kebab 小写。"""
    s = s.strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s


def plausible_word(w):
    return bool(re.fullmatch(r"[a-z][a-z0-9]{1,39}", w))


def main():
    zh = load(ZH)
    exist_mod = zh.get("modules", {})
    exist_set = zh.get("settings", {})
    exist_desc = zh.get("descriptions", {})
    exist_ui = zh.get("ui", {})
    exist_group = zh.get("groups", {})

    # 描述句：key 是英文原文整句，不会误匹配，全收（收益最大的一项）
    ext = load(os.path.join(DICT, "zh_external_entries.json"))
    added_desc = 0
    for en, cn in (ext.get("descriptions") or {}).items():
        if en and cn and en not in exist_desc and len(en) < 400:
            exist_desc[en] = cn
            added_desc += 1

    # 标识符：外部条目标题只有在「能对应上一条已知英文说明」时才收——
    # 这类条目有真实证据（我们手上有它的英文原文），不是凭空的键。
    # 新标识符的实际翻译在运行时由词法引擎完成，不需要词典里堆键。
    known_desc = set(exist_desc) | set((ext.get("descriptions") or {}))
    title_to_key = {}
    for bucket in (exist_mod, exist_set):
        for k, v in bucket.items():
            if v.get("desc") and v["desc"] in known_desc:
                title_to_key[v.get("title", "")] = k

    added_ident = 0
    for bucket_name, bucket in (("modules", exist_mod), ("settings", exist_set)):
        for name, val in (ext.get(bucket_name) or {}).items():
            key = norm(name)
            if key in exist_mod or key in exist_set:
                continue
            desc = (val or {}).get("desc")
            if desc and desc in known_desc:
                bucket[key] = {"title": (val or {}).get("title", ""), "desc": desc}
                added_ident += 1

    # 词表：不限白名单，但要求 ASCII 小写标识符 + 简短中文
    words = load(os.path.join(DICT, "zh_external_words.json"))
    wpath = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "words.json")
    cur = load(wpath)
    added_word = 0
    for en, cn in words.items():
        key = norm(en)
        if plausible_word(key) and key not in cur and cn and len(cn) <= 12:
            cur[key] = cn
            added_word += 1

    # 写进 build_dict.py 的输入：dict/zh_addons.json 的 names / descs
    #   names : kebab -> 中文（build_dict 会同时写 modules 与 settings 的 title，setdefault 不覆盖）
    #   descs : 英文原句 -> 中文（build_dict 写进 descriptions）
    apath = os.path.join(DICT, "zh_addons.json")
    addon = load(apath) if os.path.exists(apath) else {}
    names = addon.setdefault("names", {})
    dsc = addon.setdefault("descs", {})

    added_name = 0
    for key in list(exist_set) + list(exist_mod):
        title = (exist_set.get(key) or exist_mod.get(key) or {}).get("title")
        if title and key not in names:
            names[key] = title
            added_name += 1
    added_d = 0
    for en, cn in exist_desc.items():
        if en not in dsc:
            dsc[en] = cn
            added_d += 1

    with io.open(apath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(addon, f, ensure_ascii=False, indent=1, sort_keys=True)
    with io.open(wpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1, sort_keys=True)

    print("identifiers +%d (modules %d / settings %d)"
          % (added_ident, len(exist_mod), len(exist_set)))
    print("descs    +%d (now %d)" % (added_desc, len(exist_desc)))
    print("zh_addons.json: names +%d (now %d), descs +%d (now %d)"
          % (added_name, len(names), added_d, len(dsc)))
    print("words    +%d (now %d)" % (added_word, len(cur)))
    print("wrote", apath)


if __name__ == "__main__":
    main()
