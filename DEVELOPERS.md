# 开发者档案 · Meteor-ZH

> 这份文档回答三个问题：**这个项目是谁做的、AI 具体做了什么、后续维护者需要注意什么。**
>
> 之所以要写得这么细，是因为社区评审里有一条很中肯的批评：README 上那句「DeepSeek 协助完成」
> 太轻了——它没法让接手的人判断“哪些代码可信、哪些地方可能埋着坑”。而实际情况是：
> **本项目的全部代码、脚本与文档都由 AI 生成，人类负责提需求、提供环境、验收和纠正方向。**
> 这种分工如果不写清楚，后来者会误以为是人类写的，从而高估或低估某些部分。

---

## 1. 项目是怎么诞生的

2026 年 10 月 26 日，作者 `woo4005` 在 DeepSeek Harness 里贴了两张截图：

1. Meteor 的「高速清路者（Highway Clearer）」设置页 —— 模块名是中文，但 `General`、`Filter`、
   `Bind`、`Toggle on bind release`、`Chat Feedback`、`Active` 全是英文
2. Miku 附属模组的模块列表 —— Miku 自带中文模块，Meteor 本体和 AutoElytra 还是英文

需求原话（意思）：*写一个汉化插件，装上之后在 Meteor 配置界面点一下就能翻译，重启后依然正常；
功能里的设置栏也要翻译，Bind 这种也能翻；参考已有的 I18n；环境需要什么你自己配，最后给我成品。*

没有提供任何代码、没有指定技术方案，只给了两张截图和一个模糊的产品目标。

---

## 2. 人机分工

### 由人（woo4005）负责的部分

| 事项 | 说明 |
|---|---|
| 需求定义 | 「装完就能用」「重启不失效」「新装插件也要适配」这些验收标准是人定的 |
| 真实环境 | 提供 PCL 启动器配置、游戏目录、mods 清单、两张界面截图 |
| 环境授权 | 允许 AI 在本机安装/编译/写入游戏目录 |
| 验收与纠偏 | 逐轮看图反馈翻错的地方，提出「作者改成 dsh-woo4005」「加 DeepSeek 署名」「上传 GitHub」等要求 |
| GitHub 账号 | 用手机完成 OAuth 设备授权；后续自行修改了账号名 |
| 游戏内实测 | 在多人服务器里实际游玩、观察翻译效果（AI 无法启动第二个游戏实例验证） |
| 最终发布决定 | 决定什么时候发、发到哪里、发什么文案 |

### 由 AI（DeepSeek V4.1 flash 1017，在 DeepSeek Harness 中）负责的部分

**代码 100% 由 AI 编写**，包括：

- 全部 6 个 Java 源文件（约 700 行）：入口、词典容器、词法引擎、反射引擎、命令、Mixin
- 全部 16 个 Python 脚本（约 3000 行）：词典装配、短语提取、词表生成、构建、重映射、打包、验证、发布
- 全部构建工具链的设计（离线 javac + ASM ClassRemapper，因为本机访问不到 Maven Central）
- 全部文档（README、CHANGELOG、CONTRIBUTING、本文件、Issue/PR 模板、GitHub Actions）
- 应用图标（手写 PNG 编码，没有用图形库）
- GitHub 发布流程（含自实现的裸 socket HTTPS 客户端，绕开 DNS 故障）

**技术方案由 AI 选择并论证**，包括反射 vs Mixin 的取舍、词典的数据结构、词法兜底引擎的算法。

**翻译由 AI 完成**，包括 2454 条 Meteor 本体词条的继承整理、242 条 GUI 短语、66 条按键名、
96 个第三方 addon 名称、22 条描述句、795 个词元。

---

## 3. AI 工作明细（按阶段）

### 阶段 0 · 环境侦察（约 20 分钟，30+ 次工具调用）

没有现成工程，需要先把环境摸清楚：

- 用 `Get-ChildItem` 遍历磁盘，找到真实游戏目录：`E:\pcl\.minecraft\versions\1.21.11-Fabric 0.19.3\`
  （注意 `.minecraft\versions` 是空的——PCL 开了版本隔离）
- 盘点 `mods/` 里 30+ 个 jar，识别出关键的：`meteor-client-1.21.11-82.jar`、
  `meteor-miku-1.21.11-11.0.0.jar`、`Meteor-I18n-Support-1.21.11_to_26.1.jar`、
  `autoelytra-1.21.11-1.2.jar`、`xiaohe66-meteor-lotus-17.2-1.21.11.jar`
- 找到可用的 JDK：`.minecraft\runtime\java-runtime-delta`（JDK 21）——系统 PATH 里没有 Java
- 确认 Meteor 配置目录 `meteor-client/` 下已有 `modules.nbt`（61 KB，说明用户已配置过）

### 阶段 1 · 逆向参考实现

用户说「可以参考 I18n」。于是把 `Meteor-I18n-Support` 的 jar 拆开：

- `fabric.mod.json` → mod id `addon-template`，entrypoint `com.yalu.addon.TranslateAddon`
- 用 `javap -p -c` 反编译 `Translator.class`，看出它读 `assets/yalu/lang/*.json`，
  未命中的 key 会**写回磁盘** `lang.json`（这是个副作用，本项目没有沿用）
- `ModuleMixin` 用 `@Unique` 声明 `public String title` 与 `Module` 的字段合并，
  在构造器 TAIL 注入改字段
- 词典有 2454 条，key 规则 `Module.Meteor.<name>` / `Setting.Meteor.<name>`
- **关键发现**：它的 LICENSE 是 **CC0 1.0**，所以这些词条可以合法复用（见 [NOTICE](NOTICE)）

同时读 Meteor 源码：`projects/_refs/meteor-client-1.21.11/` 下有完整 958 个 `.java` 文件。
逐个确认 `Module`、`Setting`、`SettingGroup`、`Category`、`GuiRenderer` 的字段与序列化路径。

### 阶段 2 · 架构设计（关键技术决策见第 5 节）

三条结论：

1. **用反射改字段，不用 Mixin 改字段** —— JDK 21 允许对非 static final 实例字段
   `setAccessible + set`，先写了一个 20 行的测试类验证（输出 `REFLECT_OK`）才定案
2. **Mixin 只用来拦渲染入口** —— GUI 硬编码英文改字段改不到，但全部经过 `GuiRenderer#text`
3. **哪些字段绝对不能改** —— 通读 `Settings.toTag/fromTag` 后发现 `SettingGroup.name` 是
   反序列化的键，改了会让用户所有已保存的分组配置失配。写进代码注释，也写进 README

### 阶段 3 · 实现（约 700 行 Java）

| 文件 | 职责 |
|---|---|
| `MeteorZh.java` | `MeteorAddon` 入口，订阅 `TickEvent.Post`，首次 tick 执行翻译后自动退订 |
| `ZhDict.java` | 读 jar 内 `zh.json`，7 张 HashMap，含模块/设置交叉回退查找 |
| `WordTranslator.java` | 词法兜底：kebab 拆词 → 查 795 词表 → 拼中文；全不命中返回 `null` |
| `Translator.java` | 反射引擎：8 个字段句柄 + `replace()`，统计改动数 |
| `ZhCommand.java` | `.zh` / `.zh reload` / `.zh info` |
| `mixin/GuiRendererMixin.java` | `@ModifyVariable` 改写 `text()` 的第一个 String 参数 |

编译期踩的坑（都记在 `scripts/build.py` 的注释里）：

- 230 项 classpath（21 KB）塞进 javac argfile 会让 javac **找不到任何包** → 必须走环境变量 `CLASSPATH`
- argfile 里的 Windows 绝对路径反斜杠会被当转义符 → 改用相对路径 + 正斜杠
- `SettingGroup.settings` 是 package-private → 只能用 `for (Setting<?> s : group)` 迭代
- `Commands` 的包名是 `meteordevelopment.meteorclient.commands`，不是 `systems.commands`

### 阶段 4 · 词典工程（这是最耗时的部分）

词典不是手工翻的，是用脚本流水线生成的：

| 来源 | 处理方式 | 产出 |
|---|---|---|
| I18n 的 2454 条 | 转换 key 规则，剔除 `zh == en` 的未翻译项 | 267 模块 / 1136 设置 |
| Meteor 源码 | 正则扫 `theme.label("...")` / `section(...)` / `button(...)` | 242 条 GUI 短语 |
| `Utils.getKeyName/getButtonName` 的反编译 | `javap -c` 抓 lookupswitch 里的字符串常量 | 66 条按键名 |
| `Tabs` 构造器 | 源码 grep `super("...")` | 7 条标签页 |
| 第三方 jar | 自写 class 常量池解析器，正则识别 kebab 标识符与描述句 | 96 名称 + 22 描述 |

**词法引擎迭代了 4 轮**，每轮都用现有 1388 条词典做回归评估：

| 轮次 | 词元数 | 命中率 |
|---|---|---|
| 初版 | 539 | 68.9% |
| 补一轮 | 647 | 76.4% |
| 补二轮 | 763 | 83.5% |
| 补三轮 | 795 | 83.6% |

第 4 轮收益趋近于零，停在这里。

### 阶段 5 · 构建工具链

本机 `Maven Central` 域名解析失败，装不了 Gradle 依赖。于是自建离线工具链：

```
javac --release 21 + CLASSPATH 环境变量
    ↓
addon-mojmap.jar（mojmap 命名）
    ↓
RemapJar.java（ASM ClassRemapper，用 104403 行 mappings）
    ↓
addon-intermediary.jar（游戏能加载的命名）
    ↓
dist/meteor-zh-x.y.z.jar
```

`RemapJar` 和 mappings 文件是从上一个 addon 项目（`miku-villager-mover`）复用的——
这也是为什么 `scripts/build.py` 里有指向别的项目的路径，README 里如实说明了这一点。

### 阶段 6 · 发布与分发

GitHub 发布遇到两个本机网络问题，都是 AI 自己绕过去的：

1. **DNS 间歇性失败**，`github.com` 常解析到连不通的 IP → 自写裸 socket + SSL 客户端，
   连接用 IP、SNI 用正确主机名（TLS 证书校验照常通过）→ `scripts/github_publish_ip.py`
2. **OAuth 设备流轮询 404** → 定位到是 `Content-Type` 要求 `application/x-www-form-urlencoded`
   而脚本发了 JSON → 修复后成功

用户用手机扫码完成授权，AI 完成后续建库、上传 71 个文件、建 Release、上传 asset。

### 阶段 7 · 文档

README、CHANGELOG、CONTRIBUTING、NOTICE、SECURITY、Issue/PR 模板、GitHub Actions、
本文件，以及一份 22 页的项目介绍 PPT（`dist/Meteor-ZH-项目介绍.pptx`）。

### 阶段 8 · Minecraft 26.1 适配（2026-10-28）

用户装好了 26.1 实例并自己先测通了界面，剩下的交给 AI。这一段最能说明「AI 干活的方式」——
**结论先给，坑在下面**：

**技术结论：26.1 相对 1.21.11，源码只需要改一个方法的签名。**

AI 把 Meteor 26.1.2 的 1347 个 class 逐个用 `javap` 和 1.21.11 对比，
确认 `MeteorAddon`、`Module`、`Setting`、`SettingGroup`、`Settings`、`Category`、
`GuiRenderer`、`Tabs`、`Hud`、`HudElementInfo`、`Commands`、`Modules` 这十二个类
**字段名、字段修饰符、方法签名全部一致**。唯一的破坏性变更：

- `Command#build` 的参数从 `LiteralArgumentBuilder<SharedSuggestionProvider>`（服务端类型）
  变成 `LiteralArgumentBuilder<ClientSuggestionProvider>`（客户端类型）。
  泛型擦除后两者对 JVM 是同一个签名，所以把 `ZhCommand.build()` 写成**原始类型**
  `LiteralArgumentBuilder` + `@SuppressWarnings("rawtypes")`，一份源码同时编译两个版本。

**构建环境的坑（比代码多得多）：**

1. **MC 26.x 起游戏不再混淆**，整条 mojmap → intermediary 的 remap 流程直接删掉。
   这不是「适配成功」，而是「以前必须做的步骤现在不需要了」。
2. **Meteor 把 orbit / gson / fabric-api-base 等 15 个依赖以嵌套 jar 放在自己 jar 的
   `META-INF/jars/` 下**。`javac` 读不了 jar 里的 jar，必须先把它们解包到磁盘再进 classpath，
   否则报 `找不到符号: meteordevelopment.orbit.EventHandler`。
3. **PCL 的 version json 里 `fabric-loader` 和 `sponge-mixin` 没有 `downloads.artifact` 字段**，
   只有 Maven 坐标，得自己按 `group/artifact/version/artifact-version.jar` 拼路径。
   另有 5 个库（`java-objc-bridge`、netty 的 linux/osx native）本机根本不存在，要能跳过。
4. **必须用 JDK 25 编译**（产出 class major version 69），Mixin 的 `compatibilityLevel`
   也要从 `JAVA_21` 提到 `JAVA_25`。
5. `scripts/build.py` 在编译失败时会因打印非 ASCII 错误信息触发
   `UnicodeEncodeError: 'gbk'`，把真正的错误盖住——加了 stdout/stderr 的 UTF-8 重定向才好查。

**词典是怎么补到 100% 的：**

AI 写了个脚本扫描 26.1 sources jar 里全部 196 个模块源文件，用正则抽出
`super(Categories.X, "name", "description")`、`.name("x")` + `.description("y")`、
`createGroup("...")`，得到本体 169 模块 / 968 设置项 / 92 分组的**完整清单**，
再和已有词典比对——缺口只有 4 个模块 + 34 个设置名 + 38 条说明，补完后经脚本逐条核对：
**标题 0 缺失、说明 0 缺失、分组 0 缺失**。

然后并入社区四个 GPL-3.0 汉化项目（xingke0、Nippaku-Zanmu、dingzhen-vape、EnderUnion）
的译名。这里 AI 做了一次**主动裁剪**：外部词典里大量条目是本地根本没装的 addon
（`advanceditemesp`、`2b2t-queue` 之类），收进词典对用户零收益、还要背质量风险；
而 Meteor 的所有描述文字都是按**英文原句**查表的，这才是收益最大且最安全的一项。
所以最终只收描述句（+1357 条）、只收能对上已知原始英文说明的标识符、词表全收（+274 词根）。

**验证方式：** 写 `scripts/verify_261.py`，用 26.1 实例的真实 classpath 加载插件 jar，
不启动游戏就检查词典能读、`Translator.init()` 的 9 个反射字段在 26.1 的类里全部存在
（`NoSuchFieldException` 会在这里暴露）、若干查找结果正确。这一步能抓住「字段改名」这类
最致命的兼容性问题。真机验收仍然交给用户。

---

## 4. AI 没有做到的事（承认局限）

| 事情 | 为什么没做 |
|---|---|
| 在真实客户端里验收翻译效果 | jar 被运行中的进程锁住，无法启动第二个实例；最终由用户自己开游戏看 |
| Gradle 构建的本机验证 | 本机没有 Gradle，且 Maven Central 不可达。Gradle 工程是照着已知可用的配置写的，在 CI 上验证 |
| 逐个小版本验证 Meteor 兼容性 | 只验证了 1.21.11 build 82 这一档 |
| 真实 FPS / 内存峰值数据 | 需要完整客户端 + Spark profiler。README 给的是各步骤本身的微基准，并明确标注了这一点 |
| 100% 翻译覆盖率 | 第三方 addon 的英文描述句无法穷举，靠词法引擎兜底 83.6% |

---

## 5. 关键技术决策记录

### ADR-001 · 反射改字段，而不是 Mixin 改字段

**背景**：要改 `Module.title` 这类 `public final` 字段。
**选项**：① Mixin `@Accessor @Mutable`；② 反射 `setAccessible + set`。
**决定**：②。
**理由**：JDK 21 对非 static final 实例字段允许反射写入（实测通过）；Mixin 方案要处理字段合并
警告（I18n 的日志里就有 `Discarding @Unique public field name` 这种），而且要给每个类写一个
accessor，成本高。反射方案一个 `Field` 句柄就能覆盖所有实例。
**代价**：依赖 JVM 行为，未来 JVM 收紧 final 字段反射会失效（届时降级为只改非 final 字段）。

### ADR-002 · Mixin 只拦 `GuiRenderer#text`，不做 refmap

**背景**：GUI 里的 `"Bind: "` 这类字面量改字段改不到。
**决定**：`@ModifyVariable` 注入 `GuiRenderer.text(String, double, double, Color, boolean)`，
`remap = false`。
**理由**：该方法的参数里**没有任何 Minecraft 类型**，描述符在 mojmap 与 intermediary 下完全相同，
不需要 refmap——这省掉了整个 refmap 生成流程。而 Meteor 的 `GuiRenderer` 类名本身也不随映射变化。
**代价**：一旦 Meteor 改了这个方法的签名，Mixin 失效（已用 `required = false` 保证不崩游戏）。

### ADR-003 · `SettingGroup.name` 完全不改，分组标题靠渲染层映射

**背景**：`General`、`Render` 这类设置分组标题要显示成「通用」「渲染」。`SettingGroup` 只有一个
`public final String name`，没有独立的显示字段。
**选项**：① 直接反射改 `name`；② 不改字段，在 GUI 渲染时把 `name` 映射成中文。
**决定**：② **完全不改 `name`**。
**理由**：读 `Settings.toTag()` / `Settings.fromTag()` 后发现，分组是按 `name` 序列化和反查的
（`getGroup(groupTag.getString("name", ""))`）。改 `name` 会让用户**所有已保存的分组设置失配**，
表现为“自定义过的设置全部回到默认值”——而且是静默发生的，非常难排查。
实现上：分组名同时写进 `groups` 表与 `ui` 表，Mixin 拦截 `GuiRenderer#text` 时一并命中。
**代价**：`.nbt` 里看到的仍是英文分组名；GUI 层多一次查表。
**后果**：这条约束写进了 `Translator.java` 的注释、README 的「明确不改的字段」表，以及
CONTRIBUTING 的“不要做的事”。**任何 PR 都不应该改动这个字段。**

### ADR-004 · 词法兜底而不是无穷扩词典

**背景**：用户要求「新装插件也能自动翻译」。手工给每个 addon 写词条不可持续。
**决定**：内置词表逐词合成，全不命中返回 `null`。
**理由**：`null` 约定把「无法翻译」和「已经是中文」统一处理，避免了把中文标识符二次拉丁化。
**代价**：组合词可能生硬（`chest-stealer-percent` → `箱子 StealerPercent`），接受了。

### ADR-005 · 两条游戏版本线各自独立编号，源码共用

**背景**：26.1 与 1.21.11 的 Meteor API 几乎一致，但编译目标（Java 25 / Java 21）、
mapping（无混淆 / mojmap）、产物文件名都不同。用户明确要求：1.4.0 继续负责 1.21.11，
1.5.0 专门给 26.1。
**决定**：同一份 `src/`，两套构建脚本，两个版本号各自递增（1.21.11 → 1.4.x，26.1 → 1.5.x），
词典共享。
**理由**：如果强行统一版本号，1.21.11 用户会被推着升级一个自己用不上的版本；
反过来，26.1 的修复也不该让 1.21.11 的用户重新下载。独立编号让两条线的节奏互不牵连。
**代价**：每次改词典要重建两个 jar、发两次说明，维护成本翻倍。可接受——词典是纯数据，
两个 jar 的构建只差几十秒。

---

## 6. 给后续维护者的建议

1. **改 `src/main/java` 之前先看 `Translator.java` 的注释**，那里写了每个字段为什么能改/不能改。
2. **不要改 `SettingGroup.name`**，理由见 ADR-003，这会静默破坏所有用户的配置。
3. **源码是 mojmap 命名**。如果你习惯 yarn，注意 `SharedSuggestionProvider` ↔ `CommandSource`、
   `Component` ↔ `Text` 的对应关系，改错了编译不过。
4. **词典改完一定要跑 `build_dict.py`**，`zh.json` 是生成物，直接改它会在下次构建时被覆盖。
5. **`dist/` 里的 jar 是构建产物但需要提交**——因为要做分发，且 GitHub Release 的 asset 从这里来。
6. **构建脚本里有一条硬编码的 JDK 路径**（`scripts/build.py` 与 `scripts/build_261.py` 的 `JDK` 常量），换机器要改。
7. **两条线要一起改**：动了 `src/` 或词典，先 `build.py` 出 1.4.x 的 jar，再 `build_261.py` 出 1.5.x 的 jar。
   `ZhCommand.build()` 的原始类型签名是两条线共存的唯一原因，不要「顺手」把它改回带泛型的版本。

---

## 7. 一句话总结

> 这是一个**人类主导、AI 执行**的项目：人定方向和验收标准，AI 写了全部代码、全部脚本、全部文档。
> 如果这个项目要长期维护下去，接手的人最好记住上面第 6 节那七条——
> 尤其是「`SettingGroup.name` 不能改」「源码是 mojmap」「两条线要一起重建」。

---

最后更新：2026-10-28 · 对应版本 **1.4.0（Minecraft 1.21.11 线）** 与 **1.5.0（Minecraft 26.1 线）**

> 两条线共用同一份 `src/`，但版本号各自独立：1.21.11 线发 1.4.x，26.1 线发 1.5.x。
> 本文描述的是两条线共同的技术实现，差异只在构建脚本（`scripts/build.py` vs `scripts/build_261.py`）。
