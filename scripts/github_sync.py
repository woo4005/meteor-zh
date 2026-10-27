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
VERSION = "1.4.0"
BRANCH = "main"

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
    "dist": {"only_files": {"meteor-zh-%s.jar" % VERSION}},
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

## 主要变化

- **许可证改为 GPL-3.0-or-later**（此前为 CC0 1.0；从本版起源码与分发包都按 GPL-3.0 授权，`LICENSE` 已替换为官方全文）
- 新增 `DEVELOPERS.md`：完整记录需求来源、人机分工、ADR 与技术取舍
- 新增 `CONTRIBUTING.md` / `SECURITY.md` / Issue 与 PR 模板
- 新增标准 Fabric Loom Gradle 工程与 GitHub Actions（构建 + 按 tag 发布）
- README 补齐兼容性矩阵、Mixin 注入点、性能实测数据、12 条已知边界
- 明确列出「明确不改的字段」及原因（改 `SettingGroup.name` 会静默破坏所有已保存配置）
- 词法词表修正：`no` → 无（原为「否」）、`anti` → 防（原为「反」）、`rad` → 半径

## 汉化覆盖

| 内容 | 条数 |
|---|---|
| 模块名 / 带描述的 | 267 / 170 |
| 设置项 / 带说明的 | 1136 / 1028 |
| 设置分组 | 129 |
| GUI 固定文本（Bind / Active / Reset 等） | 295 |
| 模块描述补充 | 22 |
| 按键名 | 66 |
| 顶部标签页 | 7 |
| 词法兜底词表 | 795 |

## 安装

把 `meteor-zh-{ver}.jar` 放进 `mods/`，启动游戏即可，无需任何配置。

## 详细说明

- [README.md](https://github.com/{owner}/{repo}/blob/main/README.md)
- [CHANGELOG.md](https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md)
- [DEVELOPERS.md](https://github.com/{owner}/{repo}/blob/main/DEVELOPERS.md)
""".format(ver=VERSION, owner=ghp.OWNER, repo=REPO)

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
    jar = os.path.join(ROOT, "dist", "meteor-zh-%s.jar" % VERSION)
    name = os.path.basename(jar)
    raw = open(jar, "rb").read()

    st, assets = api_retry("GET", "/repos/%s/%s/releases/%d/assets" % (ghp.OWNER, REPO, rel["id"]),
                           token=token, accept=(200,))
    if isinstance(assets, list):
        for a in assets:
            if a.get("name") == name:
                print("asset 已存在: %s (%d bytes)" % (a["name"], a["size"]), flush=True)
                return a

    path = "/repos/%s/%s/releases/%d/assets?name=%s" % (
        ghp.OWNER, REPO, rel["id"], urllib.parse.quote(name))
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/octet-stream",
    }
    last = None
    for _attempt in range(4):
        for ip in UPLOAD_IPS:
            try:
                st2, _hs, payload = ghp._once(ip, "uploads.github.com", "POST", path, raw, headers, 180)
                if st2 in (200, 201):
                    info = json.loads(payload.decode("utf-8"))
                    print("asset uploaded: %s (%d bytes)" % (info["name"], info["size"]), flush=True)
                    return info
                last = (ip, st2, payload[:200])
            except Exception as exc:  # noqa: BLE001
                last = (ip, type(exc).__name__, str(exc)[:120])
        time.sleep(2)
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
        "chore: 切换到 GPL-3.0 并补齐工程化设施 (v%s)\n\n"
        "许可证\n"
        "- LICENSE 由 CC0 换为 GPL-3.0 官方全文，源码与分发包同步\n"
        "- 6 个 Java 源文件加 GPL-3.0 头与 SPDX 标识\n\n"
        "文档\n"
        "- 新增 DEVELOPERS.md：需求来源、人机分工、5 条 ADR 与技术取舍\n"
        "- 新增 CONTRIBUTING.md / SECURITY.md / Issue 与 PR 模板\n"
        "- 新增 CHANGELOG.md / NOTICE（第三方词源归属）\n"
        "- README 重写：兼容性矩阵、Mixin 注入点、性能实测、12 条已知边界\n\n"
        "工程化\n"
        "- 新增标准 Fabric Loom Gradle 工程（mojmap）与 Gradle 9.5.1 wrapper\n"
        "- 新增 GitHub Actions：build.yml 构建、release.yml 按 tag 发布\n"
        "- verify 脚本改为环境变量 + 自动探测，去掉写死的本机路径\n"
        "- 词法词表修正：no→无、anti→防、rad→半径\n\n"
        "- fabric.mod.json 版本改用 ${version} 占位符，两条构建路径都展开\n"
        "- 仓库清理：移除反编译产物与旧版本 jar" % VERSION
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
