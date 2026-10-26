#!/usr/bin/env python3
"""生成模组图标 assets/meteorzh/icon.png（纯标准库手写 PNG，无第三方依赖）。

图案：Meteor 紫渐变圆角方块 + 白色「中」字（一个方框加一条中竖）。
"""
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "icon.png")
SIZE = 256

# Meteor 主题紫
TOP = (196, 90, 236)
BOTTOM = (120, 40, 170)
WHITE = (255, 255, 255)


def in_rounded_rect(x, y, size, radius):
    if radius <= 0:
        return True
    cx = min(max(x, radius), size - 1 - radius)
    cy = min(max(y, radius), size - 1 - radius)
    dx, dy = x - cx, y - cy
    return dx * dx + dy * dy <= radius * radius


def in_zhong(x, y, size):
    """「中」字：外框 + 中竖。坐标按 size 的比例。"""
    u = size / 100.0
    # 外框：x 28..72, y 24..76，线宽 8
    frame_l, frame_r = 28 * u, 72 * u
    frame_t, frame_b = 24 * u, 76 * u
    lw = 8 * u
    in_frame = (
        frame_l <= x <= frame_r and frame_t <= y <= frame_b
        and not (frame_l + lw < x < frame_r - lw and frame_t + lw < y < frame_b - lw)
    )
    # 中竖：x 46..54, y 12..88
    in_stem = 46 * u <= x <= 54 * u and 12 * u <= y <= 88 * u
    return in_frame or in_stem


def build_pixels():
    rows = []
    for y in range(SIZE):
        row = bytearray()
        row.append(0)  # filter type 0
        t = y / (SIZE - 1)
        base = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(SIZE):
            if not in_rounded_rect(x, y, SIZE, int(SIZE * 0.18)):
                r = g = b = a = 0
            elif in_zhong(x, y, SIZE):
                r, g, b, a = WHITE[0], WHITE[1], WHITE[2], 255
            else:
                r, g, b, a = base[0], base[1], base[2], 255
            row.extend((r, g, b, a))
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path, pixels, size):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8bit RGBA
    raw = zlib.compress(pixels, 9)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    write_png(OUT, build_pixels(), SIZE)
    print(f"icon: {os.path.getsize(OUT)} bytes -> {OUT}")
