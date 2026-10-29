# Meteor-ZH 发布文案（QQ 群用）

> 用于在 Meteor / MC 插件群推广。三个版本按场景取用。
> 发布前请先把两个 jar 传到**群文件**，因为群里不少人打不开 GitHub：
> `meteor-zh-1.5.2-mc26.1.jar`（Minecraft 26.1）与 `meteor-zh-1.4.2.jar`（Minecraft 1.21.11）。

---

## 一、群聊短版（直接复制，约 200 字）

```text
【Meteor 汉化】自制的 Meteor Client 中文化插件，装上就全中文了

Meteor 本体没有中文，之前那个 I18n 只翻了模块名和设置项，
GUI 里 Bind、Modules、Reset、Chat Feedback 这些还是英文，按键名也是 Left Shift 这种，
第三方 addon 更是完全没覆盖。

这个全补上了（26.1 和 1.21.11 都有）：
· 模块名 + 功能描述（305 个模块）
· 1174 条设置项名称和说明
· 设置分组（General→通用、Render→渲染）
· GUI 按钮和提示文字
· 按键名（Left Shift→左Shift、None→无）
· 顶部标签页、HUD 元素名
· 新装的 addon 自动识别，词典没有的逐词合成中文

启动自动翻译，不用点任何东西，重启照样生效。

下载见群文件（或 GitHub Releases）
源码：https://github.com/woo4005/meteor-zh
有问题这里提：https://github.com/woo4005/meteor-zh/issues

开源 GPL-3.0，随便用随便改，改了再分发记得也开源。
```

---

## 二、完整版（群公告 / 群精华，约 700 字）

```text
━━━━━━━━━━━━━━━━━━━━
  Meteor-ZH · Meteor Client 全界面中文汉化
━━━━━━━━━━━━━━━━━━━━

【是什么】
给 Minecraft 26.1 / 1.21.11 + Fabric + Meteor Client 用的汉化 addon。
装上之后 Meteor 的界面基本全中文，不用改配置文件，不用手动触发。
两个游戏版本各有一个 jar，源码共用。

【为什么不用现成的】
社区里的 Meteor-I18n-Support 只翻了模块名和设置项，问题是：
· GUI 里大量硬编码英文没动：Bind、Modules、Config、Reset、Chat Feedback、Active
· 按键名还是 Left Shift / Mouse Left / F1 这种
· 第三方 addon（AutoElytra、Miku、Lotus 等）完全没覆盖

【这个补了什么】
· 模块名 + 描述      305 个模块（含 addon），170 条带描述
· 设置项名称 + 说明   1174 条，其中 1028 条带说明
· 设置分组标题       129 条（General→通用、Render→渲染、Colors→颜色…）
· GUI 按钮/提示      295 条（Bind→绑定、Apply→应用、Chat Feedback→聊天反馈…）
· 按键名            66 条（Left Shift→左Shift、Space→空格、None→无）
· 顶部标签页         Modules→模块、Config→配置、Friends→好友…
· HUD 元素名与分组
· 第三方插件描述句   63 条

已经自带中文的插件（比如 Miku、Lotus 的中文模块）原样保留，不会被二次翻译。

【新装 addon 怎么办】
不需要等我更新。
插件启动时遍历 Meteor 已加载的全部附属模组，词典命不中的标识符
会用内置的 795 词词表逐词合成中文：

  chunk-render-distance   → 区块渲染距离
  auto-totem-refill       → 自动图腾补充
  potion-refill-threshold → 药水补充阈值
  world-origin            → 世界原点

合成不出来的保留英文，不会乱翻。

【安装】
1. 按游戏版本选 jar，放进 .minecraft/mods/
   · Minecraft 26.1     → meteor-zh-1.5.2-mc26.1.jar
   · Minecraft 1.21.11  → meteor-zh-1.4.2.jar
   （PCL 版本隔离的话是 PCL 目录/minecraft/versions/<版本>/mods/）
2. 建议删掉旧的 Meteor-I18n-Support-*.jar（共存不崩，但功能重复）
3. 启动就完事 —— 1.5.2 起插件会自动改用 Minecraft 原版字体渲染，中文不会再变成空白；
   万一界面中文是空白，聊天栏敲 .zh font 重新检测即可
3. 启动游戏，完事

要求：
· Minecraft 26.1    → Fabric Loader ≥ 0.20.1，Java 25，Meteor 26.1.x
· Minecraft 1.21.11 → Fabric Loader ≥ 0.16.0，Java 21，Meteor 1.21.11
仅客户端，不碰服务端。

【命令】
.zh         手动重新翻译一次
.zh reload  重新读词典
.zh info    看词典条目数

【下载】
群文件：meteor-zh-1.5.2-mc26.1.jar（MC 26.1） / meteor-zh-1.4.2.jar（MC 1.21.11）
GitHub：https://github.com/woo4005/meteor-zh/releases
源码：https://github.com/woo4005/meteor-zh
反馈：https://github.com/woo4005/meteor-zh/issues
（GitHub 打不开的话直接用群文件，反馈也可以群里说）

【许可】
GPL-3.0。免费使用、修改、二次分发都行；
如果你改了再发出去，按 GPL 要求同样开源就行。

作者：woo4005
开发过程有 DeepSeek V4.1 flash 1017 协助
━━━━━━━━━━━━━━━━━━━━
```

---

## 三、一句话版（聊天里随口提）

```text
Meteor 我做了个全界面汉化插件，模块名/设置项/GUI 按钮/按键名全中文，
装上进游戏自动翻，重启也不会退回去，新装的 addon 也能自动识别。
群文件里有，GitHub 上开源：https://github.com/woo4005/meteor-zh
```

---

## 四、发布建议

**先传群文件。** 这条最重要——国内打不开 GitHub 的人很多（我自己这次就是 DNS 解析问题折腾了半天）。
顺序建议：

1. 先把 `meteor-zh-1.4.2.jar` 传到群文件，文件名别改
2. 发「群聊短版」
3. 有人问细节，再贴「完整版」或直接给群公告
4. GitHub 链接放最后，作为"想追更新/提问题"的入口

**可能被问到的问题，先准备答案：**

| 问 | 答 |
|---|---|
| 会和 I18n 冲突吗？ | 不冲突，重复翻译是幂等的，但建议只留一个 |
| 会崩服吗？ | 纯客户端 addon，服务端不需要装 |
| 支持 1.20 吗？ | 只做了 1.21.11，其他版本没测 |
| 能翻 Lotus/Miku 吗？ | 它们本身有中文，原样保留；Miku 新增的英文条目会尽量翻 |
| 怎么改翻译？ | 改 `src/main/resources/assets/meteorzh/lang/zh.json` 重新构建，或直接提 issue |
| 收费吗？ | 免费开源，GPL-3.0 |
