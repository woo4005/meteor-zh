#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新走一次 GitHub device flow，这次带上 `workflow` scope。

背景：第一次授权只申请了 `repo`。写 `.github/workflows/**` 需要 `workflow`，
否则 GitHub 对包含工作流文件的 `POST /git/trees` 返回 404（不是 403，
很容易误判成路径写错）。

用法：
    python scripts/gh_reauth.py           # 生成 code 并等待授权
    python scripts/gh_reauth.py --status  # 只看当前 token 的 scope
"""
import json
import sys
import time
import urllib.parse

sys.path.insert(0, ".")

import github_publish_ip as ghp  # noqa: E402

CLIENT_ID = ghp.CLIENT_ID
SCOPE = "repo workflow"

FORM = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}


def call(path, data, timeout=40):
    body = urllib.parse.urlencode(data).encode("utf-8")
    return ghp.http("github.com", ghp.GH_IPS, "POST", path, body, FORM, timeout=timeout)


def show_status():
    token = ghp.load_token()
    if not token:
        print("no token saved")
        return
    headers = {"Authorization": "Bearer " + token}
    for ip in ghp.API_IPS:
        try:
            st, hs, payload = ghp._once(ip, "api.github.com", "GET", "/user", None, headers, 30)
        except Exception as exc:  # noqa: BLE001
            print("ip", ip, "EXC", exc)
            continue
        if st == 200:
            print("login :", json.loads(payload.decode("utf-8"))["login"])
            print("scopes:", repr(hs.get("x-oauth-scopes")))
            return
    print("token 无效")


def main():
    if "--status" in sys.argv:
        show_status()
        return

    st, _hs, payload = call("/login/device/code", {"client_id": CLIENT_ID, "scope": SCOPE})
    info = json.loads(payload.decode("utf-8"))
    if "user_code" not in info:
        raise SystemExit("申请 device code 失败: %s %r" % (st, info))

    with open(ghp.device_code_path(), "w", encoding="utf-8") as fh:
        fh.write(info["device_code"])

    print("=" * 60)
    print(" 请在浏览器打开：%s" % info["verification_uri"])
    print(" 输入代码      ：%s" % info["user_code"])
    print(" 有效期        ：%d 秒（每 %d 秒轮询一次）" % (info["expires_in"], info["interval"]))
    print(" 申请的 scope  ：%s" % SCOPE)
    print("=" * 60, flush=True)

    interval = max(6, int(info.get("interval", 5)))
    deadline = time.time() + int(info["expires_in"]) - 10
    while time.time() < deadline:
        time.sleep(interval)
        st, _hs, payload = call("/login/oauth/access_token", {
            "client_id": CLIENT_ID,
            "device_code": info["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        try:
            resp = json.loads(payload.decode("utf-8"))
        except ValueError:
            print("poll: 非 JSON 响应", payload[:120], flush=True)
            continue

        err = resp.get("error")
        if resp.get("access_token"):
            ghp.save_token(resp["access_token"])
            print("\n授权成功，token 已保存（scope 见 --status）", flush=True)
            show_status()
            return
        if err == "authorization_pending":
            print(".", end="", flush=True)
            continue
        if err == "slow_down":
            interval += 5
            print("s", end="", flush=True)
            continue
        print("\npoll 结束: %s %r" % (err, resp), flush=True)
        return

    print("\n超时，需要重新运行本脚本", flush=True)


if __name__ == "__main__":
    main()
