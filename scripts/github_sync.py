#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本地 projects/meteor-zh 同步到 GitHub 仓库，并发布 release。

为什么不用 git：本机没有 git，且到 github.com 的 DNS 间歇性失败。
这里复用 github_publish_ip.py 里「SNI 用主机名、连接用 IP」的裸 socket 客户端。

同步方式用 Git Data API（一次提交完成全部改动），而不是逐个 contents PUT：
  1. 取 main 的当前 commit 与 tree
  2. 为每个本地文件建 blob（带本地缓存，重跑不重复上传）
  3. 建一棵新 tree：base_tree = 旧 tree，条目里 sha=null 表示删除
  4. 建 commit 并把 main 指过去
好处是 70 多个文件只产生一次提交，历史干净，删除也能一并表达。

用法：
    python scripts/github_sync.py --dry-run     # 只打印将要做的事
    python scripts/github_sync.py               # 真正同步 + 发 release
"""
import base64
import json
import os
import sys
import time
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import github_publish_ip as ghp  # noqa: E402

ROOT = ghp.ROOT
REPO = "meteor-zh"
#: 本次要发的版本线。1.4.3 = 1.21.11 线。
VERSION = "1.4.6"
#: 另一条线（26.1）的版本号，用来写在 release 正文的下载表里
VERSION_261 = "1.5.6"
#: 兼容旧名字（正文模板里还在用 {ver1211}）
VERSION_1211 = VERSION
BRANCH = "main"

#: 两条构建线的产物（一个 jar 覆盖 26.1 / 26.1.1 / 26.1.2）——见同一个仓库的 dist/ 白名单
JARS_ALL = ["meteor-zh-%s-mc1.21.11.jar" % VERSION_1211, "meteor-zh-%s-mc26.1.jar" % VERSION_261]

#: 本次 release 应附上的 jar：只放属于本版本线的产物。
#: 1.5.0 是 26.1 线，所以只上传 -mc26.1 那个；1.21.11 的 1.4.0 jar 归 v1.4.0 release。
JARS_RELEASE = ["meteor-zh-%s-mc1.21.11.jar" % VERSION]

UPLOAD_IPS = ["20.27.177.119", "140.82.112.9", "140.82.113.9", "140.82.114.9"]
BLOB_CACHE = os.path.join(os.environ.get("TEMP", "."), "meteor_zh_blobs.json")

#: 仓库根目录下的单文件
ROOT_FILES = [
    "README.md", "LICENSE", "CHANGELOG.md", "NOTICE", "CONTRIBUTING.md",
    "SECURITY.md", "DEVELOPERS.md", ".gitignore",
    "build.gradle", "settings.gradle", "gradle.properties", "gradlew", "gradlew.bat",
    # meteoraddons.com 的补充数据（无需审核即可覆盖站点上的描述 / 标签 / 支持版本）
    "meteor-addon-list.json",
]

#: 需要上传的目录及其过滤规则
DIR_SPECS = {
    ".github": {},
    "gradle": {},
    "src": {},
    "scripts": {"skip_dirs": {"__pycache__"}, "skip_ext": {".pyc"}},
    "dict": {},
    "docs": {"only_files": {"qq-group-post.md"}},
    "dist": {"only_files": set(JARS_ALL)},
    # i18n_ref 只保留英文/中文词源记录，反编译出来的 class 与第三方 jar 不上传
    "i18n_ref": {"skip_dirs": {"jar_extract"}, "only_ext": {".json"}},
}

#: 执行位（Linux 上 gradlew 必须可执行）
EXECUTABLE = {"gradlew"}


# --------------------------------------------------------------------------- #
# HTTP：按状态码挑 IP 重试
# --------------------------------------------------------------------------- #
def api_retry(method, path, data=None, token=None, accept=(200, 201),
              timeout=120, attempts=3, quiet=False):
    """发 API 请求。status 不在 accept 里就换下一个 IP 重试。

    必须这么做：某些 GitHub IP 会返回 404/劫持页面而不是真的 API 响应，
    原来的 api() 只取「第一个没抛异常的响应」，于是把假 404 当成了结果。
    """
    headers = {}
    body = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    attempts_log = []
    for attempt in range(attempts):
        for ip in ghp.API_IPS:
            try:
                st, _hs, payload = ghp._once(
                    ip, "api.github.com", method, path, body, headers, timeout)
            except Exception as exc:  # noqa: BLE001
                attempts_log.append("%s EXC %s" % (ip, exc))
                continue

            text = payload.decode("utf-8", "replace")
            if st in accept:
                try:
                    return st, (json.loads(text) if text else None)
                except ValueError:
                    return st, text

            # 4xx（除 404）是确定性业务错误，别再换 IP 浪费请求
            if st in (400, 401, 403, 422):
                print("  api %s %s -> %d (确定失败)" % (method, path, st), flush=True)
                try:
                    return st, json.loads(text)
                except ValueError:
                    return st, text

            attempts_log.append("%s %d %s" % (ip, st, text[:120]))
        time.sleep(1.5)

    if not quiet:
        print("  API 全部 IP 失败 %s %s" % (method, path), flush=True)
        for line in attempts_log[:8]:
            print("    " + line, flush=True)
    raise SystemExit("API 请求失败: %s %s" % (method, path))


# --------------------------------------------------------------------------- #
# 文件清单
# --------------------------------------------------------------------------- #
def collect_local_files(skip_workflows=False):
    """skip_workflows=True 时跳过 .github/workflows/**。

    写这些文件需要 token 带 `workflow` scope；device flow 第一次拿的 token
    只有 `repo`，此时 GitHub 对包含工作流文件的 tree 请求返回 404（不是 403）。
    """
    files = []
    for rel in ROOT_FILES:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            raise SystemExit("缺少必需文件: %s" % rel)
        files.append(rel)

    for sub, spec in DIR_SPECS.items():
        base = os.path.join(ROOT, sub)
        if not os.path.isdir(base):
            continue
        skip_dirs = spec.get("skip_dirs", set())
        skip_ext = spec.get("skip_ext", set())
        only_ext = spec.get("only_ext")
        only_files = spec.get("only_files")
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for fn in filenames:
                if only_files is not None and fn not in only_files:
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext in skip_ext:
                    continue
                if only_ext is not None and ext not in only_ext:
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                if skip_workflows and rel.startswith(".github/workflows/"):
                    continue
                files.append(rel)
    return sorted(set(files))


def remote_tree(token):
    """返回 (main 的 commit sha, tree sha, 文件路径 -> blob sha)。"""
    st, ref = api_retry("GET", "/repos/%s/%s/git/ref/heads/%s" % (ghp.OWNER, REPO, BRANCH),
                        token=token, accept=(200,))
    commit_sha = ref["object"]["sha"]
    st, commit = api_retry("GET", "/repos/%s/%s/git/commits/%s" % (ghp.OWNER, REPO, commit_sha),
                           token=token, accept=(200,))
    tree_sha = commit["tree"]["sha"]
    st, tree = api_retry("GET", "/repos/%s/%s/git/trees/%s?recursive=1" % (ghp.OWNER, REPO, tree_sha),
                         token=token, accept=(200,))
    existing = {}
    for item in tree.get("tree", []):
        if item.get("type") == "blob":
            existing[item["path"]] = item["sha"]
    return commit_sha, tree_sha, existing


def load_blob_cache():
    try:
        with open(BLOB_CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def save_blob_cache(cache):
    try:
        with open(BLOB_CACHE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
    except Exception:  # noqa: BLE001
        pass


def make_blob(token, path, cache):
    full = os.path.join(ROOT, path.replace("/", os.sep))
    size = os.path.getsize(full)
    hit = cache.get(path)
    if hit and hit.get("size") == size and hit.get("sha"):
        return hit["sha"], size, True

    raw = open(full, "rb").read()
    st, resp = api_retry(
        "POST", "/repos/%s/%s/git/blobs" % (ghp.OWNER, REPO),
        data={"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"},
        token=token, accept=(200, 201),
    )
    if not isinstance(resp, dict) or "sha" not in resp:
        raise SystemExit("建 blob 失败 %s: %s %r" % (path, st, resp))
    cache[path] = {"size": size, "sha": resp["sha"]}
    return resp["sha"], size, False


def set_repo_meta(token):
    meta = {
        "description": "Meteor Client（我的世界 Fabric 附属客户端）全界面简体中文汉化：模块名/描述/设置项/分组/按键名/HUD/GUI 硬编码文本，支持第三方 addon 自动适配。GPL-3.0。",
        "homepage": "https://github.com/%s/%s" % (ghp.OWNER, REPO),
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
    }
    st, resp = api_retry("PATCH", "/repos/%s/%s" % (ghp.OWNER, REPO), data=meta, token=token)
    print("repo meta:", st, flush=True)

    topics = ["minecraft", "fabric", "meteor-client", "chinese", "translation",
              "i18n", "addon", "minecraft-mod", "mojmap"]
    st, resp = api_retry("PUT", "/repos/%s/%s/topics" % (ghp.OWNER, REPO),
                         data={"names": topics}, token=token)
    print("topics:", st, (resp or {}).get("names") if isinstance(resp, dict) else resp, flush=True)


def ensure_release(token):
    tag = "v" + VERSION
    st, rel = api_retry("GET", "/repos/%s/%s/releases/tags/%s" % (ghp.OWNER, REPO, tag),
                        token=token, accept=(200, 404))

    body = """Meteor Client 全界面简体中文汉化 v{ver}

## 本版更新（1.4.6 / 1.5.6）

### 新增 `.zh dump`：导出模块与设置清单

玩家装了什么 addon，我这边装不到那么全。所以加了这个命令：执行后会在游戏目录写出
`meteor-zh/dump-<版本>-<时间>.json`，包含**当前所有**模块与设置——包括不在内置词典里的
那些第三方条目：

```json
{
  "addon": "jefff", "category": "Misc", "name": "better-stash-finder",
  "title": "更好的仓库寻找器", "description": "...",
  "translated": true, "inDictionary": true
}
```

`name` 是查表用的英文标识符，`inDictionary: false` 表示这个词还没收录。
把这个文件发给我，就能精准补词条，不用再靠猜。

功能借鉴自 [Nippaku-Zanmu/meteor-translation-addon](https://github.com/Nippaku-Zanmu/meteor-translation-addon)
的 `JsonDump`。

### 26.1 线：一个 jar 同时支持 26.1 / 26.1.1 / 26.1.2

Meteor 官方 26.1 线只发布过 `26.1.2-42` 一个客户端（声明 `minecraft: "~26.1"`），
26.1.1 玩家装的本来就是它。我把两个客户端 jar 逐字节比过：class 集合完全相同（各 10682 个），
只有 **8 个类**有差异（`DetectedVersion`、`SharedConstants`、`Checkbox`+2 内部类、
`AbstractReportScreen`+1 内部类、`ServerGamePacketListenerImpl`），
而 Meteor 的 **211 个 mixin 没有一个**碰这 8 个类。

`scripts/verify_261_cross.py` 把这条结论做成了检查（10 项断言）：用 26.1.1 的客户端 jar
重新编译同一份源码，断言两套 classpath 产出的 class **逐字节相同**。

> 26.1.1 实例里如果 Fabric 报缺少 `meteor-client`，那是没装 Meteor 客户端本人——
> 把 `meteor-client-26.1.2-42.jar` 放进 `mods/` 即可。

### 版本号说明

1.6.0 曾短暂发布，随后确认 26.1.1 与 26.1.2 共用同一个 Meteor 客户端，没必要为「26.1.x 兼容」
单开大版本号，于是把内容并回 **1.5.6** 并删除了 1.6.0。26.1 线继续按 1.5.x 递增。

---

## 上一版（1.4.5 / 1.5.5）：聊天栏消息正文汉化

模块名和设置项早就变成中文了，但聊天栏里的**正文**一直是英文——因为那些消息是用
`ChatUtils.info("Found stash at (highlight)%s(default), (highlight)%s(default).", x, z)`
这样的 Java 字符串模板直接拼出来的，不是 `lang` 文件里的键，`GuiRenderer` 那条渲染路径管不到。

本版把这类消息也接管了，**156 条模板**，覆盖：

- Meteor 本体：通知器、仓库寻找器、命令回显、路径点、好友、配置档案
- 第三方插件：Jefff 的仓库寻找器、Miku 的村民搬运、Baritone 的状态行等

```
改前：[Meteor] [仓库寻找器] Found stash at 5178744, 5296888.
改后：[Meteor] [仓库寻找器] 在 5178744, 5296888 发现仓库。

改前：[Meteor] [通知器] woo4005's pearl landed at 5179005, 128, 5296969 (80.0m away, travelled 0.1m).
改后：[Meteor] [通知器] woo4005 的末影珍珠落在 5179005, 128, 5296969（距离 80.0m，移动 0.1m）。
```

实现上是钩住 `ChatUtils.formatMsg`——所有带文本的消息最后都经过它。这一层拿到的文本参数已经
填好了，所以不能拿模板当 key 查表，而是把每条英文模板编译成整串锚定的正则（`%s` / `%d` / `%.1f`
变成捕获组）再按捕获组拼回中文，`(highlight)` 这类高亮标记原样保留。构建期会硬校验中英模板的
格式符个数与顺序一致，写错了构建直接失败。

调试类输出（`resolveArea:`、`GoalNear{{...}}` 等）**故意不翻**：它们是诊断信息，翻译反而丢细节。

### 顺带修复

- `ChatDict.translate("")` 会抛 `StringIndexOutOfBoundsException`（空消息取首字符），已拦掉。
- 新增 `scripts/verify_chat.py`（9 项断言），用真实填好参数的英文消息验证反查结果。

---

## 上一版（1.4.4 / 1.5.4）：官方译法优先 + 作者信息

### 官方译法优先

Jefff / Lotus 插件作者维护的官方简体中文语言文件与本站译法不一致的条目，本版一律改用官方译法：
`bounce` 弹跳、`scale` 缩放、`yaw` 偏航角。这样用过这两个插件的玩家看到的是熟悉的词。

官方未翻译的（`Mode` / `Shape Mode` / `Notification Mode`）以及在本项目语境下含义不同的
（`ping` 在 Meteor 本体里指网络延迟，官方那份在 Discord 通知模块里指「@提醒」）保留本站译法
——全局设置名无法区分上下文，改成官方词反而会误导 Meteor 本体的使用者。

### 作者信息

`fabric.mod.json` 的 `authors` 加入 **deepseek-ai**（DeepSeek 官方 GitHub 组织），并新增 `contributors`
字段。模组列表里现在显示 `woo4005 / deepseek-ai / DeepSeek V4.1 flash 1017`。

---

## 更早（1.4.3 / 1.5.3）的修复，本版同样包含

### 修复：Minecraft 1.21.11 上被 Fabric 判定「版本不兼容」

旧版的 `fabric.mod.json` 把依赖写成 `meteor-client: >=1.21.11`。Fabric 的版本解析遵循 semver，
而 `1.21.11-86` 是 `1.21.11` 的**预发布版**——semver 规定预发布版小于同号正式版，即
`1.21.11-86 < 1.21.11`，所以这条约束永远不成立，游戏会提示：

> 将 模组 'Meteor Client' (meteor-client) 1.21.11-86 替换为 1.21.11 及以上版本。

本版改成 `>=1.21.11-0`：`1.21.11-86` 既大于 `1.21.11-0`、又小于 `1.21.11`，两个方向都满足。
1.21.11 线从此可以正常加载，不再需要退回 Meteor-I18n-Support。

### 新增：「关于汉化插件」模块与自动更新

Meteor 里多了一个 **汉化** 分类，里面是「关于汉化插件」模块，界面全中文：

| 设置项 | 作用 |
|---|---|
| 显示插件信息 | 一次性开关，列出插件版本、词典规模、词表规模、字体渲染状态、更新状态 |
| 立即检查更新 | 一次性开关，立刻访问一次 GitHub Releases |
| 打开下载页面 | 一次性开关，用系统浏览器打开 Releases 页面 |
| 自动检测更新 | 默认开启。**每次启动只访问一次** GitHub，失败或超时就放弃，不反复重试 |
| 自动下载更新 | 默认关闭。勾选后在后台静默下载对应 jar，**退出游戏时**才替换旧 jar |

检测到新版本时的提示方式：**在游戏世界里走聊天栏**，**在主菜单则弹出右下角的系统提示框**，
两者都带版本号和下载地址。命令行另有 `.zh check` / `.zh about` / `.zh update`。

### 词典：合并 Jefff / Lotus 官方中文语言文件

插件作者维护的官方汉化文件（368 条）已并入词典：18 个模块、142 个设置、138 条说明。
其中 5 条官方译法覆盖了我们原有的译法（`item-frames`、`exp-slot`、`blocks-per-tick`、
`minimum-storage-count`、`storage-blocks`）；官方留英文的几条（`Mode` 等）以及语境不同的
（`ping` 在 Meteor 里指延迟）保留原译。

### 两条线的产物

| 游戏版本 | 下载 | 版本线 | 前置要求 |
|---|---|---|---|
| **Minecraft 26.1 / 26.1.1 / 26.1.2** | `meteor-zh-{ver261}-mc26.1.jar` | **1.5.x** | Fabric Loader ≥ 0.20.1、Java 25、Meteor Client 26.1.x |
| **Minecraft 1.21.11** | `meteor-zh-{ver}-mc1.21.11.jar` | **1.4.x** | Fabric Loader ≥ 0.16.0、Java 21、Meteor Client 1.21.11 |

两个 jar 的 mod id 相同，**分别放进对应实例的 `mods/`**，不要放在同一个实例里。

### 汉化覆盖

| 内容 | 条数 |
|---|---|
| 模块名 | 395 |
| 设置项 | 1444 |
| 设置分组 | 129 |
| GUI 固定文本（Bind / Active / Reset 等） | 295 |
| 英文描述句（模块与设置说明） | 1357 |
| 按键名 | 66 |
| 顶部标签页 | 7 |
| 词法兜底词表 | 1069 |

### 详细说明

- [README.md](https://github.com/{owner}/{repo}/blob/main/README.md)
- [CHANGELOG.md](https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md)
- [DEVELOPERS.md](https://github.com/{owner}/{repo}/blob/main/DEVELOPERS.md)
""".format(ver=VERSION, ver1211=VERSION_1211, ver261=VERSION_261, owner=ghp.OWNER, repo=REPO)

    if st == 200:
        print("release %s 已存在: %s" % (tag, rel.get("html_url")), flush=True)
        # 正文变了就同步过去，免得远端留着上一版的说明
        if rel.get("body") != body:
            api_retry("PATCH", "/repos/%s/%s/releases/%d" % (ghp.OWNER, REPO, rel["id"]),
                      data={"body": body}, token=token, accept=(200,))
            print("release 正文已更新", flush=True)
        return rel

    st, rel = api_retry("POST", "/repos/%s/%s/releases" % (ghp.OWNER, REPO), data={
        "tag_name": tag,
        "target_commitish": BRANCH,
        "name": "meteor-zh v" + VERSION,
        "body": body,
        "draft": False,
        "prerelease": False,
    }, token=token)
    if not isinstance(rel, dict) or "html_url" not in rel:
        raise SystemExit("创建 release 失败: %s %r" % (st, rel))
    print("release created:", rel["html_url"], flush=True)
    return rel



RETIRED_TAG = "v1.5.0"
RETIRED_BODY = """⚠️ 本版已撤回，请改用 v{VERSION}。

## 发生了什么

本版在 Minecraft 26.1 上会导致**界面中文全部显示为空白**：
模块名、设置项标题、分组标题都渲染不出来，
只剩数字和尚未翻译的英文，看起来像界面坏了一半。

## 原因

Meteor 的 GUI 不用 Minecraft 的字体，而是把文字烘焙进自建的字体图集。
它自带的四款字体只有拉丁字形，**没有任何中日韩字形**；
图集里查不到的字符不会生成任何绘制指令，于是整段中文静默消失。

Meteor 自带开关（`设置 → Visual → Font`）可以换成系统中文字体，
但它需要手动开启，全新的 26.1 实例默认用 Comfortaa，中文就会这样消失。
1.21.11 上之所以正常，是因为那边早先手动把字体设成了「等线」。

## 处理

本版的 jar 已从下载列表移除，不再提供下载。
请使用 [{TAG}](https://github.com/{OWNER}/{REPO}/releases/tag/{TAG})：它会自动检测并切换到可用的中文字体。
""".format(VERSION=VERSION_261, TAG="v" + VERSION_261, OWNER="{owner}", REPO="{repo}")


def retire_old_release(token):
    """把 1.5.0 的 jar 撤下来（不再提供下载），并把正文改成事故说明。"""
    st, rel = api_retry("GET", "/repos/%s/%s/releases/tags/%s" % (ghp.OWNER, REPO, RETIRED_TAG),
                        token=token, accept=(200, 404))
    if st != 200:
        print("release %s 不存在，无需撤回" % RETIRED_TAG, flush=True)
        return

    for asset in rel.get("assets", []):
        api_retry("DELETE", "/repos/%s/%s/releases/assets/%d" % (ghp.OWNER, REPO, asset["id"]),
                  token=token, accept=(204, 200))
        print("已撤下 asset: %s" % asset["name"], flush=True)

    body = RETIRED_BODY.replace("{owner}", ghp.OWNER).replace("{repo}", REPO)
    api_retry("PATCH", "/repos/%s/%s/releases/%d" % (ghp.OWNER, REPO, rel["id"]),
              data={"body": body}, token=token, accept=(200,))
    print("release %s 正文已改为事故说明" % RETIRED_TAG, flush=True)


def upload_asset(token, rel):
    """上传本版所有 jar（1.5.0 起是双线，两个产物）。"""
    st, assets = api_retry("GET", "/repos/%s/%s/releases/%d/assets" % (ghp.OWNER, REPO, rel["id"]),
                           token=token, accept=(200,))
    have = {a.get("name") for a in assets} if isinstance(assets, list) else set()

    for jar_name in JARS_RELEASE:
        jar = os.path.join(ROOT, "dist", jar_name)
        if not os.path.exists(jar):
            raise SystemExit("缺少产物: " + jar)
        raw = open(jar, "rb").read()
        name = jar_name
        if name in have:
            # 同名 asset 已存在时比对大小，不一致就删掉重传，避免远端留着旧产物
            old = next((a for a in assets if a.get("name") == name), None)
            if old and old.get("size") == len(raw):
                print("asset 已存在: %s (%d bytes)" % (name, len(raw)), flush=True)
                continue
            print("asset 大小不一致，删除重传: %s (远端 %s B / 本地 %d B)"
                  % (name, old.get("size") if old else "?", len(raw)), flush=True)
            api_retry("DELETE", "/repos/%s/%s/releases/assets/%d" % (ghp.OWNER, REPO, old["id"]),
                      token=token, accept=(204, 200))
            have.discard(name)

        path = "/repos/%s/%s/releases/%d/assets?name=%s" % (
            ghp.OWNER, REPO, rel["id"], urllib.parse.quote(name))
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/octet-stream",
        }
        last = None
        ok = False
        for _attempt in range(4):
            for ip in UPLOAD_IPS:
                try:
                    st2, _hs, payload = ghp._once(ip, "uploads.github.com", "POST", path, raw, headers, 180)
                    if st2 in (200, 201):
                        info = json.loads(payload.decode("utf-8"))
                        print("asset uploaded: %s (%d bytes)" % (info["name"], info["size"]), flush=True)
                        ok = True
                        break
                    last = (ip, st2, payload[:200])
                except Exception as exc:  # noqa: BLE001
                    last = (ip, type(exc).__name__, str(exc)[:120])
            if ok:
                break
            time.sleep(2)
        if not ok:
            raise SystemExit("上传 asset 失败: %r" % (last,))


def main():
    dry = "--dry-run" in sys.argv
    skip_workflows = "--skip-workflows" in sys.argv

    token = ghp.load_token()
    if not token:
        raise SystemExit("没有保存的 token，先运行 github_publish_ip.py 走一次 device flow")
    st, me = api_retry("GET", "/user", token=token, accept=(200,))
    ghp.OWNER = me["login"]
    print("account:", ghp.OWNER, "| skip_workflows:", skip_workflows, flush=True)

    local = collect_local_files(skip_workflows=skip_workflows)
    commit_sha, tree_sha, existing = remote_tree(token)

    to_delete = sorted(set(existing) - set(local))

    print("local files : %d" % len(local), flush=True)
    print("remote files: %d" % len(existing), flush=True)
    print("delete      : %d" % len(to_delete), flush=True)
    for p in to_delete:
        print("   - " + p, flush=True)

    if dry:
        print("\n[dry-run] 未改动远端。", flush=True)
        return

    cache = load_blob_cache()
    entries = []
    total = 0
    reused = 0
    for i, path in enumerate(local, 1):
        sha, size, hit = make_blob(token, path, cache)
        total += size
        if hit:
            reused += 1
        else:
            save_blob_cache(cache)
        mode = "100755" if os.path.basename(path) in EXECUTABLE else "100644"
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": sha})
        print("[%d/%d] %s %s (%d B)" % (i, len(local), "cached" if hit else "blob  ", path, size),
              flush=True)

    for path in to_delete:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})

    print("blob 复用 %d / 新传 %d" % (reused, len(local) - reused), flush=True)

    st, new_tree = api_retry(
        "POST", "/repos/%s/%s/git/trees" % (ghp.OWNER, REPO),
        data={"base_tree": tree_sha, "tree": entries}, token=token, accept=(200, 201),
    )
    if not isinstance(new_tree, dict) or "sha" not in new_tree:
        raise SystemExit("建 tree 失败: %s %r" % (st, str(new_tree)[:300]))
    print("tree:", new_tree["sha"], flush=True)

    message = (
        "feat: 1.4.5 / 1.5.5 —— 聊天栏消息正文汉化 (v%s)\n"
        "\n"
        "问题\n"
        "- 模块名早已是中文，但聊天栏正文仍是英文：\n"
        "  [Meteor] [仓库寻找器] Found stash at 5178744, 5296888.\n"
        "  这些是 ChatUtils.info(模板, 参数...) 拼出来的字符串，不是 lang 键\n"
        "\n"
        "实现\n"
        "- 钩 ChatUtils.formatMsg(String, ChatFormatting)：所有带文本消息的唯一汇聚点，\n"
        "  方法名两版唯一且注解不含 MC 类型，因此 remap = false 在两条线都成立\n"
        "- 该层收到的是已填好参数的文本，故用模板反查：英文模板编译成整串锚定正则\n"
        "  （%%s/%%d/%%.1f 变捕获组），中文模板用 $n 拼回，(highlight) 原样保留\n"
        "- dict/zh_chat.json 156 条；build_dict.py 的 sync_chat() 硬校验中英格式符个数与顺序\n"
        "- .zh info / .zh reload 会报告并重载聊天模板\n"
        "\n"
        "修复\n"
        "- ChatDict.translate(\"\") 空串取首字符导致 StringIndexOutOfBoundsException\n"
        "- 构建期格式符校验抓到 unstick 模板 %%s 与 %%d 顺序写反\n"
        "\n"
        "版本\n"
        "- 1.21.11 线 1.4.4 -> %s\n"
        "- 26.1 线 1.5.4 -> %s\n"
        "\n"
        "验证\n"
        "- verify_dict 15 项 / verify_lexical 9 项 / verify_261 14 项 / verify_chat 9 项全部通过\n"
        "\n"
        "Co-authored-by: deepseek-ai <noreply@deepseek.com>" % (VERSION, VERSION, VERSION_261)
    )
    st, new_commit = api_retry(
        "POST", "/repos/%s/%s/git/commits" % (ghp.OWNER, REPO),
        data={"message": message, "tree": new_tree["sha"], "parents": [commit_sha]},
        token=token, accept=(200, 201),
    )
    if not isinstance(new_commit, dict) or "sha" not in new_commit:
        raise SystemExit("建 commit 失败: %s %r" % (st, str(new_commit)[:300]))
    print("commit:", new_commit["sha"], flush=True)

    st, ref = api_retry(
        "PATCH", "/repos/%s/%s/git/refs/heads/%s" % (ghp.OWNER, REPO, BRANCH),
        data={"sha": new_commit["sha"], "force": False}, token=token, accept=(200,),
    )
    print("branch moved to", ref["object"]["sha"], flush=True)

    set_repo_meta(token)
    retire_old_release(token)
    rel = ensure_release(token)
    upload_asset(token, rel)

    print("\nDONE https://github.com/%s/%s" % (ghp.OWNER, REPO), flush=True)
    print("total uploaded bytes: %d" % total, flush=True)


if __name__ == "__main__":
    main()
