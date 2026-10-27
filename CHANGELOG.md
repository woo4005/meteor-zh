# 更新日志

**Meteor-ZH**（mod id `meteor-zh`）是 [Meteor Client](https://meteorclient.com) 的简体中文汉化附属模组，仓库位于 <https://github.com/woo4005/meteor-zh>。

本文件记录项目的所有重要变更。

- 格式遵循 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)。
- 版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)，本项目对版本号的具体用法见文末「版本号约定」。
- 本文件只收录公开发布的版本；**1.0.0 之前没有公开版本**。

## [未发布]

暂无变更。后续改动会先记录在此处，发布时再归入对应版本号。

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
