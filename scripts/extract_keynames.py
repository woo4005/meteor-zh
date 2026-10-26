# -*- coding: utf-8 -*-
"""Recover the hard-coded key / mouse button names from Meteor's Utils class.

`Utils.getKeyName(int)` and `Utils.getButtonName(int)` are switch statements that
return English literals ("Left Shift", "Space", "Arrow Up", "Left Mouse", ...).
Those strings end up verbatim in the GUI next to "Bind: ", so they need
dictionary entries just like module titles do.

Rather than trying to slice out the two methods (method order in the class file is
not guaranteed), we harvest every String constant javap reports and keep the
plausible display names.
"""
import io
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVAP = r"C:\Users\wang'xiao'ya\AppData\Roaming\.minecraft\runtime\java-runtime-delta\bin\javap.exe"
METEOR = os.path.join(os.path.dirname(ROOT), "miku-villager-mover", "build-offline", "meteor-mojmap.jar")
OUT = os.path.join(ROOT, "dict", "raw_keynames.json")

STRING_RE = re.compile(r"// String (.+)$")

# String constants that live in Utils but are not GUI key names.
DENY = {
    "00:00", "%02d:%02d", "_", "-", "realms", "FAILED_BECAUSE_LEFT_WORLD",
    "NONE", "null", "", " ", ":", "%s",
}


def main():
    proc = subprocess.run(
        [JAVAP, "-p", "-c", "-cp", METEOR, "meteordevelopment.meteorclient.utils.Utils"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit("javap failed: %s" % proc.stderr[:400])

    seen = []
    for line in proc.stdout.splitlines():
        m = STRING_RE.search(line.rstrip())
        if not m:
            continue
        s = m.group(1)
        if s in DENY or "%" in s or s in seen:
            continue
        if not re.match(r"^[A-Za-z0-9 ]+$", s):
            continue
        seen.append(s)

    # Everything from "Esc" onwards is the key switch; keep the whole set anyway.
    keys = [s for s in seen]
    buttons = [s for s in ("Left Mouse", "Right Mouse", "Middle Mouse", "Unknown") if s in keys]

    for extra in ("None",):
        if extra not in keys:
            keys.append(extra)

    payload = {"keys": sorted(keys), "buttons": sorted(buttons)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")

    print("candidates : %d" % len(keys))
    print("buttons    : %s" % ", ".join(buttons))
    print("written    : %s" % OUT)
    print("all        : %s" % ", ".join(keys))


if __name__ == "__main__":
    main()
