#!/usr/bin/env python3
"""
Generates Joseph's 5-frame GBA battle back-sprite (64x320 4bpp P-mode) and
dedicated 16-color palette from rom/assets/joseph_battle_back_source.jpg.
"""

from pathlib import Path
import numpy as np
from PIL import Image

PALETTE_COLORS = [
    (115, 197, 164),  # 0: Transparent key (mint green)
    (16, 16, 24),     # 1: Deep black / outline
    (248, 248, 248),  # 2: Pure white
    (224, 40, 32),    # 3: Vivid red
    (40, 32, 40),     # 4: Dark hair shadow
    (48, 48, 64),     # 5: Charcoal T-shirt base
    (48, 72, 104),    # 6: Denim blue base
    (72, 112, 152),   # 7: Denim blue highlight
    (232, 176, 136),  # 8: Skin light
    (144, 96, 80),    # 9: Skin shadow
    (88, 80, 80),     # 10: Hair / stubble
    (200, 136, 112),  # 11: Skin midtone
    (72, 40, 40),     # 12: Hair midtone
    (216, 216, 216),  # 13: Light gray
    (152, 152, 152),  # 14: Mid gray / shirt highlight
    (168, 128, 96),   # 15: Warm accent
]


def rgb_dist(c1, c2) -> int:
    dr = int(c1[0]) - int(c2[0])
    dg = int(c1[1]) - int(c2[1])
    db = int(c1[2]) - int(c2[2])
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


def find_closest_palette_index(rgb) -> int:
    best_idx = 1
    best_d = 1 << 30
    for idx in range(1, 16):
        d = rgb_dist(rgb, PALETTE_COLORS[idx])
        if d < best_d:
            best_d = d
            best_idx = idx
    return best_idx


def is_background(rgb, bg_ref) -> bool:
    return rgb_dist(rgb, bg_ref) < 1200


def process() -> None:
    rom_root = Path(__file__).resolve().parent.parent
    raw_path = rom_root / "assets/joseph_battle_back_source.jpg"
    im_raw = Image.open(raw_path).convert("RGB")
    arr_raw = np.array(im_raw)
    bg_ref = arr_raw[10, 10]

    boxes = [
        (42, 195, 280, 535),    # 0: Stance
        (325, 195, 530, 530),   # 1: Wind-up
        (580, 200, 772, 530),   # 2: High wind-up
        (820, 200, 1120, 530),  # 3: Release
        (1140, 200, 1351, 530), # 4: Follow-through
    ]

    target_h = 48
    out_frames: list[Image.Image] = []

    flat_pal: list[int] = []
    for c in PALETTE_COLORS:
        flat_pal.extend(c)
    flat_pal.extend([0] * (768 - len(flat_pal)))

    for f_idx, box in enumerate(boxes):
        crop = im_raw.crop(box)
        crop_arr = np.array(crop)

        # Frame 0: remove duplicate Poke Ball from passive left hand (keep right-hand ball!)
        if f_idx == 0:
            for y in range(250, crop_arr.shape[0]):
                for x in range(0, 60):
                    r, g, b = int(crop_arr[y, x, 0]), int(crop_arr[y, x, 1]), int(crop_arr[y, x, 2])
                    if (r > 135 and g < 115) or (r > 195 and g > 195 and b > 195):
                        crop_arr[y, x] = [184, 128, 104]

        # Frame 1: clean cyan fringe on left elbow
        if f_idx == 1:
            for y in range(220, crop_arr.shape[0]):
                for x in range(0, 25):
                    p = crop_arr[y, x]
                    if int(p[2]) > int(p[0]) + 30:
                        crop_arr[y, x] = bg_ref

        # Frames 2 & 3: clean stray chest-emblem pixels floating on side of charcoal shirt
        if f_idx in (2, 3):
            for y in range(185, 290):
                for x in range(95, min(195, crop_arr.shape[1])):
                    r, g, b = int(crop_arr[y, x, 0]), int(crop_arr[y, x, 1]), int(crop_arr[y, x, 2])
                    if (r > 150 and g < 100) or (r > 180 and g > 180 and b > 180):
                        crop_arr[y, x] = [44, 44, 58]

        if f_idx == 3:
            for y in range(150, crop_arr.shape[0]):
                for x in range(270, crop_arr.shape[1]):
                    crop_arr[y, x] = bg_ref

        cleaned = Image.fromarray(crop_arr)
        w, h = cleaned.size
        scale = target_h / float(h)
        new_w = max(1, int(round(w * scale)))
        new_h = target_h

        resized = cleaned.resize((new_w, new_h), Image.Resampling.LANCZOS)
        res_arr = np.array(resized)

        frame = Image.new("P", (64, 64), 0)
        frame.putpalette(flat_pal)

        if f_idx == 0:
            x_offset = (64 - new_w) // 2 + 3
        elif f_idx == 1:
            x_offset = (64 - new_w) // 2
        elif f_idx in (2, 4):
            x_offset = (64 - new_w) // 2 - 2
        else:
            x_offset = 64 - new_w - 2

        x_offset = max(0, min(64 - new_w, x_offset))
        y_offset = 64 - new_h

        frame_data = [0] * (64 * 64)
        for y in range(new_h):
            for x in range(new_w):
                rgb = res_arr[y, x]
                if is_background(rgb, bg_ref):
                    continue
                pal_idx = find_closest_palette_index(rgb)
                frame_data[(y + y_offset) * 64 + (x + x_offset)] = pal_idx

        if f_idx == 0:
            for y in range(54, 63):
                for x in range(0, 28):
                    if frame_data[y * 64 + x] in (2, 3, 13):
                        frame_data[y * 64 + x] = 11

        if f_idx == 3:
            for y in range(40, 64):
                for x in range(55, 64):
                    frame_data[y * 64 + x] = 0

        for x in range(64):
            idx_63 = 63 * 64 + x
            if frame_data[idx_63] not in (0, 1):
                frame_data[idx_63] = 6

        frame.putdata(frame_data)
        out_frames.append(frame)

    sheet = Image.new("P", (64, 320), 0)
    sheet.putpalette(flat_pal)
    for i, f in enumerate(out_frames):
        sheet.paste(f, (0, i * 64))

    out_png = rom_root / "overrides/graphics/trainers/back_pics/red_back_pic.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)

    out_pal = rom_root / "overrides/graphics/trainers/palettes/red_back_pic.pal"
    out_pal.parent.mkdir(parents=True, exist_ok=True)
    with out_pal.open("w", encoding="utf-8", newline="\n") as f:
        f.write("JASC-PAL\n0100\n16\n")
        for c in PALETTE_COLORS:
            f.write(f"{c[0]} {c[1]} {c[2]}\n")

    print(f"[OK] Wrote {out_png.relative_to(rom_root)} & {out_pal.relative_to(rom_root)}")


if __name__ == "__main__":
    process()
