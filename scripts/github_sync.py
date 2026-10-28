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
VERSION = "1.5.1"
#: 1.21.11 线仍停留在 1.4.0，两条线独立编号
VERSION_1211 = "1.4.1"
BRANCH = "main"

#: 两条构建线的产物（26.1 线带 -mc26.1 后缀）——见同一个仓库的 dist/ 白名单
JARS_ALL = ["meteor-zh-%s.jar" % VERSION_1211, "meteor-zh-%s-mc26.1.jar" % VERSION]

#: 本次 release 应附上的 jar：只放属于本版本线的产物。
#: 1.5.0 是 26.1 线，所以只上传 -mc26.1 那个；1.21.11 的 1.4.0 jar 归 v1.4.0 release。
JARS_RELEASE = ["meteor-zh-%s-mc26.1.jar" % VERSION]

UPLOAD_IPS = ["20.27.177.119", "140.82.112.9", "140.82.113.9", "140.82.114.9"]
BLOB_CACHE = os.path.join(os.environ.get("TEMP", "."), "meteor_zh_blobs.json")

#: 仓库根目录下的单文件
ROOT_FILES = [
    "README.md", "LICENSE", "CHANGELOG.md", "NOTICE", "CONTRIBUTING.md",
    "SECURITY.md", "DEVELOPERS.md", ".gitignore",
    "build.gradle", "settings.gradle", "gradle.properties", "gradlew", "gradlew.bat",
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

## 修复：Minecraft 26.1 上中文全部显示为空白

`v1.5.0` 在 26.1 上有一个严重问题：模块名、设置项标题、分组标题这些**已经翻成中文**的地方，
界面上完全看不到，只剩数字和尚未翻译的英文，看起来像界面坏掉了一半。词典本身没问题，问题在字体。

### 起因

Meteor 的 GUI 不使用 Minecraft 的字体。它把界面文字烘焙进一张自建的字体图集，
而 Meteor 自带的四款字体（JetBrains Mono / Comfortaa / Tw Cen MT / Pixelation）**只有拉丁字形**，
没有任何中日韩字形。图集里查不到的字符不会生成任何绘制指令，于是整段中文静默消失。

Meteor 留了开关：`设置 → Visual → Font`，可以换成系统里的任意字体。
但这是**需要手动打开**的选项，全新的 26.1 实例默认用 Comfortaa，中文就会这样消失。
1.21.11 那边之所以正常，是因为早先手动把字体设成了「等线（DengXian）」——
对比两个实例的 `meteor-zh/config.nbt` 能直接看到：1.21.11 里有 `font: DengXian`，26.1 里是空的。

### 修复

本版新增 `FontFixer`：启动后用一串中文探针测量当前字体，宽度为 0 就说明画不出中文，
于是自动把 Meteor 切到系统里第一款可用的中文字体
（等线 → 微软雅黑 → 黑体 → 宋体 → Noto Sans CJK → 苹方 …），并写回 `Config`，下次启动保持。

- 已经能显示中文的机器**不会被改动**，字体偏好保持不变
- 一个中文字体都找不到时会在日志里说明，可执行 `.zh font` 重新检测，或在设置里手动选择
- 字体图集要等首次资源加载才建好，所以插件会在最初若干 tick 内重试，不会抢跑

### 两条线都已更新

| 游戏版本 | 下载 | 版本线 | 前置要求 |
|---|---|---|---|
| **Minecraft 26.1** | `meteor-zh-{ver}-mc26.1.jar` | **1.5.x** | Fabric Loader ≥ 0.20.1、Java 25、Meteor Client 26.1.x |
| **Minecraft 1.21.11** | `meteor-zh-{ver1211}.jar` | **1.4.x** | Fabric Loader ≥ 0.16.0、Java 21、Meteor Client 1.21.11 |

两条线的源码相同，本版同样给 1.21.11 线发了 {ver1211}（新增 `FontFixer` 与 `compatibilityLevel`
按目标版本分线设置），26.1 线发 {ver}。两个 jar 的 mod id 相同，**分别放进对应实例的 `mods/`**。

### 汉化覆盖

| 内容 | 条数 |
|---|---|
| 模块名 | 376 |
| 设置项 | 1335 |
| 设置分组 | 129 |
| GUI 固定文本（Bind / Active / Reset 等） | 295 |
| 英文描述句（模块与设置说明） | 1357 |
| 按键名 | 66 |
| 顶部标签页 | 7 |
| 词法兜底词表 | 1069 |

### 安装

按游戏版本下载对应 jar，放进 `mods/`，启动游戏即可，无需任何配置。
如果界面出现中文但显示成方框或空白，执行一次 `.zh font`。

### 详细说明

- [README.md](https://github.com/{owner}/{repo}/blob/main/README.md)
- [CHANGELOG.md](https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md)
- [DEVELOPERS.md](https://github.com/{owner}/{repo}/blob/main/DEVELOPERS.md)
""".format(ver=VERSION, ver1211=VERSION_1211, owner=ghp.OWNER, repo=REPO)

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
""".format(VERSION=VERSION, TAG="v" + VERSION, OWNER="{owner}", REPO="{repo}")


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
        "fix: 26.1 上中文不显示，自动切换到可渲染中文的系统字体 (v%s)\n\n"
        "问题\n"
        "- 1.5.0 在 MC 26.1 上中文全部渲染为空白（模块名/设置项/分组标题消失）\n"
        "- 根因：Meteor 的 GUI 用自烘焙字体图集，自带四款字体无 CJK 字形；\n"
        "  图集缺字形时不生成绘制指令，整段中文静默消失\n"
        "- 26.1 实例的 meteor-zh/config.nbt 里 font 为空（默认 Comfortaa），\n"
        "  而 1.21.11 实例早先手动设成了 DengXian，所以旧版本没暴露该问题\n\n"
        "修复\n"
        "- 新增 com.meteorzh.FontFixer：用中文探针测宽，为 0 则切换系统 CJK 字体\n"
        "  （DengXian / Microsoft YaHei / SimHei / SimSun / Noto Sans CJK ...）\n"
        "- 切换结果写回 Config.font，重启后保持；已能显示中文的机器不被动到\n"
        "- 字体图集要等首次资源加载，MeteorZh 在最初 40 个 tick 内重试\n"
        "- 新增 .zh font 手动重检；找不到字体时在日志与命令里给出指引\n\n"
        "版本\n"
        "- 26.1 线 1.5.0 -> %s（v1.5.0 已撤回下载）\n"
        "- 1.21.11 线 1.4.0 -> %s（同步 FontFixer）\n"
        "- mixins.json 的 compatibilityLevel 改为按构建线设置：21 线 JAVA_21 / 26.1 线 JAVA_25\n\n"
        "验证\n"
        "- scripts/verify_261.py 增加 FontFixer 探针：无 GL 上下文时安全返回 false，不抛异常\n"
        "- 两个 jar 的 fabric.mod.json / mixins.json 逐项核对" % (VERSION, VERSION, VERSION_1211)
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
