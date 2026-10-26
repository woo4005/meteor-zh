# -*- coding: utf-8 -*-
"""Extract candidate Meteor module / setting names from third party addon jars.

Meteor module and setting identifiers are kebab-case (e.g. "elytra-finder",
"anti-afk"), while descriptions are plain sentences. Reading the constant pool of
every class is enough to recover both without a decompiler:

  * kebab-case strings  -> candidate module / setting names
  * sentence-like strings (capitalised, spaces, ending with '.') -> candidate
    descriptions

Usage:  python extract_addons.py <jar> [<jar> ...]
Output: dict/raw_addons_<jarname>.json
"""
import io
import json
import os
import re
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, "dict")

KEBAB = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
SINGLE = re.compile(r"^[a-z][a-z0-9]{2,}$")
SENTENCE = re.compile(r"^[A-Z][^.]{3,120}\.$")


def read_constant_pool(data):
    """Return every CONSTANT_Utf8 string in a class file."""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return []

    pos = 8
    (cp_count,) = struct.unpack_from(">H", data, pos)
    pos += 2

    strings = []
    index = 1
    while index < cp_count:
        tag = data[pos]
        pos += 1
        if tag == 1:  # CONSTANT_Utf8
            (length,) = struct.unpack_from(">H", data, pos)
            pos += 2
            raw = data[pos:pos + length]
            pos += length
            try:
                strings.append(raw.decode("utf-8"))
            except UnicodeDecodeError:
                strings.append(raw.decode("utf-8", "replace"))
        elif tag in (7, 8, 16, 19, 20):  # Class, String, MethodType, Module, Package
            pos += 2
        elif tag in (15,):  # MethodHandle
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):  # int/float/refs/nameandtype/dyn
            pos += 4
        elif tag in (5, 6):  # long, double take two slots
            pos += 8
            index += 1
        else:
            return strings  # unknown tag, bail out with what we have
        index += 1

    return strings


def scan_jar(path):
    kebab = set()
    single = set()
    sentences = set()

    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            data = z.read(name)
            for s in read_constant_pool(data):
                if not s or len(s) > 200:
                    continue
                if KEBAB.match(s):
                    kebab.add(s)
                elif SENTENCE.match(s):
                    sentences.add(s)
                elif SINGLE.match(s) and len(s) <= 20:
                    single.add(s)

    return kebab, single, sentences


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: extract_addons.py <jar> [<jar> ...]")

    os.makedirs(DICT, exist_ok=True)

    for jar in sys.argv[1:]:
        base = os.path.basename(jar)
        kebab, single, sentences = scan_jar(jar)

        stem = re.sub(r"[^0-9a-zA-Z]+", "_", os.path.splitext(base)[0])[:60]
        out = os.path.join(DICT, "raw_addons_%s.json" % stem)

        payload = {
            "jar": base,
            "kebab": sorted(kebab),
            "single": sorted(single),
            "sentences": sorted(sentences),
        }
        with io.open(out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

        print("%-52s kebab=%-4d single=%-4d sentences=%-4d" % (base, len(kebab), len(single), len(sentences)))
        print("    -> %s" % out)


if __name__ == "__main__":
    main()
