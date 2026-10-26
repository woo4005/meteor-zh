#!/usr/bin/env python3
"""把 Meteor-ZH 发布到 GitHub：device flow 授权 -> 建仓库 -> 上传文件 -> 建 release。

用法：
    python github_publish.py            # 轮询已保存的 device_code，授权后自动发布

device_code 由 scripts/github_device.py 生成并写入 %TEMP%\\gh_device_code.txt。
token 只保存在进程内存里，不落盘。
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_ID = "178c6fc778ccc68e1d6a"
DEVICE_FILE = os.path.join(os.environ.get("TEMP", "/tmp"), "gh_device_code.txt")

REPO_NAME = "meteor-zh"
DESCRIPTION = "Minecraft 1.21.11 Fabric / Meteor Client 全界面简体中文汉化插件（模块、设置、按键、HUD、GUI 硬编码文本）"
HOMEPAGE = "https://github.com/{owner}/meteor-zh"

UA = {"User-Agent": "meteor-zh-publisher", "Accept": "application/vnd.github+json"}


def http_json(url, method="GET", data=None, headers=None, token=None, raw=False, form=False, timeout=60):
    hdrs = dict(UA)
    if headers:
        hdrs.update(headers)
    if token:
        hdrs["Authorization"] = "Bearer " + token
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode("ascii")
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            return resp.status, (payload if raw else (json.loads(payload.decode("utf-8")) if payload else None))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        return e.code, text


def poll_token():
    if not os.path.exists(DEVICE_FILE):
        raise SystemExit("missing %s (run github_device.py first)" % DEVICE_FILE)
    device = open(DEVICE_FILE, encoding="ascii").read().strip()
    deadline = time.time() + 880
    while time.time() < deadline:
        try:
            st, r = http_json("https://github.com/login/oauth/access_token", "POST", {
                "client_id": CLIENT_ID,
                "device_code": device,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }, headers={"Accept": "application/json"}, form=True, timeout=25)
        except Exception as e:
            # 大陆网络到 github.com 偶发超时，重试即可
            print("poll net error: %s %s" % (type(e).__name__, e))
            time.sleep(6)
            continue
        if isinstance(r, dict) and r.get("access_token"):
            return r["access_token"]
        err = (r or {}).get("error") if isinstance(r, dict) else str(r)
        if err in ("authorization_pending",):
            time.sleep(5)
            continue
        if err in ("slow_down",):
            time.sleep(10)
            continue
        if err in ("expired_token", "access_denied"):
            raise SystemExit("device flow ended: %s" % err)
        print("poll: %s %s" % (st, err))
        time.sleep(6)
    raise SystemExit("timed out waiting for authorization")


def collect_files():
    files = []
    for rel_root, patterns in (
        ("", ["README.md", "LICENSE"]),
        ("src", None),
        ("scripts", None),
    ):
        base = os.path.join(ROOT, rel_root) if rel_root else ROOT
        if patterns:
            for p in patterns:
                fp = os.path.join(base, p)
                if os.path.isfile(fp):
                    files.append(fp)
        else:
            for dirpath, _dirnames, filenames in os.walk(base):
                for fn in filenames:
                    if fn.endswith((".pyc",)):
                        continue
                    files.append(os.path.join(dirpath, fn))
    jar_dir = os.path.join(ROOT, "dist")
    if os.path.isdir(jar_dir):
        for fn in sorted(os.listdir(jar_dir)):
            if fn.endswith(".jar"):
                files.append(os.path.join(jar_dir, fn))
    return files


def upload(token, owner, repo, files):
    ok = 0
    for fp in files:
        rel = os.path.relpath(fp, ROOT).replace("\\", "/")
        url = "https://api.github.com/repos/%s/%s/contents/%s" % (owner, repo, rel)
        content = base64.b64encode(open(fp, "rb").read()).decode("ascii")

        # 已存在则先取 sha 走更新
        st, cur = http_json(url, token=token)
        payload = {"message": "Add " + rel, "content": content}
        if st == 200 and isinstance(cur, dict):
            payload["sha"] = cur["sha"]
            payload["message"] = "Update " + rel

        st, res = http_json(url, "PUT", payload, token=token)
        if st in (200, 201):
            ok += 1
            print("  uploaded %-52s (%d bytes)" % (rel, os.path.getsize(fp)))
        else:
            print("  FAILED   %-52s -> %s %s" % (rel, st, str(res)[:160]))
    return ok


def main():
    token = poll_token()
    print("authorized")

    st, me = http_json("https://api.github.com/user", token=token)
    if st != 200:
        raise SystemExit("cannot read user: %s %s" % (st, me))
    owner = me["login"]
    print("user:", owner)

    # 建仓库（已存在则复用）
    st, repo = http_json("https://api.github.com/user/repos", "POST", {
        "name": REPO_NAME,
        "description": DESCRIPTION,
        "homepage": HOMEPAGE.format(owner=owner),
        "private": False,
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
    }, token=token)
    if st == 201:
        print("repo created")
    elif st == 422:
        print("repo already exists, reusing")
    else:
        raise SystemExit("repo create failed: %s %s" % (st, str(repo)[:300]))

    st, repo = http_json("https://api.github.com/repos/%s/%s" % (owner, REPO_NAME), token=token)
    default_branch = repo.get("default_branch", "main") if isinstance(repo, dict) else "main"

    files = collect_files()
    print("uploading %d files to %s/%s (%s)" % (len(files), owner, REPO_NAME, default_branch))
    ok = upload(token, owner, REPO_NAME, files)
    print("uploaded %d/%d" % (ok, len(files)))

    # release + jar asset
    ver = None
    fmj = os.path.join(ROOT, "src", "main", "resources", "fabric.mod.json")
    if os.path.isfile(fmj):
        ver = json.load(open(fmj, encoding="utf-8")).get("version")
    tag = "v" + (ver or time.strftime("%Y%m%d"))
    st, rel = http_json("https://api.github.com/repos/%s/%s/releases" % (owner, REPO_NAME), "POST", {
        "tag_name": tag,
        "name": "Meteor-ZH " + tag,
        "body": "Meteor Client 全界面简体中文汉化。下载下面的 jar 放进 mods 目录即可，"
                "启动游戏自动生效、重启后依然有效。\n\n"
                "作者：dsh-woo4005（DeepSeek V4.1 flash 1017 协助完成）",
        "draft": False,
        "prerelease": False,
    }, token=token)
    if st in (201, 422):
        if st == 201:
            print("release created:", rel.get("html_url"))
            jar = [f for f in files if f.endswith(".jar")]
            if jar and rel.get("upload_url"):
                upload_url = rel["upload_url"].split("{")[0] + "?name=" + os.path.basename(jar[0])
                data = open(jar[0], "rb").read()
                req = urllib.request.Request(upload_url, data=data, method="POST", headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/java-archive",
                    "User-Agent": "meteor-zh-publisher",
                })
                try:
                    with urllib.request.urlopen(req, timeout=180) as resp:
                        print("asset uploaded:", resp.status)
                except urllib.error.HTTPError as e:
                    print("asset upload failed:", e.code, e.read().decode("utf-8", "replace")[:200])
    else:
        print("release failed:", st, str(rel)[:200])

    print("\nDONE https://github.com/%s/%s" % (owner, REPO_NAME))


if __name__ == "__main__":
    sys.exit(main())
