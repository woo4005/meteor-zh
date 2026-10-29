# Meteor-ZH · Meteor Client 全界面中文化

[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Build](https://github.com/woo4005/meteor-zh/actions/workflows/build.yml/badge.svg)](https://github.com/woo4005/meteor-zh/actions/workflows/build.yml)
[![Minecraft](https://img.shields.io/badge/Minecraft-26.1%20%7C%201.21.11-62b47a.svg)](#兼容性)
[![Fabric](https://img.shields.io/badge/Fabric-0.20.1%20%7C%200.19.3-dbb69b.svg)](#兼容性)
[![Version](https://img.shields.io/badge/26.1--%E7%BA%BF-1.5.2-a855f7.svg)](CHANGELOG.md)
[![Version](https://img.shields.io/badge/1.21.11--%E7%BA%BF-1.4.x-a855f7.svg)](CHANGELOG.md)

**Meteor-ZH** 是一个 Meteor Client 附属模组（addon），把 Meteor 的整套界面翻成简体中文：模块名、功能描述、设置项名称与说明、设置分组、**按键名（Bind）**、HUD 元素、顶部标签页，以及 GUI 里写死在代码中的按钮与提示文字。

装上即用 —— **启动游戏自动翻译，不点任何按钮，重启后依然生效**。新装的附属模组也会在下次启动时被自动识别并翻译。

> 作者：[woo4005](https://github.com/woo4005)　·　开发协助：DeepSeek V4.1 flash 1017
> 许可证：[GNU GPL v3.0](LICENSE)（GPL-3.0-or-later）　·　[开发者档案](DEVELOPERS.md)　·　[变更日志](CHANGELOG.md)　·　[贡献指南](CONTRIBUTING.md)

---

## 目录

- [为什么需要它](#为什么需要它)
- [功能覆盖](#功能覆盖)
- [兼容性](#兼容性)
- [安装](#安装)
- [游戏内命令](#游戏内命令)
- [新装的插件怎么办](#新装的插件怎么办)
- [技术实现](#技术实现)
- [性能影响](#性能影响)
- [已知边界](#已知边界)
- [从源码构建](#从源码构建)
- [参与贡献](#参与贡献)
- [许可证](#许可证)
- [作者与 AI 贡献](#作者与-ai-贡献)

---

## 为什么需要它

Meteor Client 本体不带中文（`assets/meteor-client/lang/` 下的语言文件是空壳）。社区里的
[`Meteor-I18n-Support`](https://github.com/yalu-owo/Meteor-I18n-Support) 用 Mixin 改了模块和设置的
`title` 字段，但界面里还有**大量写死在代码里的英文字面量**它覆盖不到：

```java
// ModuleScreen.java —— 这些字符串不在任何 lang 文件里，改配置无效
theme.section("Bind", true);
theme.label("Bind: ");
theme.label("Toggle on bind release: ");
theme.label("Chat Feedback: ");
theme.label("Active: ");
reset.tooltip = "Reset";
```

再加上按键名（`Left Shift`、`Space`、`None`）、顶部标签页（`Modules`、`Config`、`HUD`）和第二、第三方的
附属模组（AutoElytra、Miku、Lotus……），装了汉化插件仍然到处是英文。

Meteor-ZH 把这些都补上了。

---

## 功能覆盖

| 位置 | 覆盖方式 | 词条数 |
|---|---|---|
| 模块名 + 模块描述 | 反射改写 `Module.title` / `Module.description` | 376 模块（另按英文原句匹配 1357 条说明） |
| 设置项名称 + 说明 | 反射改写 `Setting.title` / `Setting.description` | 1335 条（说明同样走原句匹配） |
| 设置分组标题 | 反射改写 `SettingGroup.name` 的**显示值** | 129 条 |
| GUI 硬编码文字 | Mixin 拦截 `GuiRenderer#text` 做字符串替换 | 295 条 |
| 按键名（Bind） | 同渲染层替换，`Left Shift`→`左Shift`、`None`→`无` | 66 条 |
| 顶部标签页 | 反射改写 `Tab.name` | 7 条 |
| HUD 元素名与分组 | 反射改写 `HudElementInfo.title/description`、`HudGroup.title` | — |
| 第三方插件的模块与描述 | 词典 + 词法兜底引擎 | 96 名称 + 22 描述句 |
| 模块/设置说明文字 | `descriptions` 表按英文原句精确匹配 | 1357 条 |
| 词典未收录的新标识符 | 1012 词元的词法合成引擎 | — |

**已经自带中文的插件（Lotus、Miku 的中文模块）会原样跳过，不会被二次翻译。** 这是词法引擎的
硬性设计：一个词都没命中时返回 `null`，调用方保留原文。

---

## 兼容性

| meteor-zh | Minecraft | Fabric Loader | Meteor Client | Java | 状态 |
|---|---|---|---|---|---|
| **1.5.2** | **26.1** | ≥ 0.20.1 | **26.1.2**（`26.1.2-SNAPSHOT` build 42） | **25** | 26.1 专用线 |
| **1.4.x** | 1.21.11 | ≥ 0.16.0 | 1.21.11（`1.21.11-SNAPSHOT`，发布版 build 82） | 21 | 1.21.11 专用线，继续维护 |
| 1.3.x | 1.21.11 | ≥ 0.16.0 | 1.21.11 | 21 | 已被 1.4.x 替代 |
| ≤ 1.2.x | 1.21.11 | ≥ 0.16.0 | 1.21.11 | 21 | 已被替代 |

**两条线各自独立编号，按游戏版本选择对应的 jar**：

| 游戏版本 | 下载的 jar | 版本线 | 构建脚本 |
|---|---|---|---|
| Minecraft **26.1** | `meteor-zh-1.5.2-mc26.1.jar` | 1.5.x | `scripts/build_261.py` |
| Minecraft **1.21.11** | `meteor-zh-1.4.2.jar` | 1.4.x | `scripts/build.py` |

两条线的源码共用（同一份 `src/`），但**版本号各走各的**：1.21.11 线的后续更新发 1.4.2、1.4.3……，
26.1 线的更新发 1.5.2、1.6.0……，互不牵连。词典是两条线共享的资源，会同时扩充到两个 jar 中。

两个 jar 分别放进各自实例的 `mods` 目录即可；同一个实例里**不要同时放两个**（mod id 相同，Fabric 会报重复）。

关于“支持哪些 Meteor 版本”的说明：

- Meteor-ZH 只依赖 Meteor 的四个**长期稳定**的类：`Module`、`Setting`、`SettingGroup`、`GuiRenderer`。
  26.1 与 1.21.11 的这四个类字段名一致，真正变了的只有 `Command#build` 的泛型参数
  （`SharedSuggestionProvider` → `ClientSuggestionProvider`），已用原始类型兼容两边。
- 本 mod **没有**逐个小版本做回归验证。Meteor 一旦改动上述字段或 `GuiRenderer#text` 的签名，
  数据层翻译会失效（Mixin 部分有 `required = false` 兜底，不会崩游戏）。
- **不支持 Minecraft 1.20.x 及更早**：1.21 换了渲染管线与 mappings，跨大版本无法兼容。
- **不支持服务端**：`environment: client`，纯客户端 mod。

### Mixin 注入点与冲突面

本项目是“半个侵入式插件”，使用者有权知道它动了什么：

| 项目 | 值 |
|---|---|
| Mixin 配置 | `meteor-zh.mixins.json`，`required: false`；`compatibilityLevel` 按构建线生成：1.21.11 线 `JAVA_21`、26.1 线 `JAVA_25` |
| 目标类 | `meteordevelopment.meteorclient.gui.renderer.GuiRenderer` |
| 目标方法 | `public void text(String text, double x, double y, Color color, boolean title)` |
| 注入方式 | `@ModifyVariable(method = "text", at = @At("HEAD"), argsOnly = true)`，改写第一个 `String` 参数 |
| remap | `remap = false` —— 目标方法参数里没有任何 Minecraft 类型，描述符在 mojmap 与 intermediary 下完全一致，不需要 refmap |
| 可能冲突的 mod | 任何同样 `@ModifyVariable` / `@Redirect` 到 `GuiRenderer#text` 的 Meteor addon。两个 `@ModifyVariable` 会互相覆盖，结果为“最后加载的那个说了算”，**不会崩溃** |

**明确不改的字段**（改了会破坏你的配置）：

| 字段 | 为什么不能改 |
|---|---|
| `SettingGroup.name` | 参与 `Settings.fromTag()` 反序列化，改名会让**所有已保存的分组设置失配** |
| `Module.name` | 模块在 `modules.nbt` 里的存储键 |
| `Category.nameHash` | 内部哈希，不参与序列化但影响集合比较 |
| `Setting.name` | 设置项在配置里的键名 |

---

## 安装

1. 从 [Releases](https://github.com/woo4005/meteor-zh/releases) 下载对应你游戏版本的 jar：
   - **Minecraft 26.1** → `meteor-zh-1.5.2-mc26.1.jar`
   - **Minecraft 1.21.11** → `meteor-zh-1.4.2.jar`
2. 放进 `mods/` 目录
   - 官方启动器：`.minecraft/mods/`
   - **PCL 版本隔离**：`<PCL目录>/.minecraft/versions/<版本名>/mods/`
3. **删掉**旧的 `Meteor-I18n-Support-*.jar`（与它共存不会崩，但功能重复，且两者的翻译会互相覆盖）
4. 启动游戏，翻译自动完成，字体也会自动检查

前置要求：

| 游戏 | Fabric Loader | Java | Meteor Client |
|---|---|---|---|
| Minecraft 26.1 | ≥ 0.20.1 | **25** | 26.1.x |
| Minecraft 1.21.11 | ≥ 0.16.0 | 21 | 1.21.11 |

### 界面里的中文变成空白？

Meteor 的 GUI 不用 Minecraft 的字体，而是把文字烘焙进自建的字体图集。它自带的四款字体
（JetBrains Mono / Comfortaa / Tw Cen MT / Pixelation）**只有拉丁字形，没有中日韩字形**；
更关键的是——图集的码位范围在代码里写死了，只打包 Basic Latin、Latin-1、Latin Ext-A、
Greek、Cyrillic 和 ∞，**换成任何一款中文字体也不会多出中日韩字形**。
图集里查不到的字符不画任何东西，只留一个空格宽度的空位，于是中文整段消失、
数字和没翻译的英文照常显示。

从 **1.5.2 / 1.4.2** 起插件会自己解决：启动时把 Meteor 的 `Config.customFont` 关掉，
让它改用 Minecraft 原版字体渲染（`VanillaTextRenderer`，用 MC 自带的 `mc.font`，
天然支持中文），并把 `scaleIndividually` 打开让双宽字符正确排布。
代价是失去 Meteor 的自定义美术字体，界面换成原版字体样式——这是能显示中文的最小代价。

> 1.5.1 / 1.4.1 曾尝试「自动切换到系统中文字体」，那个方案是无效的：
> 检测用的 `getWidth` 对缺字形字符会回退成空格宽度、恒为真，换字体的分支从未执行。

如果还是空白：

1. 执行 `.zh font`（游戏内聊天栏）查看当前渲染器状态；
2. 执行 `.zh reload` 强制重新初始化一次；
3. 确认没有同时装着两个 meteor-zh 的 jar（26.1 线和 1.21.11 线的 mod id 相同，不能共存）。

### 卸载

删掉 jar 即完全恢复英文。

本插件**不写入任何配置**——不改 `modules.nbt`、`config.nbt`、键位、HUD 布局，也不在游戏目录落盘任何文件。
所以卸载后你原有的设置全部保持原样。

---

## 游戏内命令

```
.zh          重新翻译一次并显示改动统计
.zh reload   重新加载词典并翻译
.zh info     查看词典条目数与加载状态
```

---

## 新装的插件怎么办

Meteor-ZH 在启动时遍历 Meteor 已加载的**全部**附属模组（`Modules.get().getAll()`），
而不只是写死的清单。词典里没有的名称会走**词法合成引擎**逐词拼出中文：

```
chunk-render-distance   ->  区块渲染距离
auto-totem-refill       ->  自动图腾补充
potion-refill-threshold ->  药水补充阈值
world-origin            ->  世界原点
min-height-log          ->  最小高度记录
```

词表 **795 个词元**，覆盖 Meteor 生态的常见词汇（`render`/`chunk`/`totem`/`waypoint`/`elytra`……）。
引擎做了三件事保证不乱翻：

1. 剔除虚词（`to`、`in`、`of`、`for`、`the`……），中文不需要它们
2. 未识别的词保留拉丁原文（`Xaero`、`Baritone` 这类专有名词不会被硬译）
3. **一个词都没命中就返回 `null`** —— 纯中文标识符（`自动跟随`、`Miku 投影打印机`）天然跳过

对现有 1388 条人工词典做回归评估，词法引擎命中率 **83.6%**（449 条完全一致 + 711 条部分命中）。
剩下的保留英文，不会产生乱码式翻译。

所以你以后新装 addon，重启一次就能看到大部分中文，不需要等作者更新词典。

---

## 技术实现

两条互相独立的通道，互为降级：

```
                  ┌──────────────────────────────────────────┐
  启动 → 首次 tick →│ 通道 A：反射改写实例字段（数据层）        │
                  │  Module/Setting/SettingGroup/Category/   │
                  │  Tab/HudElementInfo 的 title+description │
                  └──────────────────────────────────────────┘
                  ┌──────────────────────────────────────────┐
  每帧 GUI 绘制  → │ 通道 B：Mixin 拦截 GuiRenderer#text      │
                  │  查 HashMap，命中则替换字符串            │
                  └──────────────────────────────────────────┘
```

**通道 A —— 反射改写实例字段。** JDK 21 对**非 static 的 final 实例字段**，只要
`setAccessible(true)` 后调用 `Field.set()` 就能改写（JLS 允许，实际验证通过）。
相比 `@Accessor @Mutable` 的 Mixin 方案，它不需要改字节码、不需要处理字段合并警告，
而且**完全绕过序列化**——因为只改内存里的字符串，不碰 `name` 字段。

**通道 B —— Mixin 拦截渲染入口。** Meteor 的 GUI 是自绘的（Mingwei 风格），所有文字最终都走到
`GuiRenderer.text(...)`。在方法入口改写第一个 `String` 参数，就能覆盖所有写死的字面量，
而不用去改上百处调用点。

**为什么不用运行时持久化？** 不需要。每次启动重新翻译一次，天然满足“重启后依然生效”，
而且不引入任何缓存文件、不担心缓存与实际 mod 版本不一致。

**源码中的映射约定：本项目使用 Mojang 官方映射名（mojmap），不是 yarn。**
所以你会看到 `net.minecraft.commands.SharedSuggestionProvider`（yarn 里叫 `CommandSource`）
和 `net.minecraft.network.chat.Component`（yarn 里叫 `Text`）。Gradle 工程因此配置
`loom.officialMojangMappings()`，见 [从源码构建](#从源码构建)。

---

## 性能影响

实测数据（JDK 21.0.7 / OpenJDK 64-Bit Server VM，20 逻辑核，`-Xmx1g`）。测量脚本与结果可复现，
方法见表格下方。

| 指标 | 实测值 | 说明 |
|---|---|---|
| 词典解析（类已加载） | **30 ms** | 重置加载标志后二次解析 `zh.json` + `words.json` |
| 词典解析（冷启动首次） | 1.2 s | 含 Gson、Meteor 类的首次加载与校验 |
| 词典常驻堆 | **≈ 1.5 MB** | 1834 条中英文字符串 + 7 张 HashMap |
| 启动期字段改写 | **0.43 ms / 2200 次** | 反射 `Field.set`，约 197 ns/次 |
| 运行期 GUI 文本查表 | 命中 **3.3 ns**，未命中 **19.4 ns** | 2000 万次 `HashMap.get` |
| 词法合成（仅词典未命中时） | **≈ 2 µs / 标识符** | 含正则拆词 + 逐词查表 + 拼接 |
| jar 体积 | 63 KB | — |
| 运行期线程 | 0 个新增 | 只用主线程首次 tick 一次 |

**怎么读这些数字：**

- 翻译只在**启动后第一次 `TickEvent.Post`** 执行一次，之后从事件总线退订，运行期零开销。
- GUI 每帧会调用 `GuiRenderer#text` 几十到几百次，每次多一次 HashMap 查询（3~19 ns），
  即每帧增加**微秒级**开销，远低于渲染一帧所需的时间。
- 词法合成只在“词典没收录”时触发，且只在启动那一次发生。即使装 10 个陌生 addon、
  有 500 个未收录标识符，总耗时也只有约 1 ms。
- **没有测到的**：真实游戏内的 FPS 变化、内存峰值。这类数据需要在完整客户端里跑
  Spark profiler 才准确，本项目未做；上面给出的是各步骤本身的耗时，据此推算帧率影响可忽略。

复现方式（离线，不需要启动游戏）：

```bash
# 词典加载与查表行为
python scripts/verify_dict.py
python scripts/verify_lexical.py
```

微基准源码在 `scripts/bench/`（`PerfBench.java` 测反射 set 与 HashMap 查表，
`MemoryZh.java` 测词典加载耗时与堆占用）。

---

## 已知边界

> 字体相关的边界见上文「[界面里的中文变成空白？](#界面里的中文变成空白)」。

1. **设置分组的内部名不翻译，只翻译显示。** `SettingGroup.name` 参与配置反序列化
   （`Settings.fromTag()` 按 `name` 找分组），改了会让已保存的分组设置全部失配。所以
   `General` 的**标题**显示为「通用」，但存储里仍是 `General`。
2. **按键名与 GUI 文字在渲染层替换**，配置文件里存的还是英文键名。这不影响使用，
   但你在 `.nbt` 里看到的仍是英文。
3. **`Category`（左侧一级分类）不翻译。** 分类名不在配置里，但 Meteor 的分类列表是硬编码枚举，
   改名收益低、风险高（部分 addon 会按名字查找分类）。
4. **少数第三方设置的缩写含义不明确**（`enable-rp`、`min-dur`、`dt-max`），采用保守译法，
   宁可留可疑译法也不用长句猜测。
5. **词法合成是逐词拼合**，个别专有名词（`Pitch40`、`Xaero`、`Baritone`）会保留英文，
   个别组合词可能读起来略生硬（`chest-stealer-percent` → `箱子 StealerPercent`）。
6. **不翻译 Starscript 表达式内部的变量名** —— 那是脚本标识符，翻了会让脚本报错。
7. **已经是中文的标识符一律跳过**，不做二次处理。
8. **不支持 1.20.x 及更早**，理由见[兼容性](#兼容性)。
9. **与 `Meteor-I18n-Support` 共存时功能重复**：两者都改 `title` 字段，后加载的会覆盖前者。
   建议删掉旧的，只保留 Meteor-ZH（词典数据本身就是从它继承并扩展的）。
10. **Mixin 失效会降级**：`required = false`，即使 Meteor 某次更新改了 `GuiRenderer#text` 签名，
    游戏不会崩，但 GUI 里的硬编码英文（`Bind`、`Reset` 那批）会重新出现，数据层翻译仍有效。
11. **`.zh` 命令依赖 Meteor 的命令系统**，若被其他 mod 占用了 `zh` 这个前缀则需改用其他名字
    （目前没有已知冲突）。
12. **词典未覆盖的第三方 addon 描述句**保留英文（只翻了 AutoElytra、Miku 等已知 addon 的描述）。

---

## 从源码构建

有两种方式。**社区贡献者用 Gradle，维护者本机用离线脚本**——两条路产出的 jar 功能一致。

### 方式一：Gradle（推荐，目前只配了 1.21.11 线）

需要 JDK 21、联网访问 `maven.fabricmc.net` 与 `maven.meteordev.org`。

```bash
git clone https://github.com/woo4005/meteor-zh.git
cd meteor-zh
./gradlew build          # Windows: gradlew.bat build
# 产物：build/libs/meteor-zh-<版本>.jar
```

> 仓库里的 `build.gradle` 目前写死 Minecraft 1.21.11 / Loader 0.19.3 / Java 21。
> **26.1 线（Minecraft 26.1、Loader 0.20.1、Java 25）暂时只有离线脚本这条路**，
> 因为 26.x 不混淆、不需要 remap，Loom 的 `remapJar` 流程在这里反而不适用。
> 想把 26.1 也接进 Gradle，需要另建一个 `build-261.gradle.kts` 之类的配置，
> 把 Loom 换成不 remap 的模式。

工程配置要点：

| 项 | 值 |
|---|---|
| Loom 插件 | `net.fabricmc.fabric-loom-remap` 1.17.19 |
| Minecraft | 1.21.11 |
| Fabric Loader | 0.19.3 |
| 映射 | **`loom.officialMojangMappings()`**（源码是 mojmap 命名，不能用 yarn） |
| Meteor 依赖 | `meteordevelopment:meteor-client:1.21.11-SNAPSHOT` |
| Java | toolchain 21 |

> **注意**：Gradle 工程面向 GitHub Actions 与联网环境。维护者所在网络访问不到 Maven Central，
> 所以本机发布用的是下面的离线流程。Gradle 这条路径在 CI 上验证，未在本机逐次验证。

### 方式二：离线脚本（维护者实际使用）

不需要 Gradle，用 `javac` + 自带的 ASM 重映射工具直接出包，全程离线。

```bat
cd projects\meteor-zh
python scripts\build_words.py    :: 生成词表 words.json（含回归评估）
python scripts\build_dict.py     :: 装配主词典 zh.json

:: --- 1.21.11 线 ---
python scripts\build.py          :: 编译 + remap + 打包 -> dist\meteor-zh-x.y.z.jar

:: --- 26.1 线（不需要 remap，但要 JDK 25）---
python scripts\extract_261.py    :: 扫 Meteor 26.1 源码，比对词典缺口
python scripts\build_261.py      :: 编译 + 打包 -> dist\meteor-zh-x.y.z-mc26.1.jar
```

| 脚本 | 作用 |
|---|---|
| `scripts/build_words.py` | 生成词法词表，并用现有词典做回归评估（打印命中率） |
| `scripts/build_dict.py` | 合并 I18n 语料、GUI 短语、按键名、标签页、第三方条目 → `zh.json` |
| `scripts/build.py` | 1.21.11 线：javac 编译 → ASM 重映射到 intermediary → 打 jar |
| `scripts/build_261.py` | 26.1 线：javac(JDK 25) 编译 → 直接打 jar（26.x 不混淆，无 remap） |
| `scripts/extract_261.py` | 扫 Meteor 26.1.2 源码，提取模块/设置/分组/描述，与词典比对 |
| `scripts/patch_261_dict.py` | 把 26.1 新增词条补进 `dict/zh_addons.json` |
| `scripts/verify_dict.py` | 纯 JVM 加载 jar 内词典，检查查找结果 |
| `scripts/verify_lexical.py` | 纯 JVM 验证词法合成引擎 |
| `scripts/extract_*.py` | 从 Meteor 源码/jar 提取候选短语（UI 文本、按键名、addon 条目） |

> **26.1 线的两个坑**（`build_261.py` 已处理，改脚本时别回退）：
> 1. Meteor 把 `orbit`、`gson` 等依赖以**嵌套 jar** 形式放在自己 jar 的 `META-INF/jars/` 下，
>    javac 读不了嵌套 jar，必须按 `fabric.mod.json` 的 `jars` 字段解出来再加进 classpath，否则
>    报 `找不到符号: meteordevelopment.orbit.EventHandler`。
> 2. `fabric-loader` 与 `sponge-mixin` 在 PCL 生成的 version json 里**没有** `downloads.artifact`，
>    但 jar 确实在 `libraries/` 下，要按 Maven 坐标自己拼路径。

产物在 `dist/`，直接丢进 `mods/` 即可。

---

## 参与贡献

欢迎贡献，尤其是**翻译修正**——这是最需要人的地方。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

一句话版本：

- **报告问题**：用 [Issue 模板](https://github.com/woo4005/meteor-zh/issues/new/choose)，附上 `latest.log`
- **修正翻译**：改 `dict/zh_*.json` 里对应的条目，键必须与英文原串**逐字符一致**（含尾部空格和冒号），
  然后跑 `python scripts/build_dict.py` 与 `python scripts/verify_dict.py`
- **提交代码**：注意本项目源码用 **mojmap** 命名，不是 yarn；PR 前跑一遍构建脚本

---

## 许可证

本项目以 **GNU 通用公共许可证第 3 版**（GNU General Public License v3.0，
SPDX 标识 `GPL-3.0-or-later`）发布。

```
Meteor-ZH — Meteor Client 简体中文汉化
Copyright (C) 2026 woo4005

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

完整条款见 [LICENSE](LICENSE)（GPL-3.0 官方全文，35 KB）。第三方组件与数据归属见 [NOTICE](NOTICE)。

这意味着：你可以自由使用、修改、再分发本 mod，甚至商用；但**分发修改版时必须同样以 GPL-3.0
开放源码**，并保留版权声明与许可证全文。Minecraft 服务端整合包、模组包分发属于「再分发」，
需要保留 `LICENSE` 与 `NOTICE` 文件。

许可证历史上是 CC0-1.0（公共领域），**从 1.4.0 起改为 GPL-3.0-or-later**。1.3.1 及更早的
已发布版本仍按当时的 CC0-1.0 授权。

---

## 作者与 AI 贡献

本项目由 **woo4005** 提出需求、决定产品方向并验收，具体的设计、编码、词典整理、构建工具链与
文档由 **DeepSeek V4.1 flash 1017** 在 [DeepSeek Harness](https://github.com/deepseek-ai) 中完成。

> 这不是一句客套话——**代码、词表、脚本、文档实际上全部由 AI 生成**，作者的角色是提出需求、
> 提供真实环境（游戏目录、截图、日志）、逐轮验收与纠正方向。

完整的参与范围与逐项工作明细见 [DEVELOPERS.md](DEVELOPERS.md)，包含：

- AI 独立完成的部分（架构选型、反射引擎、Mixin、词法引擎、全部脚本、全部文档）
- 人机协作的部分（真实环境验证、需求变更、翻译风格裁定）
- 未被 AI 完成、由人处理的部分（游戏内实际游玩验证、GitHub 账号操作）
- 为什么这份档案要写得这么细（后续维护者需要知道代码是怎么来的）

## 致谢

- [Meteor Development](https://github.com/MeteorDevelopment/meteor-client) —— Meteor Client 本体
- [yalu](https://github.com/yalu-owo/Meteor-I18n-Support) —— `Meteor-I18n-Support` 的 2454 条
  Meteor 本体词条（该项目以 CC0 1.0 发布，本项目在此基础上扩展并重新组织）
- Fabric 团队 —— Fabric Loader / Loom
- 以及所有在群里反馈翻译问题的玩家

本项目是社区项目，与 Meteor Client 官方、Mojang Studios 均无从属关系。
