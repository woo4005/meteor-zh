# 安全政策 · Meteor-ZH

Meteor-ZH（mod id `meteor-zh`）是 **Minecraft 1.21.11 / 26.1 · Fabric · Meteor Client** 的纯客户端简体中文汉化 addon。

- 仓库：<https://github.com/woo4005/meteor-zh>
- 许可证：GPL-3.0-or-later
- 当前版本：1.5.8（26.1 线）/ 1.4.8（1.21.11 线）

---

## 安全模型

这个模组**会联网**：为了做更新检查。除此之外它只改显示文字。下面把「会做什么、不会做什么」逐条写清楚——上一版这份文档写着「无网络通信、不检查更新」，那是 1.4.0 之前的状态，1.5.3 加入更新器后就已经不成立了，属于文档错误，已在此更正。

### 会做的事

| 行为 | 触发条件 | 说明 |
|---|---|---|
| 访问 GitHub Releases API | 每次启动**最多一次**（`自动检测更新` 默认开启），或玩家手动点「立即检查更新」 | `https://api.github.com/repos/woo4005/meteor-zh/releases?per_page=30`；失败即放弃，不重试 |
| 下载新的 jar | 仅当玩家勾选「自动下载更新」**并且**检测到新版本 | 走 `https://github.com/...` 与 `objects.githubusercontent.com` / `release-assets.githubusercontent.com` |
| 替换 mods 里的 jar | 仅当上面两步成功、**且**校验通过 | 在游戏进程退出后由批处理执行，见下 |
| 写入 `meteor-zh/` 目录 | `.zh dump` 或静默下载 | dump 是玩家主动导出；下载的临时文件落在 `mods/<名字>.download` |
| 关闭 Meteor 的自定义字体 | 启动时（`FontFixer`） | 写入 Meteor 自己的 `config.nbt`（`customFont=false`）；不关掉就显示不出中文，见 README |

### 不会做的事

- **不收集数据**：没有遥测、崩溃上报、使用统计，不生成设备标识，不上报坐标/账号/IP。
- **不改 Meteor 的配置文件**（除了上面那条 `customFont`）：`modules.nbt`、键位、HUD 布局都不动。
- **不动游戏本体或其它的 mod**：只读自己的 jar 资源、只写自己的目录与目标 jar。
- **不在游戏进程内替换正在加载的 jar**：替换由退出后启动的批处理完成；当前会话从不写自己正在用的文件。
- **不执行从网络拿到的代码**：下载的只有 jar 本身，交给 Fabric 下次启动时加载；不下载、不解析、不执行脚本或反射调用远程内容。

### 下载更新的完整性校验（1.5.8 起）

这是本模组唯一的远程代码路径，因此校验做在最前面：

1. **域名白名单**：重定向由客户端自己跟随（最多 3 跳），每一跳都检查主机名必须是 `github.com` /
   `api.github.com` / `objects.githubusercontent.com` / `release-assets.githubusercontent.com` /
   `github-releases.githubusercontent.com`，或它们的子域名。不在白名单直接拒绝（`github.com.evil.example`
   这类后缀欺骗会被拒绝，因为判断是「等于」或「以 `.github.com` 结尾」，不是 `contains`）。
2. **大小必须与 API 给的 `size` 一致**：下载完成后对比字节数，不一致即删除临时文件并报错。
3. **sha256 必须与 API 给的 `digest` 一致**（`sha256:` 前缀会被剥掉、大小写不敏感）。
4. **拿不到 `digest` 就不自动替换**：老版本 GitHub API 或镜像可能不给 digest，此时只把文件下下来，
   提示「为安全起见不会自动替换，请到下载页手动安装」。宁可少一个自动化，也不做没有校验的执行。
5. **替换前备份、失败回滚**：先把旧 jar 改名成 `.bak`，替换失败（重试 60 次后仍失败）会自动改名还原，
   日志写到 `mods/meteor-zh-update.log`；成功则删掉 `.bak`。
6. **不校验就不执行**：以上任一条不满足，本次更新作废，玩家手动到 Releases 下载即可。

> 这套校验防的是「release 资产被替换 / 账号被盗 / 中间人代理」。它**不防**仓库所有者本人发布恶意版本
> ——那属于信任根问题，只能靠你自己看源码（仓库是 GPL-3.0，源码与构建脚本都在）。

理论上它只可能通过下面这类**缺陷**（而不是设计）影响你：

1. 反射访问字段时抛异常，导致游戏崩溃；
2. 词法兜底拼出异常字符串（乱码、超长、空的按钮文字）；
3. 打包脚本误把第三方文件带进 jar；
4. 更新器判断出错，下载了不适用于你游戏版本的 jar（`fabric.mod.json` 的 `depends` 会拦住大部分）。

这些属于普通 Bug，按 [Bug 报告](https://github.com/woo4005/meteor-zh/issues/new?template=bug_report.yml) 提交即可。

---

## 报告安全问题

如果你发现的是**安全**问题（例如越权读写、意外网络请求、校验可绕过、供应链问题），请：

- **首选** GitHub Security Advisory（私密，不会公开细节）：<https://github.com/woo4005/meteor-zh/security/advisories/new>
- 或通过作者 GitHub 主页上的公开联系方式发邮件给维护者：[woo4005](https://github.com/woo4005)
- **不要**开公开 issue，也不要在修复前公开 PoC。

报告里请包含：

- meteor-zh 版本（`/zh info` 或 `.zh info` 的输出）、Minecraft / Fabric Loader / Meteor Client 版本
- 问题描述与影响（能读到什么、改到什么、能造成什么后果）
- 复现步骤 / 最小 PoC
- 相关的 `logs/latest.log` 与 `mods/meteor-zh-update.log` 片段

维护者会先确认问题、评估影响范围，修复版本发布后再公开细节（协调披露）。你会在确认与修复阶段收到回复。

---

## 支持版本

| meteor-zh 版本 | 游戏版本 | 安全支持 |
|---|---|---|
| **1.5.8** | 26.1 / 26.1.1 / 26.1.2 | ✅ 支持 |
| **1.4.8** | 1.21.11 | ✅ 支持 |
| 1.5.0 ～ 1.5.7、1.4.0 ～ 1.4.7 | — | ⚠️ 可用但已知问题较多，建议升级 |
| 1.3.x 及更早 | — | ❌ 不支持 |

受支持的环境：

| 组件 | 26.1 线 | 1.21.11 线 |
|---|---|---|
| Minecraft | 26.1 / 26.1.1 / 26.1.2 | 1.21.11 |
| Fabric Loader | ≥ 0.20.1 | ≥ 0.16.0 |
| Meteor Client | 26.1.2（build 42） | 1.21.11（build 82+） |
| Java | 25 | 21 |
| 端 | 仅客户端（`environment: client`，不要装在服务端） | 同左 |

---

## 不属于安全问题的行为

以下都是设计如此，不用报安全漏洞（可以当普通 Bug / 功能请求提）：

- 更新检查会访问 GitHub（见上表），国内网络下可能长时间无响应后放弃；
- 第三方 addon 的部分设置项仍是英文（词典与词表未覆盖）；
- 设置分组内部名、配置文件里存的键名保持英文（`SettingGroup.name` 参与反序列化，故意不改）；
- 左侧分类的显示名来自 `zh.json` 的 `groups` 表，`Category.name` 本身保持英文（第三方 addon 可能按名字比较）；
- `config.nbt` 里的 `customFont` 被改成 `false`（这是中文能显示的前提，卸载后需要自己改回来）；
- 与 `Meteor-I18n-Support` 共存时语言表现异常（两者功能重复，请只留一个）；
- Minecraft 本身或其它模组导致的崩溃（请附 `latest.log` 判断）。

---

## 供应链说明

- 源码与构建脚本都在本仓库，构建可离线完成（`scripts/build.py` / `scripts/build_261.py`），运行期不写任何配置以外的持久文件。
- Release 附件由仓库脚本生成；产物在打包后有自检（`scripts/_jarcheck.py`：条目齐全、JSON 可解析、`depends` 含 `minecraft`/`java`/`meteor-client`、class 字节码版本正确），不通过就不会上传。
- **构建不完全可复现**：离线脚本依赖本机的 JDK、Minecraft 客户端 jar 与 Meteor 的 jar，且不规范化时间戳，所以同源码两次构建的 jar 字节不一定相同。要核对内容，请对比解包后的 class 与资源，而不是整包 hash。
- 更新器下载的 jar 会做 sha256 校验（见上）；GitHub API 给的 `digest` 缺失时不会自动替换。
- 许可证：**1.4.0 起为 GPL-3.0-or-later**（1.3.1 及更早为 CC0-1.0）。第三方组件与数据归属见 `NOTICE`；`i18n_ref/` 中的 Meteor 本体翻译来自以 CC0 发布的 Meteor-I18n-Support，许可证兼容。
