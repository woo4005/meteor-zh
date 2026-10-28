# -*- coding: utf-8 -*-
"""把 Meteor 26.1 相对旧版新增/改名的词条补进 dict/zh_addons.json。

这些条目是 scripts/extract_261.py 扫 26.1.2 源码找出来的、现有词典没覆盖的部分：
4 个新模块 + 34 个设置名 + 38 条设置说明 + 4 条模块说明。

写进 zh_addons.json 是因为 build_dict.py 里 convert_addons() 会把
names 同时塞进 modules 和 settings 的 title（用 setdefault，不覆盖已有值），
descs 塞进 descriptions（英文原句 -> 中文）——正好是这里需要的形状。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "dict", "zh_addons.json")

NAMES = {
    # ---- 26.1 新增模块 ----
    "anti-anchor": "防锚光环",
    "excavator": "挖掘机",
    "infinity-miner": "无限矿工",
    "weather-changer": "天气修改器",
    # ---- 26.1 新增设置名 ----
    "active": "启用",
    "characters": "字符数",
    "description": "描述",
    "dimension": "维度",
    "end-line-color": "结束线颜色",
    "end-side-color": "结束面颜色",
    "file": "文件",
    "fluid-opacity": "流体不透明度",
    "fuel-items-per-refill": "每次补充燃料数",
    "keep-active": "保持激活",
    "layer": "层",
    "limit-render-range": "限制渲染范围",
    "log-out": "满背包退出",
    "log-selection": "记录选区",
    "mine-threshold": "挖掘阈值",
    "next-layer-keybind": "下一层按键",
    "pos-1": "角点 1",
    "pos-2": "角点 2",
    "prev-layer-keybind": "上一层按键",
    "rain-level": "雨量等级",
    "random-type": "随机类型",
    "render-range": "渲染范围",
    "repair-blocks": "修复方块",
    "repair-threshold": "修复阈值",
    "selection-bind": "选区按键",
    "start-line-color": "起始线颜色",
    "start-side-color": "起始面颜色",
    "sword-slash": "剑挥砍动画",
    "target-blocks": "目标方块",
    "target-items": "目标物品",
    "thunder-level": "雷声等级",
    "tracer": "追踪线",
    "use-display-name": "使用显示名",
    "walk-home": "自动回家",
}

DESCS = {
    # ---- 26.1 新增模块的说明 ----
    "Automatically prevents Anchor Aura by placing a slab on your head.":
        "自动在你头顶放置台阶，防止他人对你使用锚光环。",
    "Excavate a selection area.":
        "挖掘选定的区域。",
    "Allows you to essentially mine forever by mining repair blocks when the durability gets low. Needs a mending pickaxe.":
        "耐久度降低时自动挖掘修复方块，让你几乎可以一直挖下去。需要带经验修补的镐。",
    "Allows you to override the world's current weather.":
        "允许你覆盖世界当前的天气。",
    # ---- 设置说明 ----
    "Is this marker visible.": "该标记是否可见。",
    "How many characters to write per page.": "每页写入多少个字符。",
    "Custom description for this marker.": "该标记的自定义描述。",
    "In which dimension this marker should be visible.": "该标记应在哪个维度可见。",
    "The line color for the fully-broken block.": "完全破坏方块的线条颜色。",
    "The side color for the fully-broken block.": "完全破坏方块的侧面颜色。",
    "Which file to use.": "使用哪个文件。",
    "Which fluids should use xray opacity.": "哪些流体使用透视不透明度。",
    "How many fuel items to put into the furnace each time it refills": "每次补充燃料时放入熔炉的燃料数量。",
    "Keep the module active after finishing the excavation.": "挖掘完成后保持模块激活。",
    "Which layer to render": "渲染哪一层。",
    "Whether to limit rendering range (useful in very large circles)": "是否限制渲染范围（超大圆形时有用）。",
    "Logs out when your inventory is full. Will walk home FIRST if walk home is enabled.":
        "物品栏满时退出服务器。若启用了自动回家，会先走回家再退出。",
    "Logs the selection coordinates to the chat.": "把选区坐标输出到聊天栏。",
    "The durability percentage at which to start mining.": "开始挖掘时的耐久度百分比。",
    "Keybind to increment layer": "增加层数的按键。",
    "1st corner of the cuboid": "长方体的第 1 个角。",
    "2nd corner of the cuboid": "长方体的第 2 个角。",
    "The specified rain level to be set.": "要设置的雨量等级。",
    "What kind of random to use.": "使用哪种随机方式。",
    "Rendering range": "渲染范围。",
    "The repair blocks to mine.": "要挖掘的修复方块。",
    "The durability percentage at which to start repairing.": "开始修复时的耐久度百分比。",
    "Bind to draw selection.": "绘制选区的按键。",
    "The line color for the non-broken block.": "未破坏方块的线条颜色。",
    "The side color for the non-broken block.": "未破坏方块的侧面颜色。",
    "Replaces the sword swing animation with the offhand idle animation.":
        "用副手待机动画替换挥剑动画。",
    "The target blocks to mine.": "要挖掘的目标方块。",
    "The target items to collect.": "要收集的目标物品。",
    "The specified thunder level to be set.": "要设置的雷声等级。",
    "If tracer line is allowed to this block.": "该方块是否允许显示追踪线。",
    "Uses the players server display name instead of their account name.":
        "使用玩家的服务器显示名而不是账号名。",
    "Will walk 'home' when your inventory is full.": "物品栏满时自动走回家。",
    "Binds camera distance scrolling to a key.": "把相机距离滚轮绑定到按键。",
    "The tick delay between placing anchors.": "放置重生锚之间的 tick 延迟。",
    "The position of your main hand.": "主手的显示位置。",
    "Players scale.": "玩家缩放比例。",
}


def main():
    with open(PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    names = data.setdefault("names", {})
    descs = data.setdefault("descs", {})

    added_n = added_d = 0
    for k, v in NAMES.items():
        if k not in names:
            names[k] = v
            added_n += 1
    for k, v in DESCS.items():
        if k not in descs:
            descs[k] = v
            added_d += 1

    with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")

    print("新增 names %d / descs %d" % (added_n, added_d))
    print("现在 names %d / descs %d" % (len(names), len(descs)))
    print("-> %s" % PATH)


if __name__ == "__main__":
    main()
