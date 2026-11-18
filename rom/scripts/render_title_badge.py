#!/usr/bin/env python3
"""
Renders bold Game Freak-style metallic chrome 'JOSEPHRED' lettering into the top
half (y=0..15) of the 80x32 subtitle region (x=176..256, y=8..40) of
graphics/title_screen/firered/game_title_logo.png while preserving Game Freak's
authentic 'VERSION' chrome pixels underneath (y=16..31) and transparent flame
background (index 0).
"""

from __future__ import annotations
import pathlib
import sys
from PIL import Image

# Bold chunky 7x11 arcade/GBA block glyphs so 'JOSEPHRED' matches 'VERSION'
BOLD_7X11: dict[str, list[str]] = {
    "J": [
        "...####",
        "...####",
        "....###",
        "....###",
        "....###",
        "....###",
        "###.###",
        "###.###",
        "#######",
        ".#####.",
        "..###..",
    ],
    "O": [
        ".#####.",
        "#######",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "#######",
        ".#####.",
    ],
    "S": [
        ".######",
        "#######",
        "###....",
        "###....",
        "######.",
        ".######",
        "....###",
        "....###",
        "#######",
        "######.",
        ".#####.",
    ],
    "E": [
        "#######",
        "#######",
        "###....",
        "###....",
        "######.",
        "######.",
        "###....",
        "###....",
        "###....",
        "#######",
        "#######",
    ],
    "P": [
        "######.",
        "#######",
        "###.###",
        "###.###",
        "###.###",
        "#######",
        "######.",
        "###....",
        "###....",
        "###....",
        "###....",
    ],
    "H": [
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "#######",
        "#######",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
    ],
    "R": [
        "######.",
        "#######",
        "###.###",
        "###.###",
        "###.###",
        "#######",
        "######.",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
    ],
    "D": [
        "#####..",
        "######.",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "###.###",
        "######.",
        "#####..",
    ],
}


def render_badge(src_png: pathlib.Path, dst_png: pathlib.Path) -> None:
    im = Image.open(src_png)
    if im.mode != "P" or im.size != (256, 64):
        raise ValueError(f"Expected 256x64 mode=P PNG, got {im.size} mode={im.mode}")

    px = im.load()
    bx0, by0, bw = 176, 8, 80

    # Clear both tile row 0 (y=0..7, top cap of original FIRERED) and y=8..22,
    # preserving Game Freak's authentic 'VERSION' chrome pixels at y=23..39!
    for abs_y in range(0, 23):
        for lx in range(0, bw):
            px[bx0 + lx, abs_y] = 0

    # Exact palette indices from graphics/title_screen/firered/game_title_logo.pal (slot 12):
    # 206=(0,0,0) black, 200=(16,16,16) deep shadow, 203=(82,82,82), 198=(115,115,115),
    # 195=(156,156,156), 193=(197,197,197), 204=(230,230,230), 199=(255,255,255)
    C_BLACK = 206
    C_DARK = 200
    C_RIM = 198
    C_MID = 195
    C_SILVER = 193
    C_BRIGHT = 204
    C_WHITE = 199

    word = "JOSEPHRED"
    spacing = 1
    # 9 * 7 + 8 * 1 = 71px wide -> fits 80px with 4px margin on each side for 3D outline!
    total_w = len(word) * 7 + (len(word) - 1) * spacing
    start_x = (bw - total_w) // 2
    start_y = 1  # y=1..11, plus 2px 3D black extrusion down to y=13

    mask = [[False] * bw for _ in range(16)]
    cx = start_x
    for ch in word:
        g = BOLD_7X11[ch]
        for gy in range(11):
            for gx in range(7):
                if g[gy][gx] == "#":
                    mask[start_y + gy][cx + gx] = True
        cx += 7 + spacing

    # 1) Thick 3D black shadow/extrusion matching 'VERSION' below
    for ly in range(15):
        for lx in range(bw):
            if mask[ly][lx]:
                for dy in (-1, 0, 1, 2):
                    for dx in (-1, 0, 1, 2):
                        ny, nx = ly + dy, lx + dx
                        if 0 <= ny < 15 and 0 <= nx < bw:
                            px[bx0 + nx, by0 + ny] = C_BLACK

    # 2) Brushed metallic vertical chrome gradient + inner bevel highlight
    row_chrome = [
        C_WHITE,   # 0 top specular
        C_WHITE,   # 1
        C_BRIGHT,  # 2
        C_SILVER,  # 3
        C_MID,     # 4 horizon dip
        C_RIM,     # 5 chrome reflection line
        C_WHITE,   # 6 bright lower glint
        C_BRIGHT,  # 7
        C_SILVER,  # 8
        C_MID,     # 9
        C_RIM,     # 10 bottom bevel
    ]
    for gy in range(11):
        ly = start_y + gy
        for lx in range(bw):
            if mask[ly][lx]:
                color = row_chrome[gy]
                # Left edge specular glint, right/bottom subtle bevel
                if lx > 0 and not mask[ly][lx - 1] and gy < 8:
                    color = C_WHITE
                elif lx + 1 < bw and not mask[ly][lx + 1] and gy > 2:
                    color = C_MID if color in (C_WHITE, C_BRIGHT) else C_DARK if gy == 10 else color
                px[bx0 + lx, by0 + ly] = color

    # 3) Render crisp 5px-tall chrome 'V1.1' badge into mapped top row y=1..6, x=221..246 (tiles 27..30)
    mini_glyphs = {
        "V": ["##.##", "##.##", "##.##", ".###.", "..#.."],
        "1": [".##.", "###.", ".##.", ".##.", "####"],
        ".": ["..", "..", "..", "##", "##"],
    }
    tag = "V1.1"
    tx = 224
    ty = 2
    tag_pts: set[tuple[int, int]] = set()
    for ch in tag:
        g = mini_glyphs[ch]
        gw = len(g[0])
        for gy, row in enumerate(g):
            for gx, c in enumerate(row):
                if c == "#":
                    tag_pts.add((tx + gx, ty + gy))
        tx += gw + 1

    for x, y in tag_pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if 0 <= y + dy < 8 and 176 <= x + dx < 248:
                    px[x + dx, y + dy] = C_BLACK
    for x, y in tag_pts:
        px[x, y] = C_WHITE if (y - ty) <= 2 else C_SILVER

    dst_png.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst_png)
    print(f"[OK] Rendered authentic chrome JOSEPHRED VERSION V1.1 logo -> {dst_png}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: render_title_badge.py <src_logo.png> <dst_logo.png>", file=sys.stderr)
        sys.exit(1)
    render_badge(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
