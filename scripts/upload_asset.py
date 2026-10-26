#!/usr/bin/env python3
"""给已创建的 release 补传 jar 附件（走 uploads.github.com 的直连 IP）。"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github_publish_ip as g  # noqa: E402

UPLOAD_IPS = ["20.27.177.119", "140.82.112.9", "140.82.113.9", "140.82.114.9"]


def main():
    token = g.load_token()
    if not token:
        raise SystemExit("没有保存的 token")

    st, me = g.api("GET", "/user", token=token)
    owner = me["login"]
    repo = g.REPO
    version = g.VERSION

    st, rel = g.api("GET", "/repos/%s/%s/releases/tags/v%s" % (owner, repo, version), token=token)
    if st != 200:
        raise SystemExit("release not found: %s %s" % (st, rel))
    rid = rel["id"]
    print("release id:", rid, rel["html_url"])

    existing = set(a["name"] for a in rel.get("assets", []))
    name = os.path.basename(g.PAYLOAD)
    if name in existing:
        print("asset already present:", name)
        return

    raw = open(g.PAYLOAD, "rb").read()
    path = "/repos/%s/%s/releases/%d/assets?name=%s" % (owner, repo, rid, name)
    st, hs, payload = g.http(
        "uploads.github.com", UPLOAD_IPS, "POST", path, raw,
        {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/java-archive",
            "Accept": "application/vnd.github+json",
        },
        timeout=180,
    )
    print("upload:", st, payload[:300].decode("utf-8", "replace"))

    st, rel2 = g.api("GET", "/repos/%s/%s/releases/tags/v%s" % (owner, repo, version), token=token)
    if st == 200:
        for a in rel2.get("assets", []):
            print("asset:", a["name"], a["size"], a["browser_download_url"])


if __name__ == "__main__":
    main()
