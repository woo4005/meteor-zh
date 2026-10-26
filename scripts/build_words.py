#!/usr/bin/env python3
"""构建 words.json（词法翻译词表）+ 用现有词典做回归评估。"""
import json, re, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 英文词元 -> 中文。用于对未收录词典的 addon 条目做逐词拼合翻译。
W = {
    # 动作/状态
    "enable": "启用", "disable": "禁用", "enabled": "启用", "disabled": "禁用",
    "auto": "自动", "automatic": "自动", "automaticly": "自动", "toggle": "切换",
    "switch": "切换", "show": "显示", "hide": "隐藏", "notify": "通知", "notify": "通知",
    "send": "发送", "open": "打开", "close": "关闭", "load": "加载", "save": "保存",
    "reset": "重置", "clear": "清除", "add": "添加", "remove": "移除", "delete": "删除",
    "set": "设置", "get": "获取", "use": "使用", "allow": "允许", "ignore": "忽略",
    "require": "需要", "required": "需要", "lock": "锁定", "unlock": "解锁",
    "snap": "对齐", "follow": "跟随", "hold": "保持", "stop": "停止", "start": "开始",
    "pause": "暂停", "resume": "继续", "scroll": "滚动", "rotate": "旋转",
    "move": "移动", "moves": "移动", "place": "放置", "break": "破坏", "mine": "挖掘",
    "dig": "挖掘", "build": "建造", "craft": "合成", "loot": "拾取", "drop": "丢弃",
    "pick": "拾取", "store": "存储", "stow": "收纳", "supply": "补给", "resupply": "补给",
    "refill": "补充", "consume": "消耗", "count": "计数", "track": "追踪",
    "search": "搜寻", "find": "寻找", "finder": "搜寻器", "scan": "扫描",
    "detect": "检测", "check": "检查", "test": "测试", "verbose": "详细",
    "debug": "调试", "info": "信息", "warn": "警告", "error": "错误", "log": "记录",
    "message": "消息", "chat": "聊天", "command": "命令", "config": "配置",
    "option": "选项", "setting": "设置", "value": "值", "default": "默认",
    "custom": "自定义", "fixed": "固定", "random": "随机", "smooth": "平滑",
    "linear": "线性", "instant": "立即", "immediate": "立即", "delay": "延迟",
    "interval": "间隔", "timeout": "超时", "duration": "持续时间", "period": "周期",
    "tick": "刻", "ticks": "刻", "second": "秒", "seconds": "秒", "sec": "秒",
    "ms": "毫秒", "minute": "分钟", "minutes": "分钟", "hour": "小时",
    "hold": "保持", "holdticks": "保持刻数", "manual": "手动", "always": "总是",
    "never": "从不", "only": "仅", "all": "全部", "none": "无", "some": "一些",
    "other": "其它", "same": "相同", "different": "不同", "multi": "多", "single": "单",
    "double": "双", "first": "第一", "last": "最后", "next": "下一个",
    "previous": "上一个", "max": "最大", "maximum": "最大", "min": "最小",
    "minimum": "最小", "mode": "模式", "type": "类型", "kind": "种类",
    "amount": "数量", "number": "数量", "total": "总数", "limit": "限制",
    "unlimited": "无限", "infinite": "无限", "infiniteflight": "无限飞行",
    "priority": "优先级", "order": "顺序", "sort": "排序", "filter": "过滤",
    "whitelist": "白名单", "blacklist": "黑名单", "list": "列表", "entry": "条目",
    "entries": "条目", "name": "名称", "names": "名称", "path": "路径",
    "file": "文件", "folder": "文件夹", "dir": "目录", "url": "链接",
    "key": "按键", "keybind": "按键绑定", "bind": "绑定", "bindings": "绑定",
    "press": "按下", "release": "松开", "click": "点击", "mouse": "鼠标",
    "keyboard": "键盘", "button": "按钮", "menu": "菜单", "screen": "界面",
    "window": "窗口", "page": "页面", "tab": "标签页", "section": "分区",
    "group": "分组", "category": "分类", "module": "模块", "addon": "附属模组",
    "hud": "HUD", "gui": "界面", "overlay": "覆盖层", "widget": "控件",
    "element": "元素", "panel": "面板", "bar": "条", "pointer": "指针",
    "preview": "预览", "expand": "展开", "collapse": "折叠", "export": "导出",
    "import": "导入", "copy": "复制", "paste": "粘贴", "edit": "编辑",
    "apply": "应用", "confirm": "确认", "cancel": "取消", "done": "完成",
    "select": "选择", "selected": "已选择", "none": "无", "active": "激活",
    "inactive": "未激活", "on": "开", "off": "关", "yes": "是", "no": "否",
    # 位置/几何
    "x": "X", "y": "Y", "z": "Z", "pos": "位置", "position": "位置",
    "coord": "坐标", "coords": "坐标", "center": "中心", "centre": "中心",
    "origin": "原点", "corner": "角落", "edge": "边缘", "side": "侧面",
    "top": "顶部", "bottom": "底部", "above": "上方", "below": "下方",
    "left": "左", "right": "右", "front": "前", "back": "后", "up": "上",
    "down": "下", "north": "北", "south": "南", "east": "东", "west": "西",
    "horizontal": "水平", "vertical": "垂直", "diagonal": "对角",
    "height": "高度", "width": "宽度", "length": "长度", "depth": "深度",
    "size": "大小", "scale": "缩放", "radius": "半径", "diameter": "直径",
    "range": "范围", "distance": "距离", "dist": "距离", "offset": "偏移",
    "spacing": "间距", "gap": "间隔", "margin": "边距", "padding": "内边距",
    "inner": "内部", "outer": "外部", "block": "方块", "blocks": "方块",
    "layer": "层", "layers": "层", "level": "层级", "axis": "轴",
    "corridor": "走廊", "curved": "弯曲", "straight": "直线",
    # 速度/运动
    "speed": "速度", "velocity": "速度", "acceleration": "加速度",
    "friction": "摩擦", "gravity": "重力", "jump": "跳跃", "fall": "坠落",
    "fly": "飞行", "flight": "飞行", "glide": "滑翔", "dive": "俯冲",
    "descend": "下降", "descending": "下降", "ascend": "上升", "climb": "攀爬",
    "pull": "拉升", "push": "推动", "boost": "推进", "brake": "刹车",
    "turn": "转向", "yaw": "偏航", "pitch": "俯仰", "roll": "翻滚",
    "angle": "角度", "degree": "度", "degrees": "度", "deg": "度",
    "rad": "弧度", "radian": "弧度", "rate": "速率", "mult": "倍数",
    "multiplier": "倍数", "factor": "系数", "delta": "增量", "step": "步长",
    "steps": "步数", "iteration": "迭代", "iterations": "迭代次数",
    "iters": "迭代次数", "refine": "细化", "arrive": "抵达", "arrival": "抵达",
    "target": "目标", "destination": "目的地", "waypoint": "路径点",
    "waypoints": "路径点", "route": "路线", "trajectory": "轨迹",
    "stall": "失速", "transition": "转换", "advance": "前进",
    "lookahead": "前瞻", "window": "窗口", "sample": "采样", "samples": "采样数",
    # 外观/渲染
    "render": "渲染", "rendering": "渲染", "display": "显示", "draw": "绘制",
    "background": "背景", "foreground": "前景", "color": "颜色", "colour": "颜色",
    "colors": "颜色", "alpha": "透明度", "opacity": "不透明度", "rgb": "RGB",
    "hex": "十六进制", "texture": "纹理", "font": "字体", "text": "文本",
    "label": "标签", "title": "标题", "tooltip": "提示", "shadow": "阴影",
    "border": "边框", "outline": "轮廓", "fill": "填充", "line": "线条",
    "lines": "线条", "box": "方框", "marker": "标记", "beam": "光束",
    "trail": "轨迹", "arrow": "箭头", "icon": "图标", "blur": "模糊",
    "glow": "发光", "highlight": "高亮", "chunk": "区块", "chunks": "区块",
    "dimension": "维度", "blueprint": "蓝图", "schematic": "投影",
    "entity": "实体", "entities": "实体", "esp": "透视", "tracer": "追踪线",
    "tracers": "追踪线", "nametag": "名称标签", "health": "生命",
    "hunger": "饥饿", "armor": "盔甲", "effect": "效果", "effects": "效果",
    "potion": "药水", "speedometer": "速度计", "watermark": "水印",
    # 实体/物品
    "player": "玩家", "players": "玩家", "mob": "生物", "mobs": "生物",
    "animal": "动物", "animals": "动物", "monster": "怪物", "hostile": "敌对",
    "passive": "被动", "item": "物品", "items": "物品", "ore": "矿石",
    "chest": "箱子", "barrel": "木桶", "furnace": "熔炉", "hopper": "漏斗",
    "shulker": "潜影盒", "ender": "末影", "inventory": "背包", "slot": "槽位",
    "slots": "槽位", "hotbar": "快捷栏", "container": "容器", "storage": "存储",
    "helmet": "头盔", "chestplate": "胸甲", "leggings": "护腿", "boots": "靴子",
    "sword": "剑", "axe": "斧", "pickaxe": "镐", "shovel": "铲", "hoe": "锄",
    "bow": "弓", "elytra": "鞘翅", "firework": "烟花", "fireworks": "烟花",
    "rocket": "火箭", "totem": "图腾", "bottle": "瓶", "food": "食物",
    "bread": "面包", "gapple": "金苹果", "apple": "苹果", "pearl": "珍珠",
    "enderpearl": "末影珍珠", "xp": "经验", "experience": "经验",
    "bottle": "瓶", "brew": "酿造", "brewing": "酿造", "stand": "台",
    "frame": "展示框", "brewingstand": "酿造台", "ladder": "梯子",
    "trapped": "陷阱", "boat": "船", "ship": "船", "minecart": "矿车",
    "horse": "马", "ride": "骑乘", "mount": "骑乘", "pet": "宠物",
    # 世界/环境
    "world": "世界", "nether": "下界", "end": "终点", "overworld": "主世界",
    "biome": "生物群系", "seed": "种子", "spawn": "出生", "spawner": "刷怪笼",
    "structure": "结构", "village": "村庄", "temple": "神殿", "fortress": "要塞",
    "portal": "传送门", "cave": "洞穴", "water": "水", "lava": "岩浆",
    "light": "光照", "lighting": "光照", "time": "时间", "weather": "天气",
    "rain": "下雨", "thunder": "雷暴", "day": "白天", "night": "夜晚",
    "sky": "天空", "city": "城市", "island": "岛屿", "region": "区域",
    "zone": "区域", "area": "区域", "near": "附近", "nearest": "最近",
    "far": "远", "nearby": "附近", "around": "周围", "surrounding": "周围",
    # 战斗
    "combat": "战斗", "fight": "战斗", "aura": "光环", "kill": "击杀",
    "kills": "击杀", "hit": "命中", "crit": "暴击", "critical": "暴击",
    "damage": "伤害", "reach": "触及", "aim": "瞄准", "silent": "静默",
    "legit": "合法", "blatant": "明显", "prediction": "预测",
    "rotate": "旋转", "rotation": "旋转", "swing": "挥动",
    # 运输/移动
    "walk": "行走", "sprint": "疾跑", "sneak": "潜行", "swim": "游泳",
    "travel": "旅行", "nav": "导航", "navigate": "导航", "barrier": "障碍",
    "obstacle": "障碍物", "corridor": "走廊", "parkour": "跑酷",
    "scaffold": "脚手架", "tower": "高塔", "ladder": "梯子",
    "spiral": "螺旋", "orbit": "环绕", "circle": "圆形",
    # 杂项
    "version": "版本", "update": "更新", "beta": "测试版", "legacy": "旧版",
    "experimental": "实验性", "official": "官方", "author": "作者",
    "license": "许可证", "issue": "问题", "issues": "问题", "source": "源码",
    "download": "下载", "install": "安装", "uninstall": "卸载",
    "compatibility": "兼容性", "support": "支持", "support": "支持",
    "translation": "翻译", "translate": "翻译", "language": "语言",
    "chinese": "中文", "english": "英文", "team": "团队", "project": "项目",
    "repository": "仓库", "release": "发布", "branch": "分支",
    "packet": "数据包", "anti": "反", "bypass": "绕过", "detect": "检测",
    "vanish": "消失", "invis": "隐身", "ghost": "幽灵", "fake": "伪造",
    "simulate": "模拟", "spoof": "欺骗", "safe": "安全", "danger": "危险",
    "confirm": "确认", "warning": "警告", "dangerous": "危险",
    "chord": "和弦", "note": "音符", "sound": "声音", "volume": "音量",
    "music": "音乐", "play": "播放", "loop": "循环", "repeat": "重复",
    "scale": "缩放", "rotate": "旋转", "flip": "翻转", "mirror": "镜像",
    # 第二轮补充（按真实词典未命中词频补充）
    "when": "当", "hand": "手", "interact": "交互", "threshold": "阈值",
    "swap": "交换", "swapping": "交换", "self": "自身", "air": "空中",
    "fd": "食物", "fw": "烟花", "look": "视角", "hole": "洞", "per": "每",
    "crash": "崩溃", "steal": "窃取", "dip": "下沉", "out": "外部",
    "durability": "耐久", "face": "面", "slider": "滑块", "replenish": "补充",
    "weapon": "武器", "web": "蛛网", "better": "更好", "blink": "闪烁",
    "spam": "刷屏", "fast": "快速", "empty": "空", "extra": "额外",
    "protect": "保护", "short": "短途", "packets": "数据包", "packet": "数据包",
    "offscreen": "屏幕外", "shape": "形状", "sensitivity": "灵敏度",
    "culling": "剔除", "hitbox": "碰撞箱", "explosions": "爆炸",
    "explosion": "爆炸", "fade": "淡出", "fire": "火焰", "friends": "好友",
    "hovered": "悬停", "liquids": "液体", "liquid": "液体", "mace": "重锤",
    "pressed": "按下", "rainbow": "彩虹", "anchor": "锚", "anvil": "铁砧",
    "exp": "经验", "sign": "告示牌", "camera": "相机", "crystal": "水晶",
    "include": "包含", "rebreak": "重复破坏", "middle": "中间",
    "offhand": "副手", "server": "服务器", "timer": "计时器",
    "scrollbar": "滚动条", "latency": "延迟", "attack": "攻击",
    "holding": "手持", "cast": "施放", "dump": "导出", "split": "拆分",
    "particles": "粒子", "particle": "粒子", "breeding": "繁殖",
    "breed": "繁殖", "burst": "爆发", "catch": "捕获", "column": "列",
    "fog": "雾", "if": "如果", "animation": "动画", "enchantment": "附魔",
    "exclude": "排除", "force": "强制", "ground": "地面", "modules": "模块",
    "age": "年龄", "handle": "处理", "knockback": "击退", "faster": "更快",
    "slow": "慢", "slower": "更慢", "quick": "快速", "instant": "立即",
    "ghost": "幽灵", "vanish": "消失", "invis": "隐身", "fake": "伪造",
    "simulate": "模拟", "spoof": "欺骗", "safe": "安全", "dangerous": "危险",
    "chord": "和弦", "note": "音符", "music": "音乐", "play": "播放",
    "loop": "循环", "repeat": "重复", "toggle": "切换", "smooth": "平滑",
    "stealth": "隐蔽", "silent": "静默", "legit": "合法", "blatant": "明显",
    "priority": "优先级", "preset": "预设", "profile": "配置档",
    "presets": "预设", "profiles": "配置档", "favorite": "收藏",
    "favorites": "收藏", "searchbar": "搜索栏", "filterbox": "过滤框",
    "checkbox": "复选框", "dropdown": "下拉框", "textbox": "文本框",
    "separator": "分隔符", "indent": "缩进", "align": "对齐",
    "tooltip": "提示", "placeholder": "占位符", "disabled": "已禁用",
    "hidden": "隐藏", "visible": "可见", "visibility": "可见性",
    # 第三轮补充
    "progress": "进度", "modifier": "修饰键", "potions": "药水", "sneaking": "潜行",
    "while": "当", "void": "虚空", "stack": "堆叠", "chams": "透视", "early": "提前",
    "dur": "耐久", "read": "读取", "xaero": "Xaero", "report": "报告", "now": "立即",
    "trident": "三叉戟", "zoom": "变焦", "placement": "放置", "projectiles": "弹射物",
    "bounce": "弹跳", "enchantments": "附魔", "invisibility": "隐身", "channels": "频道",
    "breaking": "破坏", "tools": "工具", "shulkers": "潜影盒", "full": "满",
    "keep": "保留", "map": "地图", "notifications": "通知", "moving": "移动",
    "stationary": "静止", "bounds": "边界", "predict": "预测", "prune": "修剪",
    "scrolling": "滚动", "shown": "显示", "simple": "简单", "direction": "方向",
    "sorting": "排序", "spear": "长矛", "stay": "停留", "screens": "界面",
    "unsprint": "取消疾跑", "ambience": "环境", "bed": "床", "dodge": "闪避",
    "attribute": "属性", "book": "书", "bot": "机器人", "boss": "Boss",
    "aimbot": "自瞄", "breadcrumbs": "足迹", "burrow": "钻地", "collisions": "碰撞",
    "criticals": "暴击", "discord": "Discord", "presence": "状态", "echest": "末影箱",
    "farmer": "农场", "enderman": "末影人", "flamethrower": "火焰喷射器",
    "freecam": "自由视角", "fullbright": "夜视", "view": "视角", "high": "高",
    "highway": "高速路", "builder": "建造者", "hitboxes": "碰撞箱",
    "filler": "填充器", "tweaks": "调整", "jesus": "水上行走", "logout": "登出",
    "spots": "位置", "long": "长", "multitask": "多任务", "nametags": "名称标签",
    "mining": "挖掘", "trace": "追踪", "notebot": "音符盒机器人",
    "notifier": "通知器", "nuker": "破坏器", "pop": "弹出", "portals": "传送门",
    "quiver": "箭袋", "reverse": "反向", "trap": "陷阱", "slippy": "打滑",
    "proofer": "防护", "spider": "蜘蛛", "surround": "环绕", "swarm": "蜂群",
    "trajectories": "弹道", "tunnel": "隧道", "vein": "矿脉", "miner": "挖掘器",
    "wall": "墙", "hack": "作弊", "xray": "透视", "tps": "TPS", "sync": "同步",
    "accent": "强调色", "accurate": "精确", "action": "动作", "loss": "损失",
    "advanced": "高级", "alignment": "对齐", "annoy": "骚扰", "percentage": "百分比",
    "suicide": "自杀", "weakness": "虚弱", "arrows": "箭", "control": "控制",
    "opposite": "相反", "avoid": "避免", "landing": "着陆", "grounded": "落地",
    # 第四轮补充（-er 派生词与少量遗漏）
    "manager": "管理器", "reader": "读取器", "writer": "写入器", "stealer": "窃取器",
    "smart": "智能", "percent": "百分比", "pct": "%", "parser": "解析器",
    "loader": "加载器", "saver": "保存器", "handler": "处理器", "holder": "容器",
    "adapter": "适配器", "logger": "记录器", "checker": "检查器",
    "helper": "助手", "recorder": "记录器",
    "predictor": "预测器", "solver": "求解器", "tracker": "追踪器",
    "replacer": "替换器", "detector": "检测器", "renderer": "渲染器",
    "drawer": "绘制器", "sorter": "排序器", "protector": "保护器",
    "killer": "击杀器", "breeder": "繁殖器", "copier": "复制器",
    "mover": "移动器", "jumper": "跳跃器", "climber": "攀爬器",
}

def build_words():
    # 去重检查
    assert len(W) > 300, len(W)
    out = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "words.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(sorted(W.items())), f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"words: {len(W)} entries -> {out}")
    return out

def tokenize(name):
    """kebab/snake/camel -> 词序列（小写）"""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    parts = re.split(r"[-_\s]+", s.lower())
    return [p for p in parts if p]

def translate_lexical(name):
    """模拟 Java WordTranslator 的行为"""
    toks = tokenize(name)
    if not toks:
        return None
    out = []
    unknown = []
    for t in toks:
        if t in SKIP:
            continue
        if t in W:
            out.append(W[t])
        elif t.isdigit():
            out.append(t)
        else:
            unknown.append(t)
            out.append(t.upper() if len(t) <= 3 else t.capitalize())
    if not out:
        return None
    if len(unknown) == len(out):
        return None
    return join_cn(out)


def join_cn(parts):
    """拼接中文片段，中文与拉丁/数字之间补空格"""
    s = "".join(parts)
    s = re.sub(r"([\u4e00-\u9fff])([A-Za-z0-9])", r"\1 \2", s)
    s = re.sub(r"([A-Za-z0-9])([\u4e00-\u9fff])", r"\1 \2", s)
    return s


SKIP = {"to", "in", "of", "for", "and", "or", "the", "a", "an", "on", "at", "by", "with", "from", "is", "are", "as"}

def regress():
    path = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "zh.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    total = hit = partial = miss = 0
    samples = []
    for section in ("modules", "settings"):
        for name, v in d.get(section, {}).items():
            title = v.get("title")
            if not title:
                continue
            total += 1
            gen = translate_lexical(name)
            if gen is None:
                miss += 1
                continue
            # 命中判定：生成的串与官方译名有 >=2 个共同字符（中文）
            common = len(set(gen) & set(title) - set("的了为与和"))
            if gen == title:
                hit += 1
            elif common >= 2:
                partial += 1
                if len(samples) < 12:
                    samples.append((name, title, gen))
            else:
                miss += 1
    print(f"\nregress: total={total} exact={hit} partial={partial} miss={miss}")
    print(f"  exact+partial = {(hit+partial)*100.0/total:.1f}%")
    for s in samples:
        print(f"  {s[0]:32s} off={s[1]:<14s} lex={s[2]}")

if __name__ == "__main__":
    build_words()
    regress()
