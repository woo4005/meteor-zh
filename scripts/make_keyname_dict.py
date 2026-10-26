# -*- coding: utf-8 -*-
"""Attach Chinese names to the key / mouse button labels Meteor renders.

`Utils.getKeyName` returns English literals; they are drawn by the same
GuiRenderer.text path as everything else, so they belong in the `ui` table.
Names follow Minecraft's own Chinese convention (Ctrl/Shift/Alt keep their Latin
names, arrows use arrow glyphs) instead of a literal translation.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "dict")
SRC = os.path.join(DICT, "raw_keynames.json")
OUT = os.path.join(DICT, "zh_keynames.json")

# function keys and a few names that read better left alone
IDENTITY = ["Esc", "Home", "End", "Tab"]
for i in range(1, 26):
    IDENTITY.append("F%d" % i)

MAP = {
    "None": "无",
    "Items": "物品",
    "Slot": "槽位",
    "Unknown": "未知",
    "Grave Accent": "反引号",
    "World 1": "世界1",
    "World 2": "世界2",
    "Print Screen": "屏幕截图",
    "Pause": "暂停",
    "Insert": "插入",
    "Delete": "删除",
    "Page Up": "上一页",
    "Page Down": "下一页",
    "Left Control": "左Ctrl",
    "Right Control": "右Ctrl",
    "Left Alt": "左Alt",
    "Right Alt": "右Alt",
    "Left Shift": "左Shift",
    "Right Shift": "右Shift",
    "Arrow Up": "\u2191",
    "Arrow Down": "\u2193",
    "Arrow Left": "\u2190",
    "Arrow Right": "\u2192",
    "Apostrophe": "单引号",
    "Backspace": "退格",
    "Caps Lock": "大写锁定",
    "Menu": "菜单",
    "Left Super": "左Win",
    "Right Super": "右Win",
    "Enter": "回车",
    "Numpad Enter": "小键盘回车",
    "Num Lock": "数字锁定",
    "Scroll Lock": "滚动锁定",
    "Space": "空格",
    "Mouse Left": "鼠标左键",
    "Mouse Right": "鼠标右键",
    "Mouse Middle": "鼠标中键",
}


def main():
    with io.open(SRC, "r", encoding="utf-8") as f:
        raw = json.load(f)

    mapping = {}
    for name in raw.get("keys") or []:
        if name in MAP:
            mapping[name] = MAP[name]
        elif name in IDENTITY:
            mapping[name] = name
        else:
            print("unmapped key name: %s" % name)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(mapping.items())), f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("mapped  : %d of %d" % (len(mapping), len(raw.get("keys") or [])))
    print("written : %s" % OUT)


if __name__ == "__main__":
    main()
