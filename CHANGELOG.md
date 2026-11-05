# 更新日志

**Meteor-ZH**（mod id `meteor-zh`）是 [Meteor Client](https://meteorclient.com) 的简体中文汉化附属模组，仓库位于 <https://github.com/woo4005/meteor-zh>。

本文件记录项目的所有重要变更。

- 格式遵循 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)。
- 版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)，本项目对版本号的具体用法见文末「版本号约定」。
- 本文件只收录公开发布的版本；**1.0.0 之前没有公开版本**。

## [未发布]

## [1.5.7] - 2026-11-05

修掉一个让 26.1.1 / 26.1.2 玩家误以为「没有新版」的 bug，并把资产名改成带版本区间。

### 修了什么

`UpdateChecker` 原先用「资产名必须以 `-mc<当前游戏版本>.jar` 结尾」来挑选发布资产：

```java
String targetSuffix = "-mc" + mcVersion() + ".jar";
if (!name.endsWith(targetSuffix)) continue;
```

而 26.1 线的资产叫 `meteor-zh-1.5.6-mc26.1.jar`。于是：

- 在 **26.1.1** 上，`mcVersion()` 是 `26.1.1`，要找 `-mc26.1.1.jar` → 不存在；
- 在 **26.1.2** 上，要找 `-mc26.1.2.jar` → 也不存在。

结果是「关于汉化插件」里显示 **未找到适配 26.1.1 的发布版本**——插件本身工作正常，
只是更新器的匹配条件写窄了。

### 怎么修的

新增 `UpdateChecker.assetMatches(name, mc)` 与 `specMatches(spec, mc)`，从资产名里取出
`-mc` 到 `.jar` 之间那段「适配版本表达式」，支持四种写法：

| 表达式 | 含义 | 例子 |
| --- | --- | --- |
| `1.21.11` | 精确匹配 | 只匹配 `1.21.11` |
| `26.1` | 前缀匹配，覆盖整条小版本线 | 匹配 `26.1` / `26.1.1` / `26.1.2` |
| `26.1~26.1.2` | 区间，含两端 | 匹配 `26.1` 到 `26.1.2` |
| `26.1.x` | 等价于 `26.1` | 匹配整条线 |

### 资产名改成 `meteor-zh-1.5.7-mc26.1~26.1.2.jar`

`scripts/build_261.py` 的产物名同步改成带区间的形式，玩家在 mods 目录里一眼就能看出这个 jar 覆盖哪几个小版本。

### 顺带

- 词表补 `CowBell` → 牛铃、`Didgeridoo` → 迪吉里杜管、`Chime` → 管钟（原版音符盒乐器名，之前显示英文）。
- `Test261` 新增 8 条更新器匹配断言：`26.1~26.1.2` 必须匹配 `26.1` / `26.1.1` / `26.1.2`、必须不匹配 `26.1.3`；
  `1.21.11` 匹配 `1.21.11` 不匹配 `1.21.10`；`26.1` 与 `26.1.x` 都要覆盖 `26.1.2`。

### 升级

- 26.1 线：1.5.6 → **1.5.7**（`meteor-zh-1.5.7-mc26.1~26.1.2.jar`）
- 1.21.11 线：1.4.6 → **1.4.7**（`meteor-zh-1.4.7-mc1.21.11.jar`，同一处修复）

## [1.4.7] - 2026-11-05

1.21.11 线的同步版本，内容与 [1.5.7] 相同（同一份源码），差异只有构建目标与产物名：

- 产物 `meteor-zh-1.4.7-mc1.21.11.jar`，mojmap 编译后 remap 到 intermediary，`compatibilityLevel: JAVA_21`。
- 更新器版本匹配同样改为支持前缀 / 区间表达式（1.21.11 本身就是精确版本，此处主要是与 26.1 线保持同一实现）。

## [1.5.6] - 2026-11-05

这一版把原本要单开 1.6.x 的「26.1.1 兼容」并回了 1.5.x 线——因为确认了
**26.1.1 与 26.1.2 用的是同一个 Meteor 客户端**，没必要为它单开版本号。

### 一个 jar 同时支持 26.1 / 26.1.1 / 26.1.2

Meteor 官方 26.1 线只发布过 `26.1.2-42` 一个客户端（`fabric.mod.json` 写 `minecraft: "~26.1"`）。
我把两个 MC 客户端 jar 逐字节比过：

- class 集合完全相同（各 10682 个）
- 只有 **8 个类**有差异：`DetectedVersion`、`SharedConstants`、`Checkbox`（+2 内部类）、
  `AbstractReportScreen`（+1 内部类）、`ServerGamePacketListenerImpl`
- Meteor 的 **211 个 mixin 没有一个**碰这 8 个类；插件引用的类也逐字节相同

`scripts/verify_261_cross.py` 把这件事固化成了检查（10 项断言）：用 26.1.1 的客户端 jar
重新编译同一份源码，断言两套 classpath 产出的 class **逐字节相同**。

> 26.1.1 实例里如果 Fabric 报缺少 `meteor-client`，那是没装 Meteor 客户端本人——
> 把 `meteor-client-26.1.2-42.jar` 放进 `mods/` 即可，26.1.1 用的就是它。

### 新增 `.zh dump`：导出模块与设置清单

借鉴 [Nippaku-Zanmu/meteor-translation-addon](https://github.com/Nippaku-Zanmu/meteor-translation-addon)
的 `JsonDump`。执行后会在游戏目录下写出 `meteor-zh/dump-<版本>-<时间>.json`，包含：

- 每个模块：所属 addon、分类、`name`（翻译用的英文标识符）、当前标题与描述、`inDictionary` 标记
- 每个设置：所属模块、分组、`name`、当前标题与描述、类型（`BoolSetting` 等）、`inDictionary` 标记
- 汇总：模块数、设置数、未命中词典的模块数、词典与词表规模

用途很实际：玩家装了什么 addon 我这边看不到，让对方跑一次 `.zh dump` 把文件发过来，
就能直接看出哪些标识符缺中文，不用再靠猜测补词条。
`inDictionary` 只查词典、不含词法兜底，所以能真实反映「收录了没有」。

### 顺带

- `scripts/build_261.py` 的产物名回到 `-mc26.1.jar`（不再用 `-mc26.1.x`），
  兼容范围写在 README 与本页说明里；
- `REQUIRED_ENTRIES` 补上 `Dumper` / `AboutModule` / `UpdateChecker`，构建时少一条就直接失败。

---

## [1.4.6] - 2026-11-05

与 1.5.6 对应的 1.21.11 线版本，包含同样的 `.zh dump` 功能。

---

## [1.6.0] 已被撤销

1.6.0 曾短暂发布，随后确认 26.1.1 与 26.1.2 共用同一个 Meteor 客户端，
没有必要为「26.1.x 兼容」单开大版本号，于是把内容并回 **1.5.6** 并删除该版本。

## [1.5.5] - 2026-11-04

### 新增

- **聊天栏消息汉化**：模块名早就会变成中文，但聊天里的正文一直是英文
  （`[Meteor] [仓库寻找器] Found stash at 123, 456.`、`[Meteor] [通知器] xxx's pearl landed at ...`）。
  现在这些消息也会显示中文。覆盖 Meteor 本体（Notifier / StashFinder / 命令回显 / 路径点 / 好友 / 配置档案）
  以及第三方插件的提示（Jefff 的仓库寻找器、Miku 的村民搬运、Baritone 的状态行等），共 **156 条模板**。
  - 挂在 `ChatUtils.formatMsg(String, ChatFormatting)` 上 —— 它是所有带文本消息的唯一汇聚点，
    名字在两个版本里都唯一且不含 MC 类型，所以一份源码能编译两条线。
  - `formatMsg` 收到的是**已经填好参数**的文本，所以翻译用「模板反查」：
    英文模板编译成整串锚定的正则（`%s` / `%d` / `%.1f` 变成捕获组），中文模板再用 `$1..$n` 拼回。
    构建期会硬校验中英模板的格式符个数与顺序一致，不一致直接构建失败。
  - `(highlight)` / `(default)` 伪颜色标记原样保留，聊天气泡的高亮配色不变。
  - 调试类输出（`resolveArea:`、`GoalNear{...}` 等）**故意不收录**：它们是诊断信息，翻译反而丢细节，
    宁可原样显示英文。
- 词典新增 `assets/meteorzh/lang/chat.json`（156 条），`.zh info` / `.zh reload` 会报告并重新加载它。

### 修复

- `ChatDict.translate("")` 会抛 `StringIndexOutOfBoundsException`（空消息取首字符）—— 已在入口拦掉。
- 新增 `scripts/verify_chat.py`（9 项断言）与 `scripts/jvm-test/TestChat.java`，
  用真实填好参数的英文消息验证反查结果，包括用户截图里的那两条。

---

## [1.4.5] - 2026-11-04

1.21.11 线，内容与 1.5.5 相同（同一份源码、同一个词典）：

- 聊天栏消息正文汉化（156 条模板，含 Jefff 仓库寻找器、Meteor 通知器、Baritone 状态行等）。
- 修复空消息导致 `StringIndexOutOfBoundsException`。
- 新增 `scripts/verify_chat.py` 离线验证。

---

## [1.5.4] - 2026-11-04

### 变更

- **官方译法优先**：Jefff / Lotus 官方汉化文件与本站译法不一致的条目，一律改用官方译法
  （`bounce` 弹跳、`scale` 缩放、`yaw` 偏航角）。官方未翻译（`Mode` / `Shape Mode` /
  `Notification Mode`）以及在本项目语境下含义不同的（`ping` 在 Meteor 里指网络延迟）保留原译。
- **作者信息**：`fabric.mod.json` 的 `authors` 加入 `deepseek-ai`，并新增 `contributors` 字段，
  模组列表里可以直接看到 AI 侧账号。

---

## [1.4.4] - 2026-11-04

1.21.11 线，内容与 1.5.4 相同（同一份源码、同一个词典）：

- 官方译法优先（同上）。
- `fabric.mod.json` 作者栏加入 `deepseek-ai`。
- README 补齐「关于汉化插件」「自动更新是怎么工作的」「meteor-addon-list.json」等说明。

---

## [1.5.3] - 2026-11-04

### 新增

- **「关于汉化插件」模块**：Meteor 里新增 `汉化` 分类与该模块，界面全中文，包含插件信息、
  检查更新、打开下载页、自动检测更新、自动下载更新。
- **启动时检测更新（每次启动只查一次）**：在世界里通过聊天栏提示，在主菜单通过右下角系统提示框提示，
  都带版本号与下载地址；网络失败静默放弃。
- **可选的后台静默更新**：勾选后自动下载与当前游戏版本匹配的 jar，退出游戏时用批处理替换旧 jar。
- **`.zh check` / `.zh update` / `.zh about`** 三个子命令。
- 合并 Jefff / Lotus 官方中文语言文件：18 个模块、142 个设置、138 条说明；其中 5 条官方译法
  覆盖了我们原有的译法（`item-frames`、`exp-slot`、`blocks-per-tick`、`minimum-storage-count`、`storage-blocks`）。

### 修复

- **1.21.11 线被判定版本不兼容**：`meteor-client` 依赖由 `>=1.21.11` 改为 `>=1.21.11-0`。
  Fabric 的 semver 把 `1.21.11-86` 视为 `1.21.11` 的预发布版，`1.21.11-86 < 1.21.11`，旧约束永远不满足。
- 离线校验会加载 remap 后的 jar（intermediary 命名）而 classpath 是 mojmap，插件一旦引用 MC 类型就
  `ClassNotFoundException`；1.21.11 线改用未 remap 的 `build/addon-mojmap.jar` 校验。
- OneDrive 占用构建目录导致 `shutil.rmtree` 报 `WinError 5`，构建脚本与校验脚本都改成可重试的 `wipe()`。
- 构建产物命名对齐 26.1 线：`meteor-zh-<版本>-mc<游戏版本>.jar`。

---

## [1.4.3] - 2026-11-04

1.21.11 线，功能与 1.5.3 相同（同一份源码），差异只有构建环境与产物名：

- 产物 `meteor-zh-1.4.3-mc1.21.11.jar`，mojmap 编译后 remap 到 intermediary，`compatibilityLevel: JAVA_21`。
- 修复 `meteor-client` 依赖写成 `>=1.21.11` 导致的不兼容提示。
- 新增「关于汉化插件」模块与自动更新检测（复用 26.1 线的实现）。
- 词典同步到 395 模块 / 1444 设置 / 1357 条英文说明。

---


暂无变更。后续改动会先记录在此处，发布时再归入对应版本号。

## [1.5.2] - 2026-10-30

> **1.5.1 的字体修复没有生效，本版才是真正的修复。**
> 1.21.11 线的同一修复以 **1.4.2** 发布，代码相同，只是构建目标不同。

### 修复

- **界面中文在 26.1 上仍然空白的问题（真正的根因与修复）**。
  - 1.5.1 的做法是「检测当前字体画不画得出中文，画不出就自动换一款系统里的中文字体」。这个检测用 `Fonts.RENDERER.getWidth("中文清单") > 0.5`，但 Meteor 的 `Font#getWidth` 对查不到字形的字符**回退成空格（码位 32）的宽度**：

    ```java
    CharData c = charMap.get(cp);
    if (c == null) c = charMap.get(32);   // ← 缺字形 = 空格宽度
    width += c.xAdvance;
    ```

    于是这个判断恒为真、换字体的分支一次都没跑过，日志里的「can render Chinese」是假的。
  - 更根本的原因：Meteor 的字体图集在 `Font` 构造时就**写死了只打包 6 个码位区间**——Basic Latin 32–126、Latin-1 160–255、Latin Ext-A 256–383、Greek 880–1023、Cyrillic 1024–1279、∞ 8734。**无论换成哪款中文字体，图集里都不会有中日韩字形**，所以「自动换字体」这条路本身走不通。
  - **正确做法：让 Meteor 改用 Minecraft 原版字体渲染。** `TextRenderer.get()` 的实现是
    `Config.get().customFont.get() ? Fonts.RENDERER : VanillaTextRenderer.INSTANCE`，
    把 `Config.customFont` 关掉就切到 `VanillaTextRenderer`（用的是 MC 的 `mc.font`，天然支持中文）；再把 `VanillaTextRenderer.INSTANCE.scaleIndividually` 设为 `true`，让中文这种双宽字符按实际宽度排布，否则会挤在一起。
  - `FontFixer` 因此重写：删掉字体候选表与 `getWidth` 探测，只保留 `ensureVanillaRenderer()`。代价是失去 Meteor 的自定义美术字体、界面改用原版字体样式——这是能正常显示中文的最小代价。
- **`.zh reload` 之前是空操作**：`ZhDict.load()` 开头有 `if (loaded) return;`，重新翻译时压根没重读词典。新增 `ZhDict.reload()`（清空 7 张表后重新加载），命令改调它。
- **词法兜底过度拼接**：未知标识符会被逐词拼成「无 Such 模块 XYZ」这类半中半英的串。现在要求「未识别的词不超过已识别词的一半」，否则放弃翻译、保留原文。
- **`scripts/sanity_zh.py` 误删正常词条**：它的占位语过滤规则里含「占位」「placeholder」，把 `placeholder-color`（占位符文本的颜色）当成未翻译占位语删掉了。规则已收窄为真正的未翻译标记。

### 变更

- **验证脚本从「只打印」改成「真断言」**：`TestZh` / `TestLex` / `Test261` 逐条断言并用退出码表示成败，`verify_dict.py` / `verify_lexical.py` / `verify_261.py` 透传退出码——以前 JVM 能启动就算通过，词典坏了也照样绿。
  - `Test261` 用新增的 `Translator.missingFields()` 真正检查反射字段是否都还在（原来那行「9 个反射字段全部存在」是无条件打印）。
  - `verify_261.py` 发现源码比 jar 新时会自动重建，避免拿旧产物跑出假绿。
  - `_verify_env.find_jar()` 增加按构建线挑选的参数，不再「按修改时间取最新」（两个 jar 同时在 `dist/` 里时会挑错线）。
- `scripts/build_261.py`：javac 加 `--release 25`（原来没有，换个 JDK 就会产出更高版本的字节码，游戏里直接 `UnsupportedClassVersionError`）；Meteor 的 jar 改为自动发现；实例路径与 JDK 支持环境变量覆盖；打包后自动校验 JSON 可解析、每个 class 的 major 版本、必需条目齐全。
- `scripts/build.py`：RemapJar 工具的缓存改为比较时间戳（原来「class 文件存在就跳过」，改了工具源码永远不会重编）；classpath 拼装改用 `os.pathsep`。
- `fabric.mod.json` 补齐 `java` 与 `meteor-client` 依赖声明——装错环境时 Fabric 会给出清楚的提示，而不是插件悄悄不生效。
- `build_words.py` 增加「同键不同值」检测：`release` 曾同时被写成「松开」和「发布」，后写的静默覆盖前写的。词表产物现在与来源文件闭合（新增 `scripts/absorb_orphan_words.py`，把 217 个孤儿词并回 `dict/zh_external_words.json`）。

### 说明

- 26.1 线：1.5.1 → **1.5.2**。
- 1.21.11 线：1.4.1 → **1.4.2**（同步本修复）。
- `v1.5.1` / `v1.4.1` 仍可下载，但字体问题没解决，建议升级。

## [1.4.2] - 2026-10-30

> 1.21.11 线的同步修复版，内容与 [1.5.2] 一致，只是构建目标是 Minecraft 1.21.11。

### 修复

- 字体修复改为「关闭 `Config.customFont`、走 `VanillaTextRenderer`」，并设 `scaleIndividually`（原理详见 [1.5.2]）。
- `.zh reload` 真正重新读取词典。
- 词法兜底增加收敛规则，不再把未知标识符拼成半中半英的串。

### 变更

- 验证脚本改为真断言；`build.py` 的 RemapJar 缓存按时间戳失效；`fabric.mod.json` 补 `java` / `meteor-client` 依赖。

## [1.5.1] - 2026-10-28

> ⚠️ **本版的字体修复无效，已被 [1.5.2] 取代。** 原因见 [1.5.2]：`getWidth` 探测恒为真、换字体的分支从未执行，而且 Meteor 的字体图集本身就不含中日韩码位，换字体这条路走不通。

> **字体热修复版（尝试）**：修掉 1.5.0 在 Minecraft 26.1 上「界面中文全部显示为空白」的问题。
> 1.21.11 线的同一修复以 **1.4.1** 发布，代码相同，只是构建目标不同。

### 修复

- **界面中文在 26.1 上完全不显示**。Meteor 的 GUI 不使用 Minecraft 的字体，而是把界面文字烘焙进一张自建的字体图集；它自带的四款字体（JetBrains Mono / Comfortaa / Tw Cen MT / Pixelation）只有拉丁字形，没有任何中日韩字形。图集里查不到的字符不会生成任何绘制指令，于是整段中文静默消失——数字和尚未翻译的英文照常显示，看起来像界面坏掉一半。1.21.11 实例早先被手动把字体设成了「等线」所以一直正常，全新的 26.1 实例默认 Comfortaa，问题才暴露。
  - 新增 `com.meteorzh.FontFixer`：用一个中文探针串测量当前字体的渲染宽度，宽度为 0 就判定「画不出中文」，自动把 Meteor 切到系统里第一款可用的中文字体（等线 DengXian → 微软雅黑 Microsoft YaHei → 黑体 SimHei → 宋体 SimSun → Noto Sans CJK SC → 苹方 PingFang SC → …），并把结果写回 `Config.font`，重启后保持。
  - 已经能显示中文的机器不会被动到，字体偏好原样保留。
  - 字体图集要等首次资源加载才建立，所以自检放在最初 40 个 tick 内重试，不会抢在资源加载前误判。
  - 一个中文字体都找不到时，在日志与 `.zh font` 的输出里给出明确指引；设置里也可以手动选字体。
  - 新增 `.zh font` 命令，随时重新检测并汇报当前字体。
- `meteor-zh.mixins.json` 的 `compatibilityLevel` 改为**按构建线生成**：1.21.11 线 `JAVA_21`，26.1 线 `JAVA_25`（1.5.0 期间曾被统一改成 `JAVA_25`）。

### 变更

- `scripts/verify_261.py` 增加 `FontFixer` 探针：在没有 GL 上下文的环境里必须安全返回 `false` 而不是抛异常（已实测通过）。
- `scripts/build.py` / `scripts/build_261.py` 分别按目标版本重写 `compatibilityLevel`，两条线共用同一份 `src/main/resources`。

### 说明

- 26.1 线：1.5.0 → **1.5.1**。`v1.5.0` 已从 Release 撤下 jar、只保留事故说明，请勿再使用。
- 1.21.11 线：1.4.0 → **1.4.1**（同步本修复）。

## [1.4.1] - 2026-10-28

> 1.21.11 线的同步修复版，内容与 [1.5.1] 一致，只是构建目标是 Minecraft 1.21.11。

### 修复

- 新增 `FontFixer`：自动检测当前 Meteor 字体能否渲染中文，不能则切到系统里可用的中文字体（原理详见 [1.5.1]）。
- `meteor-zh.mixins.json` 的 `compatibilityLevel` 恢复为 `JAVA_21`（1.5.0 期间曾被统一改成 `JAVA_25`）。

## [1.5.0] - 2026-10-28
> 本次发布新增 **Minecraft 26.1 / Meteor Client 26.1.x** 支持，为一条独立的构建线（26.1 线，版本号 1.5.x）。1.21.11 线继续使用 **1.4.0** 的 jar，版本号保持 1.4.x 独立递增（后续 1.4.1、1.4.2……）。两条线的源码共用同一份，只有构建脚本与产物名不同；词典为两条线共享，本次扩充对两个 jar 同时生效。

### 新增

- 支持 Minecraft 26.1 + Fabric Loader 0.20.1 + Java 25 + Meteor Client 26.1.2。产物名带 `-mc26.1` 后缀，与 1.21.11 的 jar 可以同时放在各自实例的 mods 里，互不影响。
- `scripts/build_261.py`：26.1 专用离线构建脚本。MC 26.x 起游戏不再混淆，所以**整条 mojmap → intermediary 的 remap 流程被删掉**，编译完直接打包；classpath 由实例的 version json 自动拼出，无需手写清单。
- `scripts/extract_261.py`：扫描 Meteor 26.1.2 的 sources jar，提取全部模块名、设置名、分组名与描述，用来和现有词典比对找缺口。
- `scripts/patch_261_dict.py`：把 26.1 相对旧版新增/改名的词条补进 `dict/zh_addons.json`。
- `scripts/merge_external.py`：把社区其它 Meteor 汉化项目（`xingke0/meteor_chinese` 等）的译名并入本项目词典。**只收「Meteor 26.1 源码里真实存在」的标识符**，以及按英文原句匹配的描述句，已有中文绝不覆盖。
- `scripts/sanity_zh.py`：合并后体检，剔除值里带「暂未翻译 / TODO」之类占位语的条目。
- `scripts/verify_261.py`：26.1 的离线验证——用实例真实 classpath 加载插件 jar，检查词典、**9 个反射字段全部存在**、若干查找结果，不启动游戏即可跑。

### 变更

- **词典大幅扩充**：模块 267 → 376 条，设置 1136 → 1335 条，英文描述句 22 → **1357 条**，词法引擎词表 795 → **1012 词元**。
  - 描述句是这次收益最大的一项：Meteor 的模块说明与设置说明都按英文原句查表，1357 条覆盖了 26.1 本体 + AutoElytra/Miku 等常见 addon 的绝大多数说明文字。
- **Minecraft 26.1 本体覆盖率经脚本核对达到 100%**：169 个模块、968 个设置项、92 个设置分组，全部有中文标题；每一条的英文说明也都有对应中文（走 `descriptions` 表按英文原句匹配）。
- `meteor-zh.mixins.json` 的 `compatibilityLevel` 由 `JAVA_21` 提升到 `JAVA_25`（Minecraft 26.x 的 class 是 Java 25 编译的，Sponge Mixin 0.8.7 支持 `JAVA_25`）。对 1.21.11 线同样有效。
- `ZhCommand.build()` 改用原始类型 `LiteralArgumentBuilder`：Meteor 1.21.11 的抽象方法签名是 `LiteralArgumentBuilder<SharedSuggestionProvider>`，26.1 起改成 `LiteralArgumentBuilder<ClientSuggestionProvider>`，泛型擦除后签名相同，用原始类型可以一份源码同时编译两个版本。
- `fabric.mod.json` 在 26.1 构建时自动注入 `"java": ">=25"` 依赖，低版本 JVM 会得到明确的版本提示而不是 `UnsupportedClassVersionError`。
- `scripts/build.py` 增加 stdout/stderr 的 UTF-8 重定向，避免 Windows GBK 控制台在打印非 ASCII 编译错误时抛 `UnicodeEncodeError` 盖住真正的错误。

### 修复

- 26.1 构建时 `meteordevelopment.orbit`、`net.fabricmc.api`、`org.spongepowered.asm.mixin` 找不到：Meteor 把 orbit / gson 等以嵌套 jar 形式放在自己 jar 的 `META-INF/jars/` 下，javac 读不了嵌套 jar，需要先解出来；`fabric-loader` 与 `sponge-mixin` 在 PCL 的 version json 里没有 `downloads.artifact`，要按 Maven 坐标自己拼路径。

### 已知问题（已由 1.5.1 修复）

- **在 Minecraft 26.1 上，界面里所有中文都显示为空白**：模块名、设置项标题、分组标题都渲染不出来，只剩数字和尚未翻译的英文，看起来像界面坏了一半。原因是 Meteor 自带的字体不含中日韩字形（详见 [1.5.1] 的说明），全新实例默认使用 Comfortaa 时就会暴露。1.21.11 上因为字体早先被手动设成「等线」而没有出现。
  - 临时规避：Meteor 里打开 `设置 → Visual → Font`，换成一款中文字体即可。
  - **本版 jar 已从 Release 撤下，不再提供下载**，请改用 [1.5.1]。

## [1.4.0] - 2026-10-27

> 本次发布把许可证从 CC0 1.0 迁移到 GNU GPL v3.0（GPL-3.0-or-later）。再分发或二次开发前请先阅读 `LICENSE` 与 `NOTICE`。

### 新增

- `DEVELOPERS.md` 开发者档案：公开 AI 参与范围与具体工作明细。
- `CONTRIBUTING.md` 贡献指南：覆盖 Bug 报告、翻译贡献、代码贡献与 PR 检查清单。
- `CHANGELOG.md`（本文件）与 `NOTICE`（第三方归属声明）。
- `.github/ISSUE_TEMPLATE/` 下的 Bug 报告表单、功能请求表单与 `config.yml`。
- `.github/PULL_REQUEST_TEMPLATE.md` 合并请求模板。
- `.github/workflows/build.yml`（push / PR 自动构建）与 `.github/workflows/release.yml`（打 tag 自动发布）。
- 标准 Fabric Loom Gradle 工程（`build.gradle` / `settings.gradle` / `gradle.properties` / Gradle Wrapper），源码采用 Mojang 官方映射名（mojmap），配置 `loom.officialMojangMappings()`。

### 变更

- **许可证从 CC0 1.0 迁移到 GNU GPL v3.0（GPL-3.0-or-later），全部源码补充 SPDX 许可证头。**
- `README.md` 全面重写：补上 Meteor Client 兼容矩阵、Mixin 注入目标类与冲突面、性能影响说明与测量方法、Windows / macOS / Linux 构建说明、作者与 AI 贡献说明。
- 作者与联系信息更新为 `woo4005`，仓库地址统一为 <https://github.com/woo4005/meteor-zh>。

### 修复

- `fabric.mod.json` 的版本号改为构建期注入（`${version}`），避免手工修改多处。

## [1.3.1] - 2026-10-26

### 变更

- `fabric.mod.json` 的 homepage / sources / issues 全部指向新仓库 <https://github.com/woo4005/meteor-zh>。
- 发布 GitHub Release `v1.3.1`，附上首个正式分发包 `meteor-zh-1.3.1.jar`。

### 修复

- 修复仓库地址从旧账号迁移后出现的链接失效问题。

## [1.3.0] - 2026-10-26

### 新增

- **词法兜底引擎 `WordTranslator`**：词典未收录的 kebab 标识符按词逐字合成中文，词表 795 个词元；对现有 1388 条词典的回归命中率为 83.6%。
- `scripts/build_words.py`：词表生成与回归评估脚本。
- 应用图标（256×256 PNG，纯标准库生成）。
- `fabric.mod.json` 补充作者、GitHub 链接与 Issues 链接（游戏内「问题」按钮可用）。
- `README.md` 与 `LICENSE`（当时为 CC0 1.0）。

### 变更

- 词典规模扩展到 267 个模块 / 1136 条设置 / 129 个分组 / 295 条 UI 文本 / 66 条按键名 / 7 个标签页 / 22 条描述 / 795 个词元。

## [1.2.0] - 2026-10-26

### 新增

- 第三方 addon 词典：AutoElytra 与 Miku 的 96 个名称 + 22 条描述句。
- GUI 硬编码短语表 242 条（按钮 / 分组名 / 区块标题 / tooltip）。
- 按键名词典 66 条（`Left Shift` → `左Shift`、`None` → `无`、鼠标键 → 鼠标左键）。
- 顶部标签页翻译 7 条（Modules / Config / GUI / HUD / Friends / Macros / Profiles）。
- `scripts/build_dict.py` 多源词典装配流程。

### 变更

- `ZhDict` 增加描述表与模块 / 设置交叉回退查找。

## [1.0.0] - 2026-10-26

首个公开可用版本。

### 新增

- 模块名与模块描述中文化（覆盖 Meteor 本体 171 个模块）。
- 设置项名称与描述中文化。
- 设置分组标题中文化（`General` → `通用`、`Render` → `渲染` 等）。
- 反射改写引擎：在 JDK 21 下对非 `static final` 的实例字段执行 `setAccessible` + `set`。
- 首次 tick 自动翻译；重启游戏后自动重译，无需手动触发。
- `.zh` / `.zh reload` / `.zh info` 命令。
- 通过 Mixin 拦截 `GuiRenderer#text`，替换 GUI 中写死的英文按钮与提示。
- 词典基础：沿用 `Meteor-I18n-Support`（作者 yalu，CC0 1.0）的 2454 条 Meteor 本体词条。

## 版本号约定

本项目维护两条**各自独立编号**的版本线，源码共用同一份 `src/`，但产物与版本号互不牵连：

| 版本线 | 游戏版本 | 产物 | 构建脚本 |
|---|---|---|---|
| **1.4.x** | Minecraft 1.21.11 | `meteor-zh-1.4.0.jar` | `scripts/build.py` |
| **1.5.x** | Minecraft 26.1 | `meteor-zh-1.5.0-mc26.1.jar` | `scripts/build_261.py` |

- 1.21.11 线的后续更新发 **1.4.1、1.4.2……**；26.1 线的后续更新发 **1.5.1、1.6.0……**。
  某一条线需要提高最低游戏版本时，在该线内递增主版本号（例如 26.1 线将来若要求 Meteor 27.x，则发 2.0.0）。
- **主版本号（MAJOR）**：破坏配置兼容性，或提高该线内最低 Minecraft / Meteor Client 版本要求时递增。
- **次版本号（MINOR）**：新增翻译覆盖范围（词典条目、词表词元、UI 短语、按键名、标签页、第三方 addon 词条）时递增。
- **修订号（PATCH）**：词典条目修订、翻译错误修正、构建与元数据修复，不改变已有行为契约。
- 词典是两条线**共享**的资源；扩充词典后应同时重新构建两个 jar，各自按自己的版本线递增。

[未发布]: https://github.com/woo4005/meteor-zh/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/woo4005/meteor-zh/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/woo4005/meteor-zh/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/woo4005/meteor-zh/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/woo4005/meteor-zh/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/woo4005/meteor-zh/compare/v1.0.0...v1.2.0
[1.0.0]: https://github.com/woo4005/meteor-zh/releases/tag/v1.0.0
