# 更新日志

**Meteor-ZH**（mod id `meteor-zh`）是 [Meteor Client](https://meteorclient.com) 的简体中文汉化附属模组，仓库位于 <https://github.com/woo4005/meteor-zh>。

本文件记录项目的所有重要变更。

- 格式遵循 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)。
- 版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)，本项目对版本号的具体用法见文末「版本号约定」。
- 本文件只收录公开发布的版本；**1.0.0 之前没有公开版本**。

## [未发布]

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
