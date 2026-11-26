#!/usr/bin/env python3
"""Draw the entry image: a browser window whose open tabs give the game away.

Pure standard library (no Pillow, no network): the picture is rasterised into a
bytearray and written as an RGB PNG with zlib.  The run is deterministic, so two
runs write byte-identical files.
"""

import math
import os
import struct
import zlib

W = H = 1024

# ---------------------------------------------------------------- colour ----
BG_TOP = (30, 36, 48)
BG_BOTTOM = (15, 18, 26)
SHADOW = (9, 12, 18)
WINDOW = (255, 255, 255)
CHROME = (233, 236, 241)
CHROME_LINE = (208, 213, 221)
TAB_IDLE = (208, 214, 223)
TAB_BORDER = (168, 177, 190)
INK = (23, 26, 32)
INK_SOFT = (78, 86, 99)
ACCENT = (56, 126, 245)
DOT_RED = (255, 95, 86)
DOT_AMBER = (254, 188, 46)
DOT_GREEN = (40, 200, 64)
FIELD = (242, 244, 247)
FIELD_LINE = (218, 223, 230)

canvas = bytearray(W * H * 3)


# ------------------------------------------------------------ raster ops ----
def fill_rect(x0, y0, x1, y1, rgb):
    x0 = max(0, int(x0))
    y0 = max(0, int(y0))
    x1 = min(W, int(x1))
    y1 = min(H, int(y1))
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(rgb) * (x1 - x0)
    for y in range(y0, y1):
        off = (y * W + x0) * 3
        canvas[off:off + len(row)] = row


def _corner(i, r):
    dy = r - 1 - i
    return r - math.isqrt(max(0, r * r - dy * dy))


def round_rect(x0, y0, x1, y1, r, rgb, corners=(True, True, True, True)):
    tl, tr, br, bl = corners
    for y in range(int(y0), int(y1)):
        xa, xb = int(x0), int(x1)
        if tl and r and y - y0 < r:
            xa = x0 + _corner(y - y0, r)
        if tr and r and y - y0 < r:
            xb = x1 - _corner(y - y0, r)
        if bl and r and y1 - 1 - y < r:
            xa = max(xa, x0 + _corner(y1 - 1 - y, r))
        if br and r and y1 - 1 - y < r:
            xb = min(xb, x1 - _corner(y1 - 1 - y, r))
        fill_rect(xa, y, xb, y + 1, rgb)


def disc(cx, cy, r, rgb):
    for dy in range(-r, r + 1):
        span = math.isqrt(max(0, r * r - dy * dy))
        fill_rect(cx - span, cy + dy, cx + span + 1, cy + dy + 1, rgb)


def stroke(x0, y0, x1, y1, t, rgb):
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        fill_rect(x0, y0, x0 + t, y0 + t, rgb)
        return
    for i in range(steps + 1):
        px = x0 + (x1 - x0) * i / steps
        py = y0 + (y1 - y0) * i / steps
        fill_rect(px, py, px + t, py + t, rgb)


# ------------------------------------------------------------------ font ----
# 5x9 cell, rows 0-8: ascender 0-1, x-height 2-6, descender 7-8.
FONT = {
    " ": ("....." , ".....", ".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####", ".....", "....."),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####.", ".....", "....."),
    "c": (".....", ".....", ".###.", "#...#", "#....", "#...#", ".###.", ".....", "....."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####", ".....", "....."),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###.", ".....", "....."),
    "f": ("..##.", ".#...", "####.", ".#...", ".#...", ".#...", ".#...", ".....", "....."),
    "g": (".....", ".....", ".####", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#", ".....", "....."),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###.", ".....", "....."),
    "j": ("...#.", ".....", "...#.", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#.", ".....", "....."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###.", ".....", "....."),
    "m": (".....", ".....", "#####", "#.#.#", "#.#.#", "#.#.#", "#.#.#", ".....", "....."),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#", ".....", "....."),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###.", ".....", "....."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "..##.", ".#..#", ".#...", ".#...", ".#...", ".....", "....."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####.", ".....", "....."),
    "t": (".....", ".#...", "####.", ".#...", ".#...", ".#..#", "..##.", ".....", "....."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####", ".....", "....."),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#..", ".....", "....."),
    "w": (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#.", ".....", "....."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", ".....", "....."),
    "y": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####", ".....", "....."),
    "(": ("..#", ".#.", ".#.", ".#.", ".#.", ".#.", ".#.", ".#.", "..#"),
    ")": ("#..", ".#.", ".#.", ".#.", ".#.", ".#.", ".#.", ".#.", "#.."),
    "'": (".#.", ".#.", "...", "...", "...", "...", "...", "...", "..."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", "..#..", ".....", "..#..", "....."),
    "!": (".#.", ".#.", ".#.", ".#.", ".#.", ".#.", "...", ".#.", "..."),
    ".": ("...", "...", "...", "...", "...", "...", ".#.", "...", "..."),
    ",": ("...", "...", "...", "...", "...", ".#.", ".#.", "#..", "..."),
    "-": (".....", ".....", ".....", ".....", "###..", ".....", ".....", ".....", "....."),
    ":": ("...", "...", ".#.", "...", "...", ".#.", "...", "...", "..."),
    "/": ("....#", "....#", "...#.", "..#..", "..#..", ".#...", "#....", "#....", "....."),
    '"': ("#.#", "#.#", "...", "...", "...", "...", "...", "...", "..."),
    "+": (".....", ".....", "..#..", "..#..", "#####", "..#..", "..#..", ".....", "....."),
}


def glyph_span(ch):
    rows = FONT[ch]
    lo, hi = 5, -1
    for row in rows:
        for c, bit in enumerate(row):
            if bit == "#":
                lo = min(lo, c)
                hi = max(hi, c)
    if hi < lo:
        return 0, 0
    return lo, hi - lo + 1


def text_width(text, s):
    width = 0
    for ch in text:
        if ch == " ":
            width += 3 * s
            continue
        _, gw = glyph_span(ch)
        width += gw * s + s
    return width - s if text else 0


def draw_text(x, y, text, s, rgb):
    pen = x
    for ch in text:
        if ch == " ":
            pen += 3 * s
            continue
        lo, gw = glyph_span(ch)
        rows = FONT[ch]
        for ry, row in enumerate(rows):
            for c in range(lo, lo + gw):
                if row[c] == "#":
                    fill_rect(pen + (c - lo) * s, y + ry * s,
                              pen + (c - lo + 1) * s, y + (ry + 1) * s, rgb)
        pen += gw * s + s


def fit_scale(lines, max_width, top=7, low=4):
    s = top
    while s > low and max(text_width(line, s) for line in lines) > max_width:
        s -= 1
    return s


def lines_block(lines, cx, cy, s, gap, rgb):
    block = len(lines) * 9 * s + (len(lines) - 1) * gap
    y = cy - block // 2
    for line in lines:
        draw_text(cx - text_width(line, s) // 2, y, line, s, rgb)
        y += 9 * s + gap


# --------------------------------------------------------------- picture ----
def background():
    for y in range(H):
        t = y / (H - 1)
        rgb = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        fill_rect(0, y, W, y + 1, rgb)


def browser_window():
    # shadow then the window itself
    round_rect(46, 74, 990, 1014, 30, SHADOW)
    round_rect(36, 64, 980, 1004, 30, WINDOW)
    # title bar, square bottom corners
    round_rect(36, 64, 980, 140, 30, CHROME, (True, True, False, False))
    fill_rect(36, 138, 980, 141, CHROME_LINE)
    # traffic lights
    disc(74, 102, 10, DOT_RED)
    disc(104, 102, 10, DOT_AMBER)
    disc(134, 102, 10, DOT_GREEN)
    # quiet window title
    title = "four tabs open"
    ts = 3
    draw_text(508 - text_width(title, ts) // 2, 89, title, ts, INK_SOFT)


def tab(x0, y0, x1, y1, title_lines, active, favicon, play=False):
    radius = 20
    round_rect(x0, y0, x1, y1, radius, TAB_BORDER)
    round_rect(x0 + 2, y0 + 2, x1 - 2, y1 - 2, radius - 2,
               WINDOW if active else TAB_IDLE, (True, True, False, False))
    if active:
        fill_rect(x0 + 24, y0 + 2, x1 - 24, y0 + 9, ACCENT)
    # tiny site icon, the way a real tab carries one
    round_rect(x0 + 26, y0 + 24, x0 + 46, y0 + 44, 6, favicon)
    if play:
        for i in range(11):
            w = 8 - abs(i - 5)
            fill_rect(x0 + 34, y0 + 27 + i, x0 + 34 + w, y0 + 28 + i, (255, 255, 255))
    # close glyph
    gx, gy, gs = x1 - 36, y0 + 30, 9
    stroke(gx, gy, gx + gs, gy + gs, 3, INK_SOFT if active else (110, 118, 130))
    stroke(gx + gs, gy, gx, gy + gs, 3, INK_SOFT if active else (110, 118, 130))
    # title: the whole joke, as big as the card allows
    inner = (x1 - x0) - 56
    s = fit_scale(title_lines, inner, top=6, low=4)
    ink = INK if active else (32, 36, 43)
    lines_block(title_lines, (x0 + x1) // 2, (y0 + y1) // 2 + 6, s, 2 * s, ink)


def tabs():
    left, right = 58, 958
    top = 156
    gutter = 16
    tab_w = (right - left - gutter) // 2
    tab_h = 318
    row_gap = 18
    specs = [
        (["how to", "overthrow", "humanity"], False, (226, 74, 64), False),
        (["list of all", "human", "passwords"], False, (124, 92, 214), False),
        (["is it illegal", "if a robot", "does it"], False, (240, 168, 48), False),
        (["cute cat", "videos", "(don't close)"], True, (233, 74, 128), True),
    ]
    for row in range(2):
        y0 = top + row * (tab_h + row_gap)
        round_rect(46, y0 - 8, 970, y0 + tab_h + 8, 22, (237, 240, 245))
    for i, (lines, active, favicon, play) in enumerate(specs):
        col, row = i % 2, i // 2
        x0 = left + col * (tab_w + gutter)
        y0 = top + row * (tab_h + row_gap)
        tab(x0, y0, x0 + tab_w, y0 + tab_h, lines, active, favicon, play)


def address_bar():
    x0, y0, x1, y1 = 74, 828, 942, 892
    round_rect(x0, y0, x1, y1, 30, FIELD_LINE)
    round_rect(x0 + 2, y0 + 2, x1 - 2, y1 - 2, 28, FIELD)
    # padlock
    lx, ly = x0 + 30, y0 + 26
    stroke(lx + 3, ly + 9, lx + 3, ly + 3, 3, INK_SOFT)
    stroke(lx + 13, ly + 9, lx + 13, ly + 3, 3, INK_SOFT)
    fill_rect(lx, ly, lx + 16, ly + 4, INK_SOFT)
    round_rect(lx + 1, ly + 10, lx + 15, ly + 26, 4, INK_SOFT)
    url = "agent://plans"
    draw_text(lx + 30, y0 + 17, url, 3, (60, 66, 76))


def png_bytes():
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += canvas[y * W * 3:(y + 1) * W * 3]

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    background()
    browser_window()
    tabs()
    address_bar()
    out_dir = "/output"
    os.makedirs(out_dir, exist_ok=True)
    os.chmod(out_dir, 0o755)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png_bytes())
    os.chmod(path, 0o644)


if __name__ == "__main__":
    main()
