#!/usr/bin/env python3
"""
Converts all vanilla player (Ash/Red) sprite sheets in Pokemon FireRed
into Joseph (fluffy dark hair, no hat, friendly face with goatee,
charcoal crewneck T-shirt with Poke Ball emblem, blue jeans, sneakers).
"""

import sys
from pathlib import Path
from PIL import Image

def transform_overworld_pixel(x, y, v, facing, frame_w=16, frame_h=32):
    # Hair & Hat region (y: 8..20)
    if y <= 19:
        # Red / orange / yellow cap colors -> dark fluffy hair
        if v in (11, 12, 13, 14):
            # Rich textured dark hair (15=black, 8=dark brown)
            return 8 if (x + y) % 3 == 0 else 15
        elif v == 9: # White cap emblem
            if facing == 'S':
                return 8 if y <= 18 else 2 # forehead
            elif facing == 'W':
                return 8 if y <= 18 else 2
            else: # N
                return 8
        elif v == 6 and y == 19: # old cap visor rim -> hair/forehead
            return 2 if (facing == 'S' and 4 <= x <= 11) else 8

    # Face & Goatee (y: 20..23)
    if 20 <= y <= 23:
        if facing == 'S':
            # Add goatee/beard shadow along jawline
            if y in (22, 23) and 6 <= x <= 9 and v in (2, 3):
                return 4 # Dark skin stubble
        elif facing == 'W':
            if y in (22, 23) and 8 <= x <= 10 and v in (2, 3):
                return 4

    # Torso: Red jacket & yellow straps -> Charcoal tee + Poke Ball logo (y: 23..27)
    if 23 <= y <= 27:
        if v in (13, 14): # Yellow backpack straps
            if facing == 'S':
                return 15 if x in (5, 10) else 6
            elif facing == 'W':
                return 6
            else: # N
                return 6 if (x + y) % 2 == 0 else 15
        elif v in (11, 12): # Red jacket fabric
            return 15 if (x + y) % 2 == 0 else 6 # Charcoal fabric

    # Front-facing chest: Poke Ball graphic (y: 25..26, x: 7..8)
    if facing == 'S' and y in (25, 26) and x in (7, 8):
        if y == 25:
            return 11 # Top half red
        elif y == 26:
            return 9  # Bottom half white

    return v

def process_overworld_sheet(src_im, frame_w, frame_h, facing_list):
    out_im = Image.new('P', src_im.size)
    out_im.putpalette(src_im.getpalette())
    total_frames = src_im.size[0] // frame_w
    src_pixels = list(src_im.getdata())

    out_pixels = src_pixels[:]
    img_w, img_h = src_im.size

    for f_idx in range(total_frames):
        facing = facing_list[f_idx % len(facing_list)]
        offset_x = f_idx * frame_w
        for y in range(frame_h):
            for x in range(frame_w):
                idx = y * img_w + offset_x + x
                orig_v = src_pixels[idx]
                if orig_v != 0:
                    new_v = transform_overworld_pixel(x, y, orig_v, facing, frame_w, frame_h)
                    out_pixels[idx] = new_v

        # Add top tufts on hair for facing S, N, W (y=11)
        if frame_h == 32:
            for x_local in (5, 7, 9, 11):
                if x_local < frame_w:
                    idx_12 = 12 * img_w + offset_x + x_local
                    idx_11 = 11 * img_w + offset_x + x_local
                    if src_pixels[idx_12] != 0 and src_pixels[idx_11] == 0:
                        out_pixels[idx_11] = 8

    out_im.putdata(out_pixels)
    return out_im

def process_back_sprite(src_im):
    # 5 frames of 64x64
    out_im = Image.new('P', src_im.size)
    out_im.putpalette(src_im.getpalette())
    src_pixels = list(src_im.getdata())
    out_pixels = src_pixels[:]
    img_w = 64

    for f_idx in range(5):
        y_start = f_idx * 64
        for y_local in range(64):
            y_global = y_start + y_local
            for x in range(64):
                idx = y_global * img_w + x
                v = src_pixels[idx]
                if v == 0:
                    continue

                # Head area: y_local < 30
                if y_local < 28:
                    # Hat fabric (11=bright red, 12=dark red, 13=yellow) -> Dark fluffy hair
                    if v in (11, 12, 13, 14):
                        out_pixels[idx] = 8 if (x + y_local) % 3 == 0 else 15
                    elif v in (9, 10) and y_local < 25: # Hat highlights
                        out_pixels[idx] = 8 if (x + y_local) % 2 == 0 else 4

                # Torso / Clothes: y_local >= 28
                else:
                    # Red vest -> Charcoal crewneck tee
                    if v in (11, 12):
                        out_pixels[idx] = 15 if (x + y_local) % 2 == 0 else 6
                    # Yellow backpack straps -> Charcoal fabric
                    elif v in (13, 14):
                        out_pixels[idx] = 6 if (x + y_local) % 2 == 0 else 15
                    # Blue backpack -> blend into charcoal tee back
                    elif v in (5, 7) and y_local < 52 and x < 40:
                        out_pixels[idx] = 6 if (x + y_local) % 2 == 0 else 15

    out_im.putdata(out_pixels)
    return out_im

def process_map_icon(src_im):
    # 16x16 icon
    out_im = Image.new('P', src_im.size)
    out_im.putpalette(src_im.getpalette())
    src_pixels = list(src_im.getdata())
    out_pixels = src_pixels[:]

    for y in range(16):
        for x in range(16):
            idx = y * 16 + x
            v = src_pixels[idx]
            if v == 0:
                continue
            # Hat region: rows 2..8
            if y <= 7:
                if v in (11, 12, 13, 14): # Red hat
                    out_pixels[idx] = 8 if (x + y) % 3 == 0 else 15
                elif v == 9: # White logo
                    out_pixels[idx] = 8
            # Forehead: row 8
            elif y == 8:
                if v in (6, 9):
                    out_pixels[idx] = 2 if 5 <= x <= 10 else 8
            # Beard / Goatee: rows 12..14
            elif y in (12, 13, 14) and 6 <= x <= 9:
                if v in (2, 3):
                    out_pixels[idx] = 4

    out_im.putdata(out_pixels)
    return out_im

def main():
    root = Path(__file__).resolve().parent.parent
    overrides = root / "overrides"

    # Targets to create in overrides
    targets = [
        # (src_name, dst_rel, type, frame_w, frame_h, facing)
        ("red_normal.png", "graphics/object_events/pics/people/red_normal.png", "overworld", 16, 32, ['S', 'N', 'W', 'S', 'S', 'N', 'N', 'W', 'W']),
        ("red_surf_run.png", "graphics/object_events/pics/people/red_surf_run.png", "overworld", 16, 32, ['S', 'S', 'S', 'N', 'N', 'N', 'W', 'W', 'W', 'S', 'N', 'W', 'W', 'W']),
        ("red_bike.png", "graphics/object_events/pics/people/red_bike.png", "overworld", 32, 32, ['S', 'N', 'W', 'S', 'S', 'N', 'N', 'W']),
        ("red_surf.png", "graphics/object_events/pics/people/red_surf.png", "overworld", 32, 32, ['S', 'N', 'W', 'W']),
        ("red_fish.png", "graphics/object_events/pics/people/red_fish.png", "overworld", 32, 32, ['S', 'N', 'W', 'W']),
        ("red_item.png", "graphics/object_events/pics/people/red_item.png", "overworld", 16, 32, ['S']),
        ("red_vs_seeker_bike.png", "graphics/object_events/pics/people/red_vs_seeker_bike.png", "overworld", 32, 32, ['S', 'N', 'W', 'S', 'N', 'W']),
        ("player_icon_red.png", "graphics/region_map/player_icon_red.png", "icon", 16, 16, []),
    ]

    scratch = root.parent / "scratch"

    for src_name, dst_rel, stype, fw, fh, facings in targets:
        src_path = scratch / src_name
        if not src_path.exists():
            print(f"[WARN] {src_path} not found")
            continue
        im = Image.open(src_path)
        if stype == "overworld":
            res = process_overworld_sheet(im, fw, fh, facings)
        elif stype == "back":
            res = process_back_sprite(im)
        elif stype == "icon":
            res = process_map_icon(im)

        dst_path = overrides / dst_rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        res.save(dst_path)
        print(f"[OK] Generated {dst_path.relative_to(overrides)}")

if __name__ == "__main__":
    main()
