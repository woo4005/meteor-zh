# Meteor-ZH 外部词典来源说明

本目录下的 `zh_external_entries.json` 与 `zh_external_words.json` 是从其它 Meteor 汉化
开源项目收集、清洗、去重后得到的增量词条。**本项目自有词条优先，任何外部词条都不会覆盖
`src/main/resources/assets/meteorzh/lang/zh.json` 中已有的键。**

- 采集脚本：`%TEMP%\mzh_dict\build.py`（一次性工具，未纳入仓库）
- 采集时间：2026-10-28
- 采用策略：同名键已存在 → 丢弃；键的大小写/空格/下划线做 kebab 归一化后再比对，
  归一化形式与本项目 `zh.json` 的键风格一致（小写 kebab，如 `Line Color` → `line-color`）
- 输出格式：UTF-8 无 BOM、JSON `indent=1`、键排序

---

## 一、来源仓库

全部通过 `https://api.github.com` 的 `git/trees/<branch>?recursive=1` + `git/blobs/<sha>`
获取原始文件（`contents` API 对 >1 MB 文件返回空内容）。

| # | 仓库 | 分支 | 许可证 | 词典文件 | 拉取条目数 | 最终采用 |
|---|------|------|--------|----------|-----------|---------|
| 1 | [xingke0/meteor_chinese](https://github.com/xingke0/meteor_chinese) | `master` | **GPL-3.0** | `src/main/resources/assets/meteor-translation-addon/lang/{zh_cn,en_us}.json` | 10235 | **1536** |
| 2 | [Nippaku-Zanmu/meteor-translation-addon](https://github.com/Nippaku-Zanmu/meteor-translation-addon) | `master` | **GPL-3.0** | 同上 | 2912 | **18** |
| 3 | [dingzhen-vape/Meteor-I18n-Support-plugin](https://github.com/dingzhen-vape/Meteor-I18n-Support-plugin) | `master` | **GPL-3.0** | `src/main/resources/assets/yalu/lang/{zh_cn,en_us}.json` | 3361 | **166** |
| 4 | [EnderUnion/meteor-zh-cn-addon](https://github.com/EnderUnion/meteor-zh-cn-addon) | `feature/1.21.11` | **GPL-3.0** | 与 #1 同路径 | 10260 | **0** |
| 5 | [ra1nyxin/MeteorTranslation](https://github.com/ra1nyxin/MeteorTranslation) | `main` | **无许可证文件** | 仅 `README.md`（Markdown 表格） | — | **0（跳过）** |

### 各来源说明

1. **xingke0/meteor_chinese**（GPL-3.0）
   - Nippaku 项目的分支衍生物，键格式 `meteor.<addon>.<category>.<module>[.setting.<group>.<name>]`。
   - `zh_cn.json` 是超集（含 18 个第三方 addon 的翻译），`en_us.json` 只覆盖核心
     `meteor_client` 命名空间的约 2844 个键；addon 键没有对应的英文字面，模块 id 由
     键中的 baseFormat 形式反推（`_` → `-`）。
   - 是本批增量的主力来源。
2. **Nippaku-Zanmu/meteor-translation-addon**（GPL-3.0）
   - 原始项目。几乎只含核心 Meteor 的翻译，键总是带显式 `.name` / `.description` 后缀。
   - 与 #1 高度重叠，去重后仅贡献 18 条本项目此前缺失的核心条目。
3. **dingzhen-vape/Meteor-I18n-Support-plugin**（GPL-3.0）
   - 键格式 `Module.Meteor.<id>` / `Setting.Meteor.<id>`（`.Description` 为描述），
     另有 `Module.Meteor+.*`（Meteor+ 附属模组）与带 `+` 后缀的 id（`timer+`、`speed+`）。
   - 采用 166 条，主要是 Meteor+ / 其它 addon 的模块名与少量 Baritone 相关设置（已剔除
     439 条 camelCase 的 Baritone 设置 —— 那些不是 Meteor 键）。
4. **EnderUnion/meteor-zh-cn-addon**（GPL-3.0）
   - xingke0 的复刻；`feature/1.21.11` 比 xingke0 多 25 个键，其余内容逐字节相同。
   - 因 xingke0 优先级更高且内容完全覆盖，最终采用 0 条（保留在流水线中作为兜底）。
   - 其余分支（`master`、`enderphantomwing/1.21.6`、`enderphantomwing/1.21.10`、
     `1.21-1.21.4`）的 `zh_cn.json` 与 xingke0 `master` 的 SHA-256 完全一致，未重复采集。
5. **ra1nyxin/MeteorTranslation**（**无许可证**）
   - 仓库内没有任何 LICENSE 文件，只有一份 README 的 Markdown 表格
     （`| **[module-id]** | **中文标题**：描述 |`，约 200 行）。
   - 无许可证即默认保留所有权利（All rights reserved），**不能并入 GPL-3.0 项目**，故整仓跳过。

---

## 二、许可证兼容性

本项目为 **GPL-3.0**。

| 来源 | 许可证 | 与 GPL-3.0 兼容 | 处理 |
|------|--------|-----------------|------|
| xingke0/meteor_chinese | GPL-3.0 | ✅ 兼容（同协议） | 采用 |
| Nippaku-Zanmu/meteor-translation-addon | GPL-3.0 | ✅ 兼容（同协议） | 采用 |
| dingzhen-vape/Meteor-I18n-Support-plugin | GPL-3.0 | ✅ 兼容（同协议） | 采用 |
| EnderUnion/meteor-zh-cn-addon | GPL-3.0 | ✅ 兼容（同协议） | 采用（0 条实际增量） |
| ra1nyxin/MeteorTranslation | 无 | ❌ 不兼容 | 不采用 |

> ⚠️ **关于 NOTICE 的一处过时表述**：仓库 `NOTICE` 中写明"本项目的词典有 2454 条取自
> `Meteor-I18n-Support v1.0.2`（作者 yalu），该词典以 CC0 1.0 发布"。但
> `dingzhen-vape/Meteor-I18n-Support-plugin` 当前仓库的 `LICENSE` 文件已是 **GPL-3.0**
> 全文，并非 CC0。GPL-3.0 → GPL-3.0 仍然完全兼容，采用无法律问题，但建议把 NOTICE 里
> 的 CC0 表述更正为 GPL-3.0，避免许可证声明与实际不符。

建议在 NOTICE 中追加一段（外部词条来源声明）：

```
本项目的部分词条来自以下 GPL-3.0 开源项目的翻译成果：
  - xingke0/meteor_chinese (GPL-3.0)
  - Nippaku-Zanmu/meteor-translation-addon (GPL-3.0)
  - dingzhen-vape/Meteor-I18n-Support-plugin (GPL-3.0)
  - EnderUnion/meteor-zh-cn-addon (GPL-3.0)
```

---

## 三、清洗规则与丢弃统计

### 通用清洗（`cleanup()`）

丢弃：空值、含 U+FFFD 替换字符、UTF-8 乱码特征（`ï¿½`/`ã€`/`â€`）、不含中文、
占位符（`undefined`/`null`/`TODO`/`待翻译`/`未翻译`）、明显机翻否定式（`^否[^则]`，
例如「否坠落伤害」）、重复标点（`的的`/`了了`/`，。`/`。。`）、元文本
（「翻译成」「汉化」「词典」「你的语言」「彗星端」）、超长（>400 字符）、纯符号。

### 解析期丢弃（按来源）

| 来源 | 拉取 | 丢弃原因 |
|------|------|----------|
| xingke0 | 10235 | camelCase Baritone 键 593、id 含非法字符（`/`）88、id 非法起始 44、键解析失败 7、自身插件键 10、空值 21、无中文 7、id 词数过多 8 |
| EnderUnion | 10260 | 同上（593/88/44/7/10/21/7/8），内容与 xingke0 重合 |
| Nippaku | 2912 | 自身插件键 14、无中文 140、空值 24、重复标点 2 |
| yalu (dingzhen-vape) | 3361 | camelCase Baritone 设置 439、空值 45、无中文 48、id 含中文 2、非 Meteor 命名空间 2 |

### 合并期丢弃（四来源合并去重后）

| 原因 | 条数 |
|------|------|
| 本项目已有同名键（设置） | 13051 |
| 本项目已有同名键（模块） | 1391 |
| id 含显示用字符 `# * : № / \` | 148 |
| 同 id 同时被当作 module 与 setting（按 module 处理） | 1 |
| 无可用标题 | 7 |
| 描述：本项目已有同一英文原句 | 1298（去重后唯一英文句） |
| 描述：英文原句在源中未翻译 | 45 |
| 描述：源值是元文本 | 1 |
| 词根：非 `^[a-z][a-z0-9]{1,39}$` 或属 WordTranslator 跳过词 | 2 |

### 关于 descriptions 段为空

三个 xingke 系来源共提供 **1344 个唯一英文原句**的描述，其中 **1298 个本项目
`zh.json` 已经收录**（早期一轮 `scripts/merge_external.py` 已把它们并入了
`src/main/resources/assets/meteorzh/lang/zh.json`，该文件 descriptions 由 63 条增至 1357 条）；
其余 **46 个唯一原句在来源里仍是英文未翻译**（如 `The tick delay between placing blocks.`），
另有 1 条为元文本（「把彗星端模块名称翻译成你的语言」）。因此本文件的 `descriptions`
段没有剩余增量为空 —— 这不是漏采。

---

## 四、成品统计

| 文件 | 段 | 条数 |
|------|----|------|
| `zh_external_entries.json` | `modules` | 330 |
| | `settings` | 1390 |
| | （合计条目；含 desc 的分别为 326 / 1267） | 1720 |
| `zh_external_words.json` | 词根映射 | 57 |

词根来源：单一 token 标识符直接取标题 21 条；多 token 标识符的「已知前缀/后缀 + 未知
中间段」对齐挖掘、≥3 次投票 38 条（另有 2 条在最终过滤中被剔除）。
57 条全部满足 `^[a-z][a-z0-9]{1,39}$`，可被 `scripts/merge_external.py` 的
`plausible_word` 直接接受。

### 与主词典合并时的注意事项

`scripts/merge_external.py` 目前对 `modules` / `settings` 只接受 **`dict/raw_261.json`
（Meteor 26.1 真实 id 白名单）里存在的键**。本文件中的条目是"本项目主词典尚未收录"的
增量，绝大多数是第三方 addon 与其它 Meteor 版本的 id，**通过 26.1 白名单的比例为 0**
（核心 26.1 词条本项目已全部具备）。若希望这批词条生效，需要：
- 放宽 `merge_external.py` 的白名单（这些 id 来自其它汉化 addon 自身的键，是可信的
  Meteor/addon 标识符），或
- 人工抽检后把 `modules` / `settings` 直接并入 `zh.json`。

`zh_external_words.json` 不受白名单限制，可直接并入 `words.json`。
