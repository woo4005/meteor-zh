# -*- coding: utf-8 -*-
"""把 words.json 里「没有来源」的孤儿词并回 dict/zh_external_words.json。

背景：`src/main/resources/assets/meteorzh/lang/words.json` 是构建产物，由
`build_words.py`（字面量 W）+ `dict/zh_external_words.json`（外部词典词根）合并而成。
历史上有一批词是直接手改 words.json 加进去的，没有回写到任何来源文件，
于是「重建 words.json」会把它们悄悄丢掉 —— 产物不可复现。

这个脚本做一次性对账：找出产物里有、但两个来源都没有的词，追加进
`dict/zh_external_words.json`，让「来源 → 产物」重新闭合。可以反复运行，幂等。

用法：
    python scripts/absorb_orphan_words.py            # 只报告
    python scripts/absorb_orphan_words.py --write    # 写回 zh_external_words.json
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS_JSON = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "words.json")
EXTERNAL_JSON = os.path.join(ROOT, "dict", "zh_external_words.json")


def load(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def literal_words():
    """从 build_words.py 里取出 W 字面量的键。

    直接 import 会执行脚本主体（会写文件），所以这里用 ast 解析，只取 W 的键。
    """
    import ast

    src_path = os.path.join(ROOT, "scripts", "build_words.py")
    with io.open(src_path, "r", encoding="utf-8-sig") as f:
        tree = ast.parse(f.read())

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "W":
                if isinstance(node.value, ast.Dict):
                    keys = []
                    for k in node.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.append(k.value)
                    return keys
    raise SystemExit("在 build_words.py 里没找到 W = {...} 字面量")


def main():
    write = "--write" in sys.argv
    produced = load(WORDS_JSON)
    external = load(EXTERNAL_JSON)
    literal = set(literal_words())

    orphans = {
        k: v for k, v in produced.items()
        if k not in literal and k not in external
    }

    print("words.json      : %d" % len(produced))
    print("W 字面量         : %d" % len(literal))
    print("zh_external_words: %d" % len(external))
    print("孤儿词           : %d" % len(orphans))

    if not orphans:
        print("\n来源与产物已闭合，无需处理。")
        return 0

    sample = sorted(orphans.items())[:15]
    print("\n样例: " + ", ".join("%s=%s" % (k, v) for k, v in sample))

    if not write:
        print("\n（加 --write 写回 dict/zh_external_words.json）")
        return 0

    merged = dict(external)
    for k, v in orphans.items():
        merged.setdefault(k, v)
    with io.open(EXTERNAL_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print("\n已写回 %s：%d -> %d 条" % (EXTERNAL_JSON, len(external), len(merged)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
