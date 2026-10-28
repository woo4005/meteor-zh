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
VERSION = "1.5.0"
#: 1.21.11 线仍停留在 1.4.0，两条线独立编号
VERSION_1211 = "1.4.0"
BRANCH = "main"

#: 两条构建线的产物（26.1 线带 -mc26.1 后缀）
JARS = ["meteor-zh-%s.jar" % VERSION_1211, "meteor-zh-%s-mc26.1.jar" % VERSION]

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
    "dist": {"only_files": set(JARS)},
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
    if st == 200:
        print("release %s 已存在: %s" % (tag, rel.get("html_url")), flush=True)
        return rel

    body = """Meteor Client 全界面简体中文汉化 v{ver}

## 本版新增 Minecraft 26.1 支持（1.5.x 线）

两条构建线**各自独立编号**，源码共用同一份：

| 游戏版本 | 下载 | 版本线 | 前置要求 |
|---|---|---|---|
| **Minecraft 26.1** | `meteor-zh-{ver}-mc26.1.jar` | **1.5.x**（本版新增） | Fabric Loader ≥ 0.20.1、Java 25、Meteor Client 26.1.x |
| **Minecraft 1.21.11** | `meteor-zh-{ver1211}.jar` | **1.4.x**（继续维护） | Fabric Loader ≥ 0.16.0、Java 21、Meteor Client 1.21.11 |

1.21.11 线的后续更新发 1.4.1、1.4.2……，26.1 线的更新发 1.5.1、1.6.0……，互不牵连。
词典为两条线共享，本版扩充的词条已同时打进两个 jar。

两个 jar 的 mod id 相同，**各自放进对应实例的 `mods/`**，不要塞进同一个实例。

## 主要变化

- **新增 Minecraft 26.1 / Meteor Client 26.1.2 支持**：MC 26.x 起游戏不再混淆，整条 mojmap → intermediary 的 remap 流程被删掉，编译完直接打包
- **词典大扩充**：模块 267 → 376，设置 1136 → 1335，英文描述句 22 → **1357**，词法词表 795 → **1069 词元**
- **Minecraft 26.1 本体覆盖率 100%**：169 模块 / 968 设置项 / 92 分组，标题与说明全部有中文（脚本逐条核对）
- 并入社区四个 GPL-3.0 汉化项目（xingke0、Nippaku-Zanmu、dingzhen-vape、EnderUnion）的译名，见 `NOTICE`
- `compatibilityLevel` 提升到 `JAVA_25`；`ZhCommand.build()` 改用原始类型，一份源码同时编译 21 和 25
- 新增离线验证脚本 `scripts/verify_261.py`：不启动游戏即可验证词典、**9 个反射字段是否仍然存在**、查找结果

## 汉化覆盖

| 内容 | 条数 |
|---|---|
| 模块名 / 带描述的 | 376 / 170 |
| 设置项 / 带说明的 | 1335 / 1028 |
| 设置分组 | 129 |
| GUI 固定文本（Bind / Active / Reset 等） | 295 |
| 英文描述句（模块与设置说明） | 1357 |
| 按键名 | 66 |
| 顶部标签页 | 7 |
| 词法兜底词表 | 1069 |

## 安装

按游戏版本下载对应 jar，放进 `mods/`，启动游戏即可，无需任何配置。

## 详细说明

- [README.md](https://github.com/{owner}/{repo}/blob/main/README.md)
- [CHANGELOG.md](https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md)
- [DEVELOPERS.md](https://github.com/{owner}/{repo}/blob/main/DEVELOPERS.md)
""".format(ver=VERSION, ver1211=VERSION_1211, owner=ghp.OWNER, repo=REPO)

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


def upload_asset(token, rel):
    """上传本版所有 jar（1.5.0 起是双线，两个产物）。"""
    st, assets = api_retry("GET", "/repos/%s/%s/releases/%d/assets" % (ghp.OWNER, REPO, rel["id"]),
                           token=token, accept=(200,))
    have = {a.get("name") for a in assets} if isinstance(assets, list) else set()

    for jar_name in JARS:
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
        "feat: 新增 Minecraft 26.1 支持，词典大幅扩充 (v%s)\n\n"
        "26.1 构建线\n"
        "- 新增 scripts/build_261.py：MC 26.x 不再混淆，去掉整条 remap，直接打包\n"
        "- 产物 meteor-zh-%s-mc26.1.jar（Fabric Loader >= 0.20.1 / Java 25 / Meteor 26.1.x）\n"
        "- ZhCommand.build() 改用原始类型，一份源码同时编译 1.21.11 与 26.1\n"
        "- meteor-zh.mixins.json 的 compatibilityLevel: JAVA_21 -> JAVA_25\n"
        "- fabric.mod.json 在 26.1 构建时注入 \"java\": \">=25\"\n\n"
        "词典\n"
        "- 新增 scripts/extract_261.py：扫 Meteor 26.1.2 源码提取模块/设置/分组/描述\n"
        "- 新增 scripts/patch_261_dict.py、scripts/merge_external.py、scripts/sanity_zh.py\n"
        "- 模块 267 -> 376，设置 1136 -> 1335，描述句 22 -> 1357，词表 795 -> 1069\n"
        "- 并入 xingke0 / Nippaku-Zanmu / dingzhen-vape / EnderUnion 四个 GPL-3.0 项目的译名\n"
        "- NOTICE 更新第三方词源与许可证说明（yalu 词典的 CC0 表述已更正）\n\n"
        "验证\n"
        "- 新增 scripts/verify_261.py：用实例真实 classpath 离线验证词典、9 个反射字段与查找结果\n"
        "- build.py 增加 stdout/stderr UTF-8 重定向，编译错误不再被 GBK 控制台吞掉\n\n"
        "文档\n"
        "- README：双线兼容性表、按版本下载、前置要求表、26.1 线的两个构建坑\n"
        "- CHANGELOG / qq-group-post 同步到 1.5.0" % (VERSION, VERSION)
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
    rel = ensure_release(token)
    upload_asset(token, rel)

    print("\nDONE https://github.com/%s/%s" % (ghp.OWNER, REPO), flush=True)
    print("total uploaded bytes: %d" % total, flush=True)


if __name__ == "__main__":
    main()
