#!/usr/bin/env python3
"""
Converts all vanilla player (Red/Ash) overworld & Town Map sprite sheets in
Pokemon FireRed into Joseph:
  - Dynamic per-frame head-top detection (handles walking, sprinting, surfing,
    biking, and fishing head bobbing cleanly with zero leftover cap brims)
  - Fluffy dark espresso/black hair (no cap, no headband visor, trimmed profile bill)
  - Clean forehead, eyes, and subtle goatee stubble
  - Solid charcoal crewneck T-shirt with chest Poke Ball graphic & blue denim jeans
"""

from pathlib import Path
from PIL import Image

# Palette indices in graphics/object_events/palettes/player.pal:
#  0: transparent
#  1: #ac7b41 warm brown
#  2: #ffc594 light skin
#  3: #de9473 mid skin
#  4: #7b4141 dark brown (hair midtone / beard stubble)
#  5: #4141d5 bright denim blue
#  6: #39397b dark slate-navy (charcoal-blue shadow / jeans shadow)
#  7: #73a4c5 light denim highlight
#  8: #6a2929 deep espresso brown (hair body)
#  9: #eeeeff crisp white
# 10: #b4b4d5 cool gray
# 11: #ff6a4a vivid red
# 12: #c53939 crimson red
# 13: #ffde5a bright yellow
# 14: #bd9c39 dark gold
# 15: #000000 pure black / charcoal


def find_head_bounds(frame_px: list[list[int]], fw: int, fh: int, sheet_kind: str) -> tuple[int, int, int]:
    """
    Finds (head_top_y, head_left_x, head_right_x) for a single frame by locating
    the red cap crown (colors 11, 12) in the upper body and stepping 1 row up to
    the cap's top outline (color 8/15).
    """
    # On red_item frames 2..4, a held item/ball can sit above y=12 ONLY in hand columns,
    # Wait: in red_item, Red holds the item in front of chest OR above head? Let's check:
    # In audit_sprites.png row 4, Red holds items in front of his chest (y ~ 21..26)!
    # So the cap crown is ALWAYS the topmost cluster of (11, 12) in y = 4..23!
    red_rows: list[tuple[int, list[int]]] = []
    for y in range(2, min(25, fh)):
        xs = [x for x in range(fw) if frame_px[y][x] in (11, 12)]
        if len(xs) >= 4:
            red_rows.append((y, xs))

    if not red_rows:
        # Fallback if a frame has tiny/tilted crown
        for y in range(2, min(25, fh)):
            xs = [x for x in range(fw) if frame_px[y][x] in (11, 12)]
            if len(xs) >= 2:
                red_rows.append((y, xs))

    first_red_y = red_rows[0][0]
    # Top outline of cap is 1 row above first_red_y
    top_y = max(0, first_red_y - 1)
    crown_xs = [x for _, xs in red_rows[:5] for x in xs]
    left_x = max(0, min(crown_xs) - 1)
    right_x = min(fw - 1, max(crown_xs) + 1)
    return top_y, left_x, right_x


def hair_shade(x: int, dy: int, cx: float) -> int:
    """Natural layered dark fluffy hair without geometric stripes."""
    dist = abs(x - cx)
    if dy <= 0:
        return 15 if int(round(dist)) % 2 == 0 else 8
    if dy in (1, 2) and dist <= 2.2:
        return 4 if (x + dy) % 3 == 0 else 8
    if dy <= 4 and dist <= 3.5:
        return 8 if (x * 3 + dy) % 4 != 0 else 15
    return 15 if dist >= 4.2 else 8


def process_overworld_frame(
    frame_px: list[list[int]],
    fw: int,
    fh: int,
    facing: str,
    sheet_kind: str,
) -> list[list[int]]:
    out = [row[:] for row in frame_px]
    top_y, hx0, hx1 = find_head_bounds(frame_px, fw, fh, sheet_kind)
    cx = (hx0 + hx1) / 2.0

    # 1. Trim protruding baseball cap bill on West / East profile frames first
    if facing == "W":
        for dy in range(3, 8):
            y = top_y + dy
            if 0 <= y < fh:
                # Cap bill sticks out 2px on the far left (hx0 - 2 .. hx0)
                for x in range(max(0, hx0 - 3), hx0 + 1):
                    if frame_px[y][x] in (15, 9, 10, 8, 12):
                        out[y][x] = 0
                # Restore crisp black front hair outline at hx0 + 1
                if hx0 + 1 < fw and out[y][hx0 + 1] != 0:
                    out[y][hx0 + 1] = 15
    elif facing == "E":
        for dy in range(3, 8):
            y = top_y + dy
            if 0 <= y < fh:
                for x in range(hx1, min(fw, hx1 + 4)):
                    if frame_px[y][x] in (15, 9, 10, 8, 12):
                        out[y][x] = 0
                if hx1 - 1 >= 0 and out[y][hx1 - 1] != 0:
                    out[y][hx1 - 1] = 15

    # 2. Transform head, visor, face, and torso relative to top_y
    for y in range(fh):
        dy = y - top_y
        for x in range(fw):
            v = out[y][x]
            if v == 0:
                continue

            # Keep fishing rods & held items outside head/body columns untouched
            if sheet_kind == "fish":
                # Rod pixels extend outside [hx0-1 .. hx1+1] or below hands
                if x < hx0 - 1 or x > hx1 + 1:
                    continue

            # A. Upper Hair Crown (dy = 0..6)
            if 0 <= dy <= 6 and (hx0 - 2 <= x <= hx1 + 2):
                if v in (8, 9, 10, 11, 12, 13, 14):
                    out[y][x] = hair_shade(x, dy, cx)
                elif v == 6:
                    out[y][x] = 15

            # B. Visor & Forehead Zone (dy = 7..8) — eliminates white/blue headband completely!
            elif dy == 7 and (hx0 - 2 <= x <= hx1 + 2):
                if facing == "S":
                    if v in (9, 10, 6, 11, 12):
                        # Center forehead skin peek with a slight center hair quiff, dark hair at temples
                        if abs(x - cx) <= 0.6:
                            out[y][x] = 8  # front quiff tip dipping at center hairline
                        elif abs(x - cx) <= 2.6:
                            out[y][x] = 3  # warm upper forehead skin
                        else:
                            out[y][x] = 15
                    elif v == 1:
                        out[y][x] = 15
                elif facing == "N":
                    if v in (9, 10, 6, 11, 12, 1):
                        out[y][x] = hair_shade(x, dy, cx)
                elif facing == "W":
                    if v in (9, 10, 6, 11, 12):
                        out[y][x] = 3 if x <= cx - 1.5 else hair_shade(x, dy, cx)
                elif facing == "E":
                    if v in (9, 10, 6, 11, 12):
                        out[y][x] = 3 if x >= cx + 1.5 else hair_shade(x, dy, cx)

            elif dy == 8 and (hx0 - 2 <= x <= hx1 + 2):
                if facing == "S":
                    # Row directly above eyes: must be clean skin forehead in center, hair/sideburns at edges!
                    if v in (6, 9, 10, 11, 12):
                        out[y][x] = 2 if abs(x - cx) <= 2.2 else 3
                    elif v == 4:
                        out[y][x] = 15  # crisp sideburn
                elif facing == "N":
                    if v in (8, 9, 10, 11, 12, 6, 1, 4):
                        out[y][x] = 15 if abs(x - cx) >= 3.0 else 8
                elif facing == "W":
                    if v in (6, 9, 10, 11, 12):
                        out[y][x] = 2 if x <= cx - 1.0 else 15
                    elif v in (8, 4) and x >= cx - 0.5:
                        out[y][x] = 15 if x >= cx + 2.0 else 8
                elif facing == "E":
                    if v in (6, 9, 10, 11, 12):
                        out[y][x] = 2 if x >= cx + 1.0 else 15
                    elif v in (8, 4) and x <= cx + 0.5:
                        out[y][x] = 15 if x <= cx - 2.0 else 8

            # C. Lower Nape / Sideburns / Goatee Zone (dy = 9..11)
            elif 9 <= dy <= 11 and (hx0 - 2 <= x <= hx1 + 2):
                if facing == "N":
                    if v in (1, 4, 8, 11, 12, 6, 9, 10):
                        out[y][x] = 15 if dy >= 10 or abs(x - cx) >= 2.5 else 8
                elif facing == "S":
                    # Sprinting/jumping South frames tilt head forward 1px, putting visor (6/9/10) at dy=9!
                    if dy in (9, 10) and v in (6, 9, 10):
                        out[y][x] = 2 if abs(x - cx) <= 2.2 else 3
                    elif v in (11, 12) and sheet_kind not in ("item", "vs_seeker"):
                        out[y][x] = 15
                    # Subtle goatee shadow right at chin center (dy == 10..11)
                    if dy == 10 and abs(x - cx) <= 0.8 and out[y][x] in (2, 3):
                        out[y][x] = 4
                elif facing in ("W", "E"):
                    if dy == 9 and v in (6, 9, 10):
                        out[y][x] = 2
                    elif v == 1:
                        out[y][x] = 8
                    if dy == 10 and (
                        (facing == "W" and x <= cx - 2.0) or (facing == "E" and x >= cx + 2.0)
                    ) and out[y][x] in (2, 3):
                        out[y][x] = 4

            # D. Torso: Solid Charcoal T-Shirt (dy = 11..15)
            if 11 <= dy <= 16 and (hx0 - 1 <= x <= hx1 + 1):
                if sheet_kind in ("item", "vs_seeker"):
                    # Preserve held item/Poke Ball/VS Seeker, convert open red vest & straps on torso
                    if v in (11, 12, 13, 14) and (dy <= 13 or abs(x - cx) >= 1.8 or sheet_kind == "vs_seeker"):
                        out[y][x] = 15
                else:
                    if v in (11, 12, 13, 14):
                        # Solid dark charcoal tee (15) with subtle slate shoulder highlight (6) on outer edge
                        out[y][x] = 6 if abs(x - cx) >= 2.8 and dy <= 13 else 15
                    elif facing == "S" and dy in (13, 14) and v in (9, 10) and abs(x - cx) <= 1.2:
                        # Clean existing white/gray zip into charcoal before placing Poke Ball logo
                        out[y][x] = 15

    # 3. Add fluffy forward-and-up hair tufts at top_y - 1 so silhouette isn't a flat dome
    tuft_y = top_y - 1
    if tuft_y >= 0:
        icx = int(round(cx))
        for tx, col in [(icx - 2, 15), (icx - 1, 8), (icx, 15), (icx + 1, 8), (icx + 2, 15)]:
            if 0 <= tx < fw and out[top_y][tx] != 0 and out[tuft_y][tx] == 0:
                out[tuft_y][tx] = col

    # 4. Crisp 2x2 Poke Ball graphic on front of charcoal tee for standard South frames
    if facing == "S" and sheet_kind in ("normal", "run"):
        icx = int(round(cx))
        y_top = top_y + 13
        y_bot = top_y + 14
        if y_bot < fh:
            for bx in (icx, icx + 1) if (hx1 - hx0) % 2 == 1 else (icx - 1, icx):
                if 0 <= bx < fw and out[y_top][bx] in (15, 6, 10, 11, 12):
                    out[y_top][bx] = 11  # Red upper half
                if 0 <= bx < fw and out[y_bot][bx] in (15, 6, 9, 10, 11, 12):
                    out[y_bot][bx] = 9   # White lower half

    return out


def process_overworld_sheet(src_im: Image.Image, fw: int, fh: int, facings: list[str], sheet_kind: str) -> Image.Image:
    out_im = Image.new("P", src_im.size)
    out_im.putpalette(src_im.getpalette())
    img_w, img_h = src_im.size
    n_frames = img_w // fw
    assert len(facings) == n_frames, f"Expected {n_frames} facings, got {len(facings)}"

    src_px = src_im.load()
    dst_px = out_im.load()

    for f_idx in range(n_frames):
        ox = f_idx * fw
        grid = [[src_px[ox + x, y] for x in range(fw)] for y in range(fh)]
        conv = process_overworld_frame(grid, fw, fh, facings[f_idx], sheet_kind)
        for y in range(fh):
            for x in range(fw):
                dst_px[ox + x, y] = conv[y][x]

    return out_im


def process_map_icon(src_im: Image.Image) -> Image.Image:
    """16x16 Town Map head icon for Joseph (no cap, fluffy dark hair, clean forehead, goatee)."""
    out_im = src_im.copy()
    px = out_im.load()

    for y in range(16):
        for x in range(16):
            v = px[x, y]
            if v == 0:
                continue
            # Crown & cap (y <= 7)
            if y <= 7:
                if v in (11, 12, 9, 10, 8):
                    px[x, y] = 8 if (2 <= y <= 5 and 5 <= x <= 10 and (x + y) % 2 == 0) else 15
                elif v == 6:
                    px[x, y] = 15
            # Visor rows (y = 8..9) -> clean hairline + warm forehead skin!
            elif y == 8:
                if v in (9, 10, 6, 11, 12):
                    if x in (7, 8):
                        px[x, y] = 8
                    elif 5 <= x <= 10:
                        px[x, y] = 3
                    else:
                        px[x, y] = 15
                elif v == 1:
                    px[x, y] = 15
            elif y == 9:
                if v in (6, 9, 10, 11, 12):
                    px[x, y] = 2 if 5 <= x <= 10 else 15
                elif v == 4:
                    px[x, y] = 15
            # Chin / goatee shadow (y = 12..14)
            elif y in (12, 13) and x in (7, 8) and v in (2, 3):
                px[x, y] = 4

    # Add small fluffy crown tufts at y=1 if y=2 has hair
    for tx, col in [(6, 15), (7, 8), (8, 15), (9, 8)]:
        if px[tx, 2] != 0 and px[tx, 1] == 0:
            px[tx, 1] = col

    return out_im


def main() -> None:
    rom_root = Path(__file__).resolve().parent.parent
    upstream_gfx = rom_root / "upstream-pokefirered/graphics"
    overrides = rom_root / "overrides/graphics"

    sheets = [
        (
            "object_events/pics/people/red_normal.png",
            16, 32,
            ["S", "N", "W", "S", "S", "N", "N", "W", "W"],
            "normal",
        ),
        (
            "object_events/pics/people/red_surf_run.png",
            16, 32,
            ["S", "N", "W", "S", "S", "S", "N", "N", "N", "W", "W", "W", "S", "S"],
            "run",
        ),
        (
            "object_events/pics/people/red_bike.png",
            32, 32,
            ["S", "N", "W", "S", "S", "N", "N", "W", "W"],
            "bike",
        ),
        (
            "object_events/pics/people/red_surf.png",
            32, 32,
            ["S", "S", "N", "N", "W", "W", "S", "N", "E"],
            "surf",
        ),
        (
            "object_events/pics/people/red_fish.png",
            32, 32,
            ["E", "E", "E", "E", "N", "N", "N", "N", "S", "S", "S", "S"],
            "fish",
        ),
        (
            "object_events/pics/people/red_item.png",
            16, 32,
            ["S"] * 9,
            "item",
        ),
        (
            "object_events/pics/people/red_vs_seeker_bike.png",
            32, 32,
            ["S"] * 6,
            "vs_seeker",
        ),
    ]

    for rel, fw, fh, facings, kind in sheets:
        src = Image.open(upstream_gfx / rel)
        conv = process_overworld_sheet(src, fw, fh, facings, kind)
        dst = overrides / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        conv.save(dst)
        print(f"[OK] {rel}")

    icon_rel = "region_map/player_icon_red.png"
    icon_conv = process_map_icon(Image.open(upstream_gfx / icon_rel))
    icon_dst = overrides / icon_rel
    icon_dst.parent.mkdir(parents=True, exist_ok=True)
    icon_conv.save(icon_dst)
    print(f"[OK] {icon_rel}")


if __name__ == "__main__":
    main()
