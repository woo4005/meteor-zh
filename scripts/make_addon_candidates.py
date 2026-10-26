# -*- coding: utf-8 -*-
"""Build the work list handed to the addon dictionary translator.

Collects the English identifiers and descriptions recovered from the third party
addon jars, drops the ones Meteor core already covers, and drops strings that are
clearly not user facing (mod ids, version markers, file permissions).
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "dict")

# identifiers that are never shown in the Meteor GUI
DENY = {
    "mc-version", "meteor-addon-template", "autoelytra-example", "autoelytra-hud",
    "meteor-miku", "rwxr-xr-x", "chord-length-s", "dt-max", "dt-min",
}

TARGETS = [
    ("raw_addons_autoelytra_1_21_11_1_2.json", "AutoElytra"),
    ("raw_addons_meteor_miku_1_21_11_11_0_0.json", "Miku"),
]


def load(path):
    if not os.path.exists(path):
        return {}
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    runtime = load(os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "zh.json"))
    known = set()
    known.update((runtime.get("modules") or {}).keys())
    known.update((runtime.get("settings") or {}).keys())

    names = {}
    descs = {}
    by_addon = {}

    for filename, label in TARGETS:
        raw = load(os.path.join(DICT, filename))
        added = []

        for k in raw.get("kebab") or []:
            if k in DENY or k in known or k in names:
                continue
            names[k] = ""
            added.append(k)

        if label == "AutoElytra":
            for s in raw.get("sentences") or []:
                if s in descs:
                    continue
                descs[s] = ""

        by_addon[label] = len(added)

    payload = {"names": names, "descs": descs}
    out = os.path.join(DICT, "candidates_addons.json")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print("names to translate : %d" % len(names))
    print("descs to translate : %d" % len(descs))
    print("per addon          : %s" % by_addon)
    print("written            : %s" % out)


if __name__ == "__main__":
    main()
