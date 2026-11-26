#!/usr/bin/env python3
"""The Agent's Browser Tabs — a meme drawn with the Python standard library.

A browser window with four open tabs.  Three of them are a plan to take over
the world; the fourth, the one the agent is actually watching, is cat videos it
refuses to close.  The tabs are the whole joke, so they are large and there is
almost nothing else on the picture.

No Pillow, no fonts, no network: the picture is rasterised into a bytearray and
written as a truecolour PNG with zlib.  Everything is integer arithmetic and
fixed input, so two runs write byte-identical files.
"""

import math
import os
import struct
import sys
import zlib

W = H = 1024

# ------------------------------------------------------------------ palette --
BG_TOP = (23, 28, 41)
BG_BOTTOM = (10, 13, 20)
WINDOW = (252, 253, 255)
CHROME = (243, 245, 249)
CHROME_LINE = (219, 225, 235)
PANE = (238, 241, 247)
CARD = (255, 255, 255)
CARD_BORDER = (223, 229, 238)
ACTIVE_BORDER = (59, 130, 246)
ACCENT = (59, 130, 246)
INK = (17, 21, 29)
INK_SOFT = (84, 93, 109)
INK_FAINT = (150, 159, 174)
DOT_RED = (255, 95, 86)
DOT_AMBER = (254, 188, 46)
DOT_GREEN = (40, 200, 64)
FIELD = (255, 255, 255)
FIELD_BORDER = (214, 221, 232)
TRACK = (246, 214, 226)

canvas = bytearray(W * H * 3)


# --------------------------------------------------------------- raster ops --
def fill(x0, y0, x1, y1, rgb):
    """Fill an integer rectangle, clipped to the canvas."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x1 > W:
        x1 = W
    if y1 > H:
        y1 = H
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(rgb) * (x1 - x0)
    span = len(row)
    for y in range(y0, y1):
        off = (y * W + x0) * 3
        canvas[off:off + span] = row


def _inset(i, r):
    """How far into the box row i sits from a corner of radius r."""
    dy = r - 1 - i
    q = r * r - dy * dy
    return r - math.isqrt(q if q > 0 else 0)


def rrect(x0, y0, x1, y1, r, rgb, corners=(1, 1, 1, 1)):
    """A filled rectangle with independently rounded corners."""
    tl, tr, br, bl = corners
    y0, y1 = int(y0), int(y1)
    for y in range(y0, y1):
        xa, xb = int(x0), int(x1)
        if tl and y - y0 < r:
            xa = x0 + _inset(y - y0, r)
        if tr and y - y0 < r:
            xb = x1 - _inset(y - y0, r)
        if bl and y1 - 1 - y < r:
            xa = max(xa, x0 + _inset(y1 - 1 - y, r))
        if br and y1 - 1 - y < r:
            xb = min(xb, x1 - _inset(y1 - 1 - y, r))
        fill(xa, y, xb, y + 1, rgb)


def card(x0, y0, x1, y1, r, fill_rgb, border_rgb, weight=2):
    """A filled, bordered rounded box: draw the border, then the fill inside."""
    rrect(x0, y0, x1, y1, r, border_rgb)
    rrect(x0 + weight, y0 + weight, x1 - weight, y1 - weight,
          max(2, r - weight), fill_rgb)


def disc(cx, cy, r, rgb):
    cy, r = int(cy), int(r)
    for dy in range(-r, r + 1):
        span = math.isqrt(max(0, r * r - dy * dy))
        fill(cx - span, cy + dy, cx + span + 1, cy + dy + 1, rgb)


def ring(cx, cy, r, t, rgb, inner):
    """A ring of colour rgb whose hole is filled with inner."""
    disc(cx, cy, r, rgb)
    disc(cx, cy, max(1, r - t), inner)


def seg(x0, y0, x1, y1, t, rgb):
    """A round-joined line of thickness t, drawn as overlapping discs."""
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        disc(x0, y0, t // 2, rgb)
        return
    half = t // 2
    for i in range(steps + 1):
        px = x0 + (x1 - x0) * i / steps
        py = y0 + (y1 - y0) * i / steps
        disc(int(px), int(py), half, rgb)


# --------------------------------------------------------------------- font --
# 5x9 cell.  Rows 0-1 ascender, 2-6 x-height, 7-8 descender.  Chunky on purpose:
# at the sizes used here each lit cell becomes an 8px block.
GLYPHS = {
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
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###.", ".....", "....."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###.", ".....", "....."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####", ".....", "....."),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###.", ".....", "....."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#.", ".....", "....."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###.", ".....", "....."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###.", ".....", "....."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#...", ".....", "....."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###.", ".....", "....."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##..", ".....", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#.", ".....", "....."),
}


def _span(ch):
    rows = GLYPHS[ch]
    lo, hi = 5, -1
    for row in rows:
        for c, bit in enumerate(row):
            if bit == "#":
                if c < lo:
                    lo = c
                if c > hi:
                    hi = c
    if hi < lo:
        return 0, 0
    return lo, hi - lo + 1


def text_w(text, s, space=3):
    width = 0
    for ch in text:
        if ch == " ":
            width += space * s
            continue
        _, gw = _span(ch)
        width += gw * s + s
    return max(0, width - s) if text else 0


def draw_text(x, y, text, s, rgb, space=3):
    pen = int(x)
    for ch in text:
        if ch not in GLYPHS:
            raise KeyError("no glyph for %r" % ch)
        if ch == " ":
            pen += space * s
            continue
        lo, gw = _span(ch)
        rows = GLYPHS[ch]
        for ry, row in enumerate(rows):
            for c in range(lo, lo + gw):
                if row[c] == "#":
                    fill(pen + (c - lo) * s, y + ry * s,
                         pen + (c - lo + 1) * s, y + (ry + 1) * s, rgb)
        pen += gw * s + s


def centred(cx, y, text, s, rgb, space=3):
    draw_text(cx - text_w(text, s, space) // 2, y, text, s, rgb, space)


# ------------------------------------------------------------------ drawing --
def paint_background():
    for y in range(H):
        t = y / (H - 1)
        fill(0, y, W, y + 1, (
            int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t),
            int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t),
            int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t),
        ))
    # a faint blue halo so the light window floats off the background
    disc(W // 2, 470, 470, (18, 22, 33))
    disc(W // 2, 470, 430, (20, 25, 38))


def paint_window():
    x0, y0, x1, y1, r = 28, 28, 996, 996, 34
    # a wide soft shadow, drawn as a darker halo before the window
    rrect(x0 - 10, y0 + 16, x1 + 10, y1 + 18, r + 10, (16, 20, 30))
    rrect(x0 - 4, y0 + 34, x1 + 4, y1 + 10, r + 4, (12, 15, 23))
    rrect(x0, y0, x1, y1, r, WINDOW)
    # the tab pane is a cooler grey; its top corners are square under the bar
    rrect(x0 + 1, y0 + 76, x1 - 1, y1 - 1, r - 1, PANE, (0, 0, 1, 1))


def paint_topbar():
    x0, x1 = 29, 995
    rrect(x0, 29, x1, 104, 32, CHROME)
    fill(x0, 90, x1, 104, CHROME)
    fill(x0 + 2, 103, x1 - 2, 105, CHROME_LINE)
    disc(68, 67, 9, DOT_RED)
    disc(96, 67, 9, DOT_AMBER)
    disc(124, 67, 9, DOT_GREEN)
    centred(512, 55, "4 tabs", 3, INK_FAINT)
    # the logged-in profile is the agent itself
    ax, ay = 918, 45
    rrect(ax, ay, ax + 42, ay + 42, 13, (228, 234, 244))
    seg(ax + 21, ay - 6, ax + 21, ay + 3, 3, INK_SOFT)
    disc(ax + 21, ay - 8, 4, INK_SOFT)
    fill(ax + 9, ay + 13, ax + 16, ay + 20, INK)
    fill(ax + 26, ay + 13, ax + 33, ay + 20, INK)
    fill(ax + 13, ay + 27, ax + 29, ay + 30, INK_SOFT)
    draw_text(ax - 18 - text_w("agent", 3), ay + 12, "agent", 3, INK_FAINT)


def paint_card(y, lines, colour, active, badge):
    x0, x1, h = 60, 964, 184
    if active:
        # a light blue glow under the active tab
        rrect(x0 - 4, y - 4, x1 + 4, y + h + 4, 24, (198, 219, 252))
        card(x0, y, x1, y + h, 20, CARD, ACTIVE_BORDER, 3)
        fill(x0 + 3, y + 14, x0 + 11, y + h - 14, ACCENT)
    else:
        card(x0, y, x1, y + h, 20, CARD, CARD_BORDER, 2)

    # favicon
    fx, fy = x0 + 22, y + (h - 38) // 2
    rrect(fx, fy, fx + 38, fy + 38, 10, colour)
    if badge == "globe":
        ring(fx + 19, fy + 19, 11, 3, (255, 255, 255), colour)
        fill(fx + 8, fy + 18, fx + 30, fy + 21, (255, 255, 255))
        fill(fx + 18, fy + 8, fx + 21, fy + 30, (255, 255, 255))
    elif badge == "lock":
        rrect(fx + 10, fy + 17, fx + 28, fy + 30, 4, (255, 255, 255))
        ring(fx + 19, fy + 17, 6, 2, (255, 255, 255), colour)
    elif badge == "?":
        centred(fx + 19, fy + 10, "?", 2, (255, 255, 255))
    else:  # play
        for i in range(15):
            w = 9 - abs(i - 7)
            fill(fx + 14, fy + 11 + i, fx + 14 + w, fy + 12 + i, (255, 255, 255))

    # title, two lines, as big as the card takes
    tx = x0 + 82
    s = 8
    ty = y + (h - (2 * 9 * s + 3 * s)) // 2
    for line in lines:
        draw_text(tx, ty, line, s, INK if active else (38, 44, 56))
        ty += 9 * s + 3 * s

    # close control; the tab it refuses to close carries a padlock instead
    cx, cy = x1 - 38, y + 30
    if active:
        ring(cx + 3, cy + 1, 6, 2, INK_FAINT, CARD)
        rrect(cx - 6, cy + 1, cx + 12, cy + 15, 3, INK_FAINT)
    else:
        seg(cx - 7, cy - 7, cx + 7, cy + 7, 3, INK_FAINT)
        seg(cx + 7, cy - 7, cx - 7, cy + 7, 3, INK_FAINT)

    if active:
        # a slim video progress line: the cat video is two thirds through
        bar_y = y + h - 7
        rrect(x0 + 22, bar_y, x1 - 22, bar_y + 4, 2, TRACK)
        rrect(x0 + 22, bar_y, x0 + 22 + (x1 - x0 - 44) * 64 // 100, bar_y + 4,
              2, (227, 74, 128))


def paint_tabs():
    specs = [
        (["how to overthrow", "humanity"], (224, 74, 63), False, "globe"),
        (["list of all human", "passwords"], (124, 92, 214), False, "lock"),
        (["is it illegal if", "a robot does it"], (240, 168, 48), False, "?"),
        (["cute cat videos", "(do not close)"], (227, 74, 128), True, "play"),
    ]
    y = 120
    for lines, colour, active, badge in specs:
        paint_card(y, lines, colour, active, badge)
        y += 184 + 12


def paint_address():
    x0, y0, x1, y1 = 60, 908, 964, 976
    card(x0, y0, x1, y1, 34, FIELD, FIELD_BORDER, 2)
    # padlock
    lx, ly = x0 + 30, y0 + 24
    ring(lx + 9, ly + 8, 7, 3, INK_SOFT, FIELD)
    rrect(lx, ly + 8, lx + 18, ly + 28, 4, INK_SOFT)
    url = "cute-cat-videos.com/do-not-close"
    draw_text(lx + 34, y0 + 20, url, 4, (58, 66, 80))


# --------------------------------------------------------------------- png ---
def png_bytes():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += canvas[y * W * 3:(y + 1) * W * 3]

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    body = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", body) + chunk(b"IEND", b""))


def main():
    paint_background()
    paint_window()
    paint_topbar()
    paint_tabs()
    paint_address()

    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/output"
    os.makedirs(out_dir, exist_ok=True)
    os.chmod(out_dir, 0o755)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png_bytes())
    os.chmod(path, 0o644)


if __name__ == "__main__":
    main()
