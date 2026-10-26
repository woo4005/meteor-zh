#!/usr/bin/env python3
"""通过 IP 直连把 meteor-zh 发布到 GitHub。

本机 DNS 到 github.com 间歇性失败，浏览器也因此打不开登录页。
这里直接连 GitHub 的已知 IP（TLS SNI 仍用正确主机名），绕开 DNS。
GitHub 的证书按主机名校验，所以 SNI 正确即可通过校验。
"""

import base64
import json
import os
import sys
import time
import urllib.parse
import socket
import ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = None  # 由 GET /user 的 login 填充
REPO = "meteor-zh"
VERSION = "1.3.1"
CLIENT_ID = "178c6fc778ccc68e1d6a"

PAYLOAD = os.path.join(ROOT, "dist", "meteor-zh-%s.jar" % VERSION)

GH_IPS = ["20.205.243.166", "140.82.112.3", "140.82.113.3", "140.82.114.3", "140.82.116.3"]
API_IPS = ["140.82.112.6", "140.82.113.6", "140.82.114.6", "140.82.116.6", "20.205.243.168"]

UA = "meteor-zh-publisher"


def _dechunk(b):
    out = b""
    while b:
        i = b.find(b"\r\n")
        if i < 0:
            break
        try:
            n = int(b[:i], 16)
        except ValueError:
            break
        if n == 0:
            break
        out += b[i + 2:i + 2 + n]
        b = b[i + 2 + n + 2:]
    return out


def _once(ip, host, method, path, body, headers, timeout):
    ctx = ssl.create_default_context()
    s = socket.create_connection((ip, 443), timeout=timeout)
    try:
        ss = ctx.wrap_socket(s, server_hostname=host)
    except Exception:
        s.close()
        raise
    try:
        h = {
            "Host": host,
            "User-Agent": UA,
            "Connection": "close",
            "Accept-Encoding": "identity",
        }
        if headers:
            h.update(headers)
        data = b""
        if body is not None:
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            h["Content-Length"] = str(len(data))
        head = method + " " + path + " HTTP/1.1\r\n"
        head += "".join("%s: %s\r\n" % (k, v) for k, v in h.items())
        head += "\r\n"
        ss.sendall(head.encode("utf-8") + data)
        buf = b""
        while True:
            c = ss.recv(65536)
            if not c:
                break
            buf += c
    finally:
        try:
            ss.close()
        except Exception:
            pass

    head, _, payload = buf.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    if len(lines) < 1:
        raise IOError("empty response")
    status = int(lines[0].split()[1])
    hs = {}
    for ln in lines[1:]:
        k, _, v = ln.decode("latin-1").partition(":")
        hs[k.strip().lower()] = v.strip()
    if "chunked" in hs.get("transfer-encoding", "").lower():
        payload = _dechunk(payload)
    return status, hs, payload


def http(host, ips, method, path, body=None, headers=None, timeout=20, retries=6):
    last = None
    for attempt in range(retries):
        for ip in ips:
            try:
                return _once(ip, host, method, path, body, headers, timeout)
            except Exception as e:  # noqa: BLE001
                last = e
        time.sleep(1.5)
    raise last


def api(method, path, data=None, token=None, timeout=45):
    headers = {}
    body = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    st, hs, payload = http("api.github.com", API_IPS, method, path, body, headers, timeout=timeout)
    try:
        return st, json.loads(payload.decode("utf-8")) if payload else None
    except ValueError:
        return st, payload.decode("utf-8", "replace")


def device_code_path():
    return os.path.join(os.environ.get("TEMP", "."), "gh_device_code.txt")


def token_path():
    return os.path.join(os.environ.get("TEMP", "."), "gh_token.txt")


def save_token(tok):
    with open(token_path(), "w", encoding="ascii") as f:
        f.write(tok)


def load_token():
    p = token_path()
    if os.path.isfile(p):
        t = open(p, encoding="ascii").read().strip()
        if t:
            return t
    return None


def poll_token(deadline):
    device = open(device_code_path(), encoding="ascii").read().strip()
    interval = 9
    while time.time() < deadline:
        body = urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "device_code": device,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }).encode("ascii")
        try:
            st, hs, payload = http(
                "github.com", GH_IPS, "POST", "/login/oauth/access_token", body,
                {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            )
            data = json.loads(payload.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("poll net error: %s %s" % (type(e).__name__, e), flush=True)
            time.sleep(6)
            continue

        if "access_token" in data:
            return data["access_token"]
        err = data.get("error", "")
        if err == "authorization_pending":
            pass
        elif err == "slow_down":
            interval += 5
        elif err == "expired_token":
            raise SystemExit("device code 已过期，需要重新生成")
        elif err == "access_denied":
            raise SystemExit("用户拒绝授权")
        else:
            print("poll:", data, flush=True)
        time.sleep(interval)
    raise SystemExit("等待授权超时")


def collect_files():
    items = []
    for rel in ("README.md", "LICENSE", "fabric.mod.json", ".gitignore"):
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            items.append(rel)
    for sub in ("src", "scripts", "dict", "i18n_ref"):
        base = os.path.join(ROOT, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__",)]
            for fn in filenames:
                if fn.endswith((".pyc", ".class")):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                items.append(rel)
    if os.path.isfile(PAYLOAD):
        items.append(os.path.relpath(PAYLOAD, ROOT).replace("\\", "/"))
    return sorted(set(items))


def upload(token, files):
    ok = 0
    for i, rel in enumerate(files, 1):
        raw = open(os.path.join(ROOT, rel), "rb").read()
        content = base64.b64encode(raw).decode("ascii")
        st, existing = api("GET", "/repos/%s/%s/contents/%s" % (OWNER, REPO, urllib.parse.quote(rel)), token=token)
        body = {
            "message": "Add " + rel,
            "content": content,
            "branch": "main",
        }
        if st == 200 and isinstance(existing, dict) and existing.get("sha"):
            body["sha"] = existing["sha"]
            body["message"] = "Update " + rel
        st2, resp = api("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, urllib.parse.quote(rel)),
                        data=body, token=token, timeout=120)
        if st2 in (200, 201):
            ok += 1
            print("[%d/%d] %s" % (i, len(files), rel), flush=True)
        else:
            print("[%d/%d] FAIL %s -> %s %s" % (i, len(files), rel, st2, str(resp)[:200]), flush=True)
    return ok


def main():
    global OWNER
    token = load_token()
    if token:
        print("using saved token", flush=True)
    else:
        deadline = time.time() + 890
        print("waiting for device authorization...", flush=True)
        token = poll_token(deadline)
        save_token(token)
        print("got token, len=%d" % len(token), flush=True)

    st, me = api("GET", "/user", token=token)
    if st != 200:
        raise SystemExit("GET /user failed %s %s" % (st, me))
    login = me["login"]
    OWNER = login
    print("user:", login, flush=True)

    st, repo = api("POST", "/user/repos", data={
        "name": REPO,
        "description": "Meteor Client 中文汉化 addon：模块名/描述/设置项/GUI 文本自动翻译，支持第三方 addon",
        "private": False,
        "has_issues": True,
        "has_wiki": False,
        "auto_init": False,
    }, token=token)
    if st in (200, 201):
        print("repo created:", repo["html_url"], flush=True)
    elif st == 422:
        print("repo already exists", flush=True)
    else:
        print("repo create:", st, str(repo)[:300], flush=True)

    files = collect_files()
    print("uploading %d files..." % len(files), flush=True)
    ok = upload(token, files)
    print("uploaded %d/%d" % (ok, len(files)), flush=True)

    st, rel = api("GET", "/repos/%s/%s/releases/tags/v%s" % (OWNER, REPO, VERSION), token=token)
    if st != 200:
        st, rel = api("POST", "/repos/%s/%s/releases" % (OWNER, REPO), data={
            "tag_name": "v" + VERSION,
            "target_commitish": "main",
            "name": "meteor-zh v" + VERSION,
            "body": "Meteor Client 中文汉化 v%s\n\n- 模块名 / 描述 / 设置项 / 分组名 / HUD 标题全量中文\n- 硬编码 GUI 文本（Bind、Active、Reset 等）中文\n- 795 词词法兜底，未收录的第三方 addon 标识符自动合成中文\n- 按键名中文（左Shift / 左Ctrl / None→无）\n- 启动自动翻译，重启依旧生效\n- 作者：dsh-woo4005；DeepSeek V4.1 flash 1017 协助完成" % VERSION,
        }, token=token)
    print("release:", st, (rel or {}).get("html_url") if isinstance(rel, dict) else rel, flush=True)

    print("DONE https://github.com/%s/%s" % (OWNER, REPO), flush=True)


if __name__ == "__main__":
    main()
