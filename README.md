# Meteor-ZH · Meteor Client 中文化

给 **Minecraft 1.21.11 · Fabric · Meteor Client** 用的全界面简体中文汉化 addon。

装上即用：**启动游戏自动翻译**，不需要点任何按钮，重启后依然生效。

> 作者：**dsh-woo4005**　·　DeepSeek V4.1 flash 1017 协助完成

---

## 为什么用它

原版 Meteor Client 不带中文。社区里的 `Meteor-I18n-Support` 只翻译了模块名和设置项，
**GUI 里大量硬编码英文**（`Bind`、`Modules`、`Reset`、`Chat Feedback`）以及**按键名**
（`Left Shift`、`Space`）依旧是英文，第三方附属模组也完全没有覆盖。

Meteor-ZH 把这些补齐了：

| 位置 | 覆盖情况 |
|---|---|
| 模块名 + 描述 | Meteor 本体 171 个模块全覆盖，第三方 addon 由词典与词表兜底 |
| 设置项名称 + 描述 | 1136 条 |
| 设置分组标题 | 129 条（`General`→`通用`、`Render`→`渲染` …） |
| GUI 硬编码文字 | 295 条（`Bind`→`绑定`、`Modules`→`模块`、`Apply`、`Chat Feedback` …） |
| 按键名（Bind） | 66 条（`Left Shift`→`左Shift`、`Space`→`空格`、`None`→`无`） |
| 顶部标签页 | Modules / Config / GUI / HUD / Friends / Macros / Profiles |
| HUD 元素名与分组 | 标题与描述 |
| 第三方插件描述句 | 22 条（AutoElytra 等） |

**已经自带中文的插件（如 Lotus、Miku 的中文模块）原样保留，不会被二次翻译。**

---

## 自动适配新装的插件

`Meteor-ZH` 在启动时遍历 Meteor 已加载的**所有**附属模组，而不只是写死的清单。
词典里没有的名称会走**内置词表逐词合成**：

```
chunk-render-distance  ->  区块渲染距离
auto-totem-refill      ->  自动图腾补充
potion-refill-threshold->  药水补充阈值
world-origin           ->  世界原点
```

词表目前 795 个词元，覆盖 Meteor 生态的常见词汇。合成不了的词保留英文，绝不乱翻；
纯中文标识符直接跳过。所以你以后新装 addon，重启一次就能看到中文，不需要等作者更新。

---

## 安装

1. 从 [Releases](https://github.com/wzy080532/meteor-zh/releases) 下载 `meteor-zh-x.y.z.jar`
2. 放进 `.minecraft/mods/`（PCL 版本隔离用户：`E:\pcl\.minecraft\versions\1.21.11-Fabric 0.19.3\mods\`）
3. **删掉**旧的 `Meteor-I18n-Support-*.jar`（共存不会崩，但功能重复）
4. 启动游戏

要求：Fabric Loader ≥ 0.16.0，Minecraft ≥ 1.21.9，仅客户端。

---

## 游戏内命令

```
.zh          重新翻译一次并显示统计
.zh reload   重新加载词典并翻译
.zh info     查看词典条数与加载状态
```

---

## 卸载

删掉 jar 即完全恢复英文。

本插件**不写入任何配置**——不改 `modules.nbt`、不改 `config.nbt`、不改键位与 HUD 布局，
所以卸载后你原有的设置全部保持原样。

---

## 已知边界

1. **设置分组的内部名**（如 `General`）只翻译显示，存储仍是英文。这是刻意的：分组名参与配置反序列化，改了会让已保存的分组设置失配。
2. **`None`、按键名**在渲染层替换，配置文件里存的还是英文键名，不影响使用。
3. 少数第三方设置的缩写含义不明（`enable-rp`、`min-dur`），采用了保守译法。
4. 词法合成是逐词拼合，个别专有名词（`Pitch40`、`Xaero`）会保留英文。

---

## 从源码构建

不需要 Gradle，用 `javac` + 自带的 ASM 重映射工具直接出包（离线可用）。

```bat
cd projects\meteor-zh
python scripts\build_words.py    :: 生成词表 words.json
python scripts\build_dict.py     :: 装配主词典 zh.json
python scripts\build.py          :: 编译 + remap + 打包 -> dist\meteor-zh-x.y.z.jar
```

关键脚本：

| 脚本 | 作用 |
|---|---|
| `build_words.py` | 生成词法词表，并用现有词典做回归评估 |
| `build_dict.py` | 合并 I18n 语料、GUI 短语、按键名、标签页、第三方条目 |
| `build.py` | javac 编译 → ASM 重映射到 intermediary → 打 jar |
| `verify_dict.py` / `verify_lexical.py` | 纯 JVM 验证词典与词法引擎 |
| `github_publish.py` | device flow 授权后发布到 GitHub |

词典来源：Meteor 本体 2454 条取自 `Meteor-I18n-Support`（CC0 公共领域），其余由本项目整理与翻译。

---

## 许可

[CC0 1.0 Universal](LICENSE) — 公共领域，随便用。
