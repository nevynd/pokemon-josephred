import numpy as np
from pathlib import Path
from PIL import Image

PALETTE_COLORS = [
    (115, 197, 164), # 0: Transparent key (mint green)
    (16, 16, 24),    # 1: Deep black / outline
    (248, 248, 248), # 2: Pure white
    (224, 40, 32),   # 3: Vivid red
    (40, 32, 40),    # 4: Dark hair shadow
    (48, 48, 64),    # 5: Charcoal T-shirt base
    (48, 72, 104),   # 6: Denim blue base
    (72, 112, 152),  # 7: Denim blue highlight
    (232, 176, 136), # 8: Skin light
    (144, 96, 80),   # 9: Skin shadow
    (88, 80, 80),    # 10: Hair / stubble
    (200, 136, 112), # 11: Skin midtone
    (72, 40, 40),    # 12: Hair midtone
    (216, 216, 216), # 13: Light gray
    (152, 152, 152), # 14: Mid gray / shirt highlight
    (168, 128, 96),  # 15: Warm coffee / accent
]

def rgb_dist(c1, c2):
    dr = int(c1[0]) - int(c2[0])
    dg = int(c1[1]) - int(c2[1])
    db = int(c1[2]) - int(c2[2])
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db

def find_closest_palette_index(rgb):
    best_idx = 1
    best_d = float('inf')
    for idx in range(1, 16):
        d = rgb_dist(rgb, PALETTE_COLORS[idx])
        if d < best_d:
            best_d = d
            best_idx = idx
    return best_idx

def is_background(rgb, bg_ref):
    return rgb_dist(rgb, bg_ref) < 1200

def process():
    raw_path = r"C:\Users\Admin\.gemini\antigravity\brain\8d7b401a-6584-4897-af6c-6fbca0af7f47\joseph_battle_back_raw_v3_1794925559390.jpg"
    im_raw = Image.open(raw_path).convert('RGB')
    arr_raw = np.array(im_raw)
    bg_ref = arr_raw[10, 10]

    # Character boxes in raw image:
    boxes = [
        (42, 195, 280, 535),   # 0: Stance
        (325, 195, 530, 530),  # 1: Wind-up
        (580, 200, 772, 530),  # 2: High wind-up
        (820, 200, 1120, 530), # 3: Release (cut strictly before hand of char 4)
        (1140, 200, 1351, 530) # 4: Follow-through
    ]

    target_h = 48
    out_frames = []

    flat_pal = []
    for c in PALETTE_COLORS:
        flat_pal.extend(c)
    while len(flat_pal) < 768:
        flat_pal.extend([0, 0, 0])

    for f_idx, box in enumerate(boxes):
        crop = im_raw.crop(box)
        crop_arr = np.array(crop)

        # In Frame 0, clean up extra red ball on left hand
        if f_idx == 0:
            for y in range(len(crop_arr)):
                for x in range(len(crop_arr[0])):
                    if x < 45 and y > 260:
                        p = crop_arr[y, x]
                        if p[0] > 140 and p[1] < 120:
                            crop_arr[y, x] = [200, 136, 112]

        # In Frame 1, remove cyan fringe on left elbow
        if f_idx == 1:
            for y in range(len(crop_arr)):
                for x in range(len(crop_arr[0])):
                    if x < 25 and y > 220:
                        p = crop_arr[y, x]
                        if p[2] > p[0] + 30: # bluish/cyan fringe
                            crop_arr[y, x] = bg_ref

        # In Frame 3, clean up anything on the right edge below hand
        if f_idx == 3:
            for y in range(len(crop_arr)):
                for x in range(len(crop_arr[0])):
                    if x > 270 and y > 150: # below or past the outstretched hand
                        crop_arr[y, x] = bg_ref

        w, h = crop.size
        scale = target_h / float(h)
        new_w = max(1, int(round(w * scale)))
        new_h = target_h

        resized = crop.resize((new_w, new_h), Image.Resampling.LANCZOS)
        res_arr = np.array(resized)

        frame = Image.new('P', (64, 64), 0)
        frame.putpalette(flat_pal)

        # Determine x placement to align with GBA FireRed positioning
        if f_idx == 0:
            x_offset = (64 - new_w) // 2 + 3 # centered slightly right (x ~ 18..54)
        elif f_idx == 1:
            x_offset = (64 - new_w) // 2
        elif f_idx == 2:
            x_offset = (64 - new_w) // 2 - 2
        elif f_idx == 3:
            x_offset = 64 - new_w - 2 # right hand reaches to x=61
        elif f_idx == 4:
            x_offset = (64 - new_w) // 2 - 2

        x_offset = max(0, min(64 - new_w, x_offset))
        y_offset = 64 - new_h # touches bottom baseline (y=63)

        frame_data = [0] * (64 * 64)
        for y in range(new_h):
            for x in range(new_w):
                rgb = res_arr[y, x]
                if is_background(rgb, bg_ref):
                    continue
                pal_idx = find_closest_palette_index(rgb)
                frame_data[(y + y_offset) * 64 + (x + x_offset)] = pal_idx

        # Clean stray pixels in Frame 3 bottom-right
        if f_idx == 3:
            for y in range(40, 64):
                for x in range(55, 64):
                    frame_data[y * 64 + x] = 0

        # Ensure all pixels at y=63 that belong to jeans are index 6 or 7
        for x in range(64):
            idx_63 = 63 * 64 + x
            if frame_data[idx_63] not in (0, 1):
                frame_data[idx_63] = 6

        frame.putdata(frame_data)
        out_frames.append(frame)

    # Save outputs
    strip = Image.new('P', (64 * 5, 64), 0)
    strip.putpalette(flat_pal)
    for i, f in enumerate(out_frames):
        f.save(f"scratch/joseph_back_f{i}.png")
        strip.paste(f, (i * 64, 0))
    strip.save("scratch/joseph_back_strip.png")

    # Stack vertically into 64x320 for GBA
    sheet = Image.new('P', (64, 320), 0)
    sheet.putpalette(flat_pal)
    for i, f in enumerate(out_frames):
        sheet.paste(f, (0, i * 64))
    sheet.save("scratch/joseph_back_sheet.png")

    # Also save directly into rom/overrides!
    out_png = Path("rom/overrides/graphics/trainers/back_pics/red_back_pic.png")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_png))

    # Also save palette into rom/overrides/graphics/trainers/palettes/red_back_pic.pal!
    out_pal = Path("rom/overrides/graphics/trainers/palettes/red_back_pic.pal")
    out_pal.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pal, "w") as f:
        f.write("JASC-PAL\n0100\n16\n")
        for c in PALETTE_COLORS:
            f.write(f"{c[0]} {c[1]} {c[2]}\n")

    print(f"[OK] Wrote {out_png} (64x320, 4bpp P-mode)")
    print(f"[OK] Wrote {out_pal} (JASC-PAL 16 colors)")

if __name__ == '__main__':
    process()
