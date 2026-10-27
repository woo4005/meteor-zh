# 安全政策 · Meteor-ZH

Meteor-ZH（mod id `meteor-zh`）是 **Minecraft 1.21.11 · Fabric · Meteor Client** 的纯客户端简体中文汉化 addon。

- 仓库：<https://github.com/woo4005/meteor-zh>
- 许可证：GPL-3.0-or-later
- 当前版本：1.4.0

---

## 安全模型

本模组的设计目标是"只改显示文字"，因此刻意把权限压到最低：

- **无网络通信**：不发起任何 HTTP / DNS / WebSocket 请求，不检查更新，不上报任何东西。
- **不收集数据**：没有遥测、崩溃上报、使用统计，也不生成标识符。
- **不写入用户配置**：只读取 jar 内的 `assets/meteorzh/lang/*.json`，通过反射修改**内存中**的显示字段。不改 `modules.nbt`、`config.nbt`、键位、HUD 布局；删掉 jar 即完全恢复英文。
- **不加载远程代码**：不下载、不解析、不执行任何外部内容。
- **不新增依赖**：运行期只使用 Minecraft / Fabric / Meteor Client 已提供的类；构建期用到的 ASM remap 工具不会打进成品 jar。

换句话说，它全部"写操作"仅限：反射修改已实例化对象的显示字段（`Module.title` 之类）以及 mixin 在渲染层替换文本。

理论上它只可能通过下面这类**缺陷**（而不是设计）影响你：

1. 反射访问字段时抛异常，导致游戏崩溃；
2. 词表兜底拼出异常字符串（乱码、超长、空的按钮文字）；
3. 打包脚本误把第三方文件带进 jar。

这些属于普通 Bug，按 [Bug 报告](https://github.com/woo4005/meteor-zh/issues/new?template=bug_report.yml) 提交即可。

---

## 报告安全问题

如果你发现的是**安全**问题（例如越权读写、意外网络请求、供应链问题），请：

- **首选** GitHub Security Advisory（私密，不会公开细节）：<https://github.com/woo4005/meteor-zh/security/advisories/new>
- 或通过作者 GitHub 主页上的公开联系方式发邮件给维护者：[woo4005](https://github.com/woo4005)
- **不要**开公开 issue，也不要在修复前公开 PoC。

报告里请包含：

- meteor-zh 版本、Minecraft / Fabric Loader / Meteor Client 版本
- 问题描述与影响（能读到什么、改到什么、能造成什么后果）
- 复现步骤 / 最小 PoC
- 相关的 `logs/latest.log` 片段

维护者会先确认问题、评估影响范围，修复版本发布后再公开细节（协调披露）。你会在确认与修复阶段收到回复。

---

## 支持版本

只维护最新的 **1.x** 版本。

| meteor-zh 版本 | 安全支持 |
|---|---|
| **1.4.x**（最新） | ✅ 支持，发现问题会发补丁版 |
| 1.3.x 及更早 | ❌ 不再支持，请先升级到最新 1.x |
| 其它 / 自行修改的构建 | ❌ 不支持 |

受支持的环境：

| 组件 | 版本 |
|---|---|
| Minecraft | 1.21.11 |
| Fabric Loader | ≥ 0.16.0 |
| Meteor Client | 1.21.11 |
| 端 | 仅客户端（`environment: client`，不要装在服务端） |

---

## 不属于安全问题的行为

以下都是设计如此，不用报安全漏洞（可以当普通 Bug / 功能请求提）：

- 第三方 addon 的部分设置项仍是英文（词典与词表未覆盖）；
- 设置分组内部名、配置文件里存的键名保持英文（`SettingGroup.name` 参与反序列化，故意不改）；
- 与 `Meteor-I18n-Support` 共存时语言表现异常（两者功能重复，请只留一个）；
- Minecraft 本身或其它模组导致的崩溃（请附 `latest.log` 判断）。

---

## 供应链说明

- 源码与构建脚本都在本仓库，构建可离线完成（`scripts/build.py`），不依赖动态下载的二进制。
- Release 附件 `meteor-zh-x.y.z.jar` 由仓库 `scripts/build.py` 生成；如需自行核对，可用同版本源码重新构建后对比内容。
- 许可证：**1.4.0 起为 GPL-3.0-or-later**（1.3.1 及更早为 CC0-1.0）。第三方组件与数据归属见 `NOTICE`；`i18n_ref/` 中的 Meteor 本体翻译来自以 CC0 发布的 Meteor-I18n-Support，许可证兼容。
