# 更新日志

**Meteor-ZH**（mod id `meteor-zh`）是 [Meteor Client](https://meteorclient.com) 的简体中文汉化附属模组，仓库位于 <https://github.com/woo4005/meteor-zh>。

本文件记录项目的所有重要变更。

- 格式遵循 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)。
- 版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)，本项目对版本号的具体用法见文末「版本号约定」。
- 本文件只收录公开发布的版本；**1.0.0 之前没有公开版本**。

## [未发布]

暂无变更。后续改动会先记录在此处，发布时再归入对应版本号。

## [1.5.0] - 2026-10-28
> 本次发布新增 **Minecraft 26.1 / Meteor Client 26.1.x** 支持，为一条独立的构建线；1.21.11 线继续用 1.4.x 的 jar。两条线的源码共用同一份，只有构建脚本与产物名不同。

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

- **主版本号（MAJOR）**：破坏配置兼容性，或提高最低 Minecraft / Meteor Client 版本要求时递增。
- **次版本号（MINOR）**：新增翻译覆盖范围（词典条目、词表词元、UI 短语、按键名、标签页、第三方 addon 词条）时递增。
- **修订号（PATCH）**：词典条目修订、翻译错误修正、构建与元数据修复，不改变已有行为契约。

[未发布]: https://github.com/woo4005/meteor-zh/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/woo4005/meteor-zh/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/woo4005/meteor-zh/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/woo4005/meteor-zh/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/woo4005/meteor-zh/compare/v1.0.0...v1.2.0
[1.0.0]: https://github.com/woo4005/meteor-zh/releases/tag/v1.0.0
