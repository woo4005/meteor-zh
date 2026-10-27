# 贡献指南 · Meteor-ZH

**Meteor-ZH**（mod id `meteor-zh`）是给 **Minecraft 1.21.11 · Fabric · Meteor Client** 用的全界面简体中文汉化 addon：装上后启动游戏自动翻译，纯客户端、无需手动操作。

- 仓库：<https://github.com/woo4005/meteor-zh>
- 许可证：**GPL-3.0-or-later**
- 当前版本：**1.4.0**
- 交流语言：简体中文

谢谢你愿意花时间。**目前最需要人手的贡献是翻译**——不需要写 Java，改 JSON 就行。

---

## 行为准则（简版）

- 友善、就事论事：技术争论针对代码和译文，不针对人。
- 不接受人身攻击、歧视、骚扰、刷屏。
- 讨论用简体中文即可；引用英文原文时保持原样，不要改写成"意译"。
- 维护者有权关闭不符合上述约定的 issue / PR。

---

## 报告 Bug

提交之前请先确认三件事：

1. 在 [Issues](https://github.com/woo4005/meteor-zh/issues) 里搜索过，没有重复；
2. 读过 README 的「安装」与「已知边界」——部分现象是刻意设计（例如设置分组内部名保持英文）；
3. 已删除旧的 `Meteor-I18n-Support-*.jar`。它和本模组功能重复，共存会干扰判断。

然后开一个 **Bug 报告**（仓库已带 Issue 模板），尽量带上：

| 信息 | 说明 |
|---|---|
| Minecraft 版本 | 精确到补丁号，例如 `1.21.11` |
| Fabric Loader 版本 | 启动器的版本列表，或 `logs/latest.log` 开头可查 |
| Meteor Client 版本 | 例如 `1.21.11` |
| meteor-zh 版本 | `mods/` 里的 jar 文件名，或游戏内执行 `.zh info` |
| `logs/latest.log` | **必填**。位置 `.minecraft/logs/latest.log`（PCL 版本隔离用户：`versions/<版本>/logs/latest.log`），完整粘贴或作为附件上传 |
| 截图 | 能直观看到缺失 / 错误文字的游戏界面 |
| 是否装了 I18n 类插件 | 例如 Meteor-I18n-Support；装过请先移除再复现 |
| 复现步骤 | 打开哪个模块、哪个分页、点了什么，越精确越好 |

崩溃类问题请一并附上 `crash-reports/crash-*.txt`。

---

## 贡献翻译（最需要人手的部分）

翻译不需要写 Java。所有译文都在 JSON 词典里，改完跑两个脚本即可。

### 1. 改哪个文件

| 要改的内容 | 文件 | 现有条目 |
|---|---|---|
| GUI 里硬编码的英文短语（按钮、标签、提示、标题） | `dict/zh_ui.json` | 242 条 |
| 按键名（Bind 旁边显示的键名） | `dict/zh_keynames.json` | 66 条 |
| 顶部标签页（Modules / Config / GUI / HUD …） | `dict/zh_tabs.json` | 7 条 |
| 第三方 addon 的模块名、设置名、描述句 | `dict/zh_addons.json` | `names` 96 条 / `descs` 22 条 |
| 词法兜底词表 | `src/main/resources/assets/meteorzh/lang/words.json` | 795 个词元（由脚本生成，**不要手改**） |

**不要手改** `src/main/resources/assets/meteorzh/lang/zh.json`。它是 `scripts/build_dict.py` 的产物，每次构建都会被覆盖。

### 2. JSON 结构

`dict/zh_ui.json` 按 GUI 位置分成 6 个桶，每个桶都是「英文原串 → 中文」：

```json
{
  "groups":   { "General": "通用", "Render": "渲染" },
  "labels":   { "Bind: ": "绑定: ", "Active: ": "激活: " },
  "sections": { "Modules": "模块", "Settings": "设置" },
  "buttons":  { "Add": "添加", "Apply": "应用" },
  "tooltips": { "Reset": "重置" },
  "titles":   { "Module copied!": "模块已复制！" }
}
```

- `groups`：设置分组标题（`General`、`Render` …）
- `labels`：界面上带冒号 / 空格的标签（`Bind: `、`Name: `、`Pos: ` …）
- `sections`：面板分节标题（`Modules`、`Settings`、`Animals` …）
- `buttons`：按钮文字
- `tooltips`：鼠标悬停提示
- `titles`：弹窗 / 提示条标题

其余文件是扁平的「键 → 值」。

`dict/zh_keynames.json`：

```json
{ "Left Shift": "左Shift", "Space": "空格", "None": "无" }
```

`dict/zh_tabs.json`：

```json
{ "Modules": "模块", "Config": "配置", "Macros": "宏" }
```

`dict/zh_addons.json` 多包一层 `names` / `descs`：

```json
{
  "names": { "auto-firework": "自动烟花", "arrival-range": "抵达范围" },
  "descs": { "AutoElytraV1 HUD element.": "AutoElytraV1 HUD 元素。" }
}
```

`names` 里的 kebab-case 标识符会同时用于模块表和设置表；`descs` 的键是英文原句（逐字一致）。

**有一条隐含规则**：`build_dict.py` 会跳过「值与原串完全相同」的条目（`value != name` 才收录）。所以想保留英文时**不要**写 `"Foo": "Foo"`，直接不写这条即可。

### 3. 键必须与英文原串逐字符一致

字典是运行时按字符串查表：**多一个空格、少一个冒号、大小写不同，都会查不到**，表现就是"这个词还是英文"。

这些是真实存在的、容易写错的键：

| 正确写法 | 容易写错成 | 区别 |
|---|---|---|
| `"Bind: "` | `"Bind:"` / `"Bind"` | 末尾有一个空格 |
| `"Active: "` | `"Active:"` | 前者带空格，**两个键同时存在且都收录** |
| `" - "` | `"-"` | 两侧空格 |
| `" > "` | `">"` | 两侧空格 |
| `"("` | `"（"` | 是半角左括号 |

做法：

- **直接复制**英文原串，不要手打。设置名 / 模块名来自 Meteor 的 `en_us.json`，仓库 `i18n_ref/en_us.json` 里有（CC0 语料，从 Meteor-I18n-Support 抽取）；GUI 硬编码短语和按键名请在 Meteor Client 源码里搜索（注意源码是 mojmap 映射）。
- 保存为 **UTF-8（无 BOM）**，JSON 用 2 空格缩进，**不能有尾逗号**。
- 新增条目请插在对应桶里、按字母序就近放，便于 diff 阅读。

### 4. 术语与风格

**先查已有译法。** 同一个英文词在 `dict/zh_ui.json` 里怎么译，就沿用（例如 `Setting`→设置、`Bind`→绑定、`Modules`→模块、`General`→通用）。术语不一致比"译得不准"更影响体验。

约定：

- **修饰键保留拉丁文**：`Ctrl` / `Shift` / `Alt` 不译，`Left Shift`→`左Shift`、`Right Control`→`右Ctrl`；`Super` 按现有译法作 `Win`（`Left Super`→`左Win`）。
- **`None` → `无`**。
- **鼠标键 → 鼠标左键 / 鼠标右键 / 鼠标中键**（与 `dict/zh_keynames.json` 现有写法一致）。
- **专有名词保留英文**：`Xaero`、`Baritone`、`Litematica`、`AutoElytra` 等 addon 名、作者名、模组品牌名不译；它们通常也不该出现在词典里。
- **标点沿用原文**：原文是 `"Bind: "` 就写 `"绑定: "`，用 ASCII 冒号 + 空格，**不要**换成全角「：」，也不要吞掉尾部空格。原文有 `...`、`!`、`?` 时中文用 `…`、`！`、`？`。
- **简洁优先**：GUI 空间有限，`Chat Feedback` 译「聊天反馈」而不是「聊天信息反馈」。
- **数字与占位符原样保留**：`Line 1`→`第 1 行`（数字前后按中文习惯留空格）；`%s`、`%d` 等占位符一个字符都不能动。
- **不加原文没有的标点**：原文没有句号，译文也不要加。

### 5. 改完必须跑

```bat
python scripts\build_dict.py
python scripts\verify_dict.py
```

- `build_dict.py`：合并 `i18n_ref` 语料与上述词典，重写 `src/main/resources/assets/meteorzh/lang/zh.json`，并打印 `modules / settings / groups / ui / descs` 条数。**条数不应无故减少**；新增翻译后对应条数应增加。
- `verify_dict.py`：在纯 JVM（不启动 Minecraft）里加载打好的 jar 查词，确认资源确实进包、Gson 能解析、查表能命中。

> 两个 `verify_*.py` 读的是 `dist/` 里**已打包的 jar**，所以改完词典要先重新打包再验证：
>
> ```bat
> python scripts\build.py
> python scripts\verify_dict.py
> ```
>
> 另外这两个脚本顶部把 `JAVA` 路径和 jar 文件名写死了（例如 `dist/meteor-zh-1.3.0.jar`）；你的环境不同时，改脚本开头的 `JAVA` / `JAR` 常量即可。

需要补词法兜底词表时：

```bat
python scripts\build_words.py
```

`words.json` 由 `scripts/build_words.py` 顶部的 `W` 词表生成，直接改 `words.json` 会在下次运行时被覆盖。要加词就改脚本里的 `W`，再重新生成。

### 6. 提交翻译 PR

- 分支命名：`i18n/<范围>`，例如 `i18n/ui-bind`、`i18n/keynames-mouse`。
- commit message 用 Conventional Commits，类型用 `i18n`：

  ```
  i18n(ui): 补全绑定与聊天反馈相关短语
  ```

- PR 里写清：改了哪个文件、新增/修正了哪些条目、`build_dict.py` 输出的条数变化、是否跑过 `verify_dict.py`。

---

## 贡献代码

### 环境

- **JDK 21**（Minecraft 1.21.11 要求 Java 21）
- Python 3（构建 / 验证脚本只依赖标准库，读写一律显式 UTF-8）
- Minecraft **1.21.11** · Fabric Loader **≥ 0.16.0** · Meteor Client **1.21.11**

### 构建方式

| 方式 | 命令 | 产物 | 适用 |
|---|---|---|---|
| Gradle（社区贡献者推荐） | `gradlew.bat build`（Windows） / `./gradlew build`（macOS、Linux） | `build/libs/` | 有网络、能拉依赖 |
| 离线脚本（维护者日常使用） | `python scripts\build.py` | `dist/meteor-zh-<版本>.jar` | 离线、无需 Gradle |

离线脚本的顺序是：`build_words.py` 生成词表 → `build_dict.py` 装配主词典 → `build.py` 用 `javac` 编译、再用 ASM 重映射到 intermediary 并打 jar。

### ⚠ 源码使用 Mojang 官方映射（mojmap），不是 yarn

这是本项目最容易踩的坑。从社区教程、其它 addon 或 yarn 项目抄来的代码，**大部分类名与 yarn 不同**，直接编译会报 `cannot find symbol`。

| 用途 | 本项目（mojmap） | yarn 里的名字 |
|---|---|---|
| 命令建议提供器 | `net.minecraft.commands.SharedSuggestionProvider` | `CommandSource` |
| 文本组件 | `net.minecraft.network.chat.Component` | `Text` |

写代码前先确认映射；编译报错找不到类时，**先怀疑映射不对**，而不是急着加依赖。

### 反射与 mixin 的边界

`Translator.java` 只修改**不参与 NBT 序列化**的显示字段（`Module.title`、`Setting.title`、`Category.name`、HUD 标题、标签页名）。这样改完界面是中文，但存档里的 `modules.nbt` / `config.nbt` 仍是英文键名，卸载后设置完全不受影响。

**绝对不要改 `SettingGroup.name`。** `Settings#fromTag` 按 name 查分组，改了会让所有已保存的分组设置失配——代码里 `Translator.java` 有注释说明，分组标题是在渲染层（`mixin/GuiRendererMixin.java`）替换的。

其它底线：

- 保持纯客户端：不新增网络请求、不下载远程内容、不收集数据。
- 不把译文写死进 Java；所有译文进 JSON 词典。
- 不为了"翻得更全"去替换 Meteor 的数据字段或改它的类，只动显示层。

### 分支与提交

| 分支前缀 | 用途 |
|---|---|
| `feat/<简短描述>` | 新功能 |
| `fix/<简短描述>` | 修复 bug |
| `i18n/<范围>` | 翻译 / 词典 |
| `docs/<简短描述>` | 文档 |

commit message 采用 Conventional Commits：`<type>(<scope>): <简短说明>`，type 用 `feat` / `fix` / `docs` / `i18n` / `refactor` / `build` / `chore`。说明用中文可以，示例：

```
i18n(ui): 补全绑定与聊天反馈相关短语
fix(bind): 修正鼠标侧键名未翻译
feat(tabs): 支持自定义标签页标题
docs: 补充 mojmap 命名说明
```

### PR 前要跑的脚本

```bat
python scripts\build_dict.py
python scripts\verify_dict.py
```

改动词法引擎 / 词表时再加：

```bat
python scripts\verify_lexical.py
```

跑 Gradle 的话，`gradlew.bat build` 能编译通过即可；行为验证仍建议进游戏点一遍。

---

## 提交 PR 前的检查清单

复制到 PR 描述里逐条打勾：

- [ ] 已运行 `python scripts/build_dict.py`，`zh.json` 已重新生成并一并提交
- [ ] 已运行 `python scripts/verify_dict.py`，无异常
- [ ] 新增 / 修改的词典键与英文原串**逐字符一致**（含尾部空格与冒号）
- [ ] 术语与 `dict/zh_ui.json` 已有译法一致
- [ ] 没有改动 `SettingGroup.name`（也没有其它破坏存档序列化的改动）
- [ ] Java 源码使用 **mojmap** 命名，不是 yarn
- [ ] 版本号：普通 PR **不动**版本号。发版时维护者改 `gradle.properties` 里的 `mod_version`（它是唯一版本源，`fabric.mod.json` 的 `"version": "${version}"` 由 Gradle 展开，不要手改成固定值）；用离线脚本发布时再同步改 `scripts/build.py` 顶部的 `VERSION`，两处版本必须一致
- [ ] 相关文档已更新（README「已知边界」、本文件、Issue/PR 模板）
- [ ] 提交中不含 `build/` 等编译中间产物；`dist/` 只提交发版 jar
- [ ] PR 描述写清了「为什么改」「怎么验证」，并用 `Closes #123` 关联 issue

---

## 不要做的事

- **不要提交构建产物**。除了 `dist/` 下的发版 jar（用于分发，允许提交），`build/`、`*.class`、临时 jar 等一律不要进提交。
- **不要改 `SettingGroup.name`**。它参与配置反序列化，改了会让所有人已保存的分组设置失配（`Translator.java` 有注释）。
- **不要把翻译写死进 Java 代码**。译文只进 JSON 词典，否则下次更新词表就被绕过。
- **不要提交 IDE / 本机配置**：`.idea/`、`.vscode/`、`*.iml`、含本机绝对路径的文件。
- **不要在一个 PR 里混无关改动**。批量格式化、重排整个 JSON 会和真实改动混在一起，没法 review。
- **不要用旧仓库地址**。本项目仓库是 <https://github.com/woo4005/meteor-zh>；文档、`fabric.mod.json`、`README` 里的链接都应指向这里，不要写历史账号。

---

## 许可

本项目以 **GPL-3.0-or-later** 授权。提交 PR 即表示你同意以同一许可证发布你的贡献。

历史说明：1.3.1 及更早的已发布版本是按 CC0-1.0（公共领域）发布的，**从 1.4.0 起**改为 GPL-3.0-or-later；新提交一律按 GPL 处理。

引用第三方语料时请确认许可证兼容：Meteor-I18n-Support 的语料是 CC0（可用）；CC BY-NC 之类**不能**直接并入本项目。

---

## 联系

- Bug / 功能请求：GitHub [Issues](https://github.com/woo4005/meteor-zh/issues)
- 安全问题：见 [SECURITY.md](SECURITY.md)，**不要**开公开 issue
- 作者：[woo4005](https://github.com/woo4005) · 开发协助：DeepSeek V4.1 flash 1017
