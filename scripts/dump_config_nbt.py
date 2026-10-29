#!/usr/bin/env python3
"""Dump a Meteor Client config.nbt (gzip + NBT) to readable text.

Meteor saves its config with a custom NBT writer, so the file is a plain
NBT stream inside a gzip container.  This script prints the full recursive
structure so we can see *every* saved setting, not just the first group.

Usage:
  python scripts/dump_config_nbt.py <config.nbt> [...]
"""
import gzip
import sys

TAG_NAMES = {
    0: "TAG_End", 1: "TAG_Byte", 2: "TAG_Short", 3: "TAG_Int", 4: "TAG_Long",
    5: "TAG_Float", 6: "TAG_Double", 7: "TAG_ByteArray", 8: "TAG_String",
    9: "TAG_List", 10: "TAG_Compound", 11: "TAG_IntArray", 12: "TAG_LongArray",
}
SIZES = {1: 1, 2: 2, 3: 4, 4: 8, 5: 4, 6: 8}


class Reader:
    def __init__(self, data):
        self.d = data
        self.i = 0

    def take(self, n):
        v = self.d[self.i:self.i + n]
        self.i += n
        return v

    def u1(self):
        return self.take(1)[0]

    def u2(self):
        return int.from_bytes(self.take(2), "big", signed=True)

    def u4(self):
        return int.from_bytes(self.take(4), "big", signed=True)

    def u8(self):
        return int.from_bytes(self.take(8), "big", signed=True)

    def string(self):
        n = self.u2()
        return self.take(n).decode("utf-8", "replace")


def read_payload(r, tag):
    if tag == 1:
        return int.from_bytes(r.take(1), "big", signed=True)
    if tag == 2:
        return r.u2()
    if tag == 3:
        return r.u4()
    if tag == 4:
        return r.u8()
    if tag == 5:
        import struct
        return struct.unpack(">f", r.take(4))[0]
    if tag == 6:
        import struct
        return struct.unpack(">d", r.take(8))[0]
    if tag == 7:
        n = r.u4()
        return list(r.take(n))
    if tag == 8:
        return r.string()
    if tag == 9:
        elem = r.u1()
        n = r.u4()
        return [read_payload(r, elem) for _ in range(n)]
    if tag == 10:
        out = {}
        while True:
            t = r.u1()
            if t == 0:
                return out
            name = r.string()
            out[name] = read_payload(r, t)
    if tag == 11:
        n = r.u4()
        return [r.u4() for _ in range(n)]
    if tag == 12:
        n = r.u4()
        return [r.u8() for _ in range(n)]
    raise ValueError(f"unknown tag {tag}")


def dump(obj, indent=0, label=""):
    pad = "  " * indent
    if isinstance(obj, dict):
        head = f"{pad}{label}" if label else f"{pad}"
        print(head + "{")
        for k, v in obj.items():
            dump(v, indent + 1, f"{k}: ")
        print(pad + "}")
    elif isinstance(obj, list):
        head = f"{pad}{label}" if label else f"{pad}"
        if not obj:
            print(head + "[]")
            return
        print(head + "[")
        for v in obj:
            dump(v, indent + 1)
        print(pad + "]")
    else:
        print(f"{pad}{label}{obj!r}")


def main():
    for path in sys.argv[1:]:
        print("=" * 70)
        print(path)
        print("=" * 70)
        raw = open(path, "rb").read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        r = Reader(raw)
        tag = r.u1()
        if tag != 10:
            print(f"unexpected root tag {tag} ({TAG_NAMES.get(tag)})")
            continue
        r.string()  # root name
        dump(read_payload(r, 10))
        print()


if __name__ == "__main__":
    main()
