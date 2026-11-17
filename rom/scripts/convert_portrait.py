#!/usr/bin/env python3
"""
Converts Joseph's portrait / pixel-art reference into Pokémon FireRed's exact
trainer sprite formats:
  1) Oak Speech Intro Platform Sprite:
     - graphics/oak_speech/red/pal.pal (32-entry JASC-PAL, 15-bit GBA RGB)
     - graphics/oak_speech/red/pic.png (64x96 8bpp indexed PNG, 0=transparent, 65..95=colors)
  2) Trainer Card / Front Battle Sprite:
     - graphics/trainers/palettes/red.pal (16-entry JASC-PAL, 15-bit GBA RGB)
     - graphics/trainers/front_pics/red_front_pic.png (64x64 4bpp indexed PNG, 0=transparent, 1..15=colors)
"""

from __future__ import annotations
import argparse
import collections
import pathlib
from PIL import Image


def gba_snap(val: int) -> int:
    return (val >> 3) << 3


def clean_background(im_rgba: Image.Image, tolerance: int = 38) -> Image.Image:
    w, h = im_rgba.size
    out = im_rgba.copy()
    opx = out.load()

    # Check if already transparent PNG
    if min(opx[x, y][3] for y in range(h) for x in range(w)) < 128:
        return out

    # Sample background RGB from corners
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)]
    seed_rgbs = [opx[sx, sy][:3] for sx, sy in corners]
    avg_r = sum(c[0] for c in seed_rgbs) // len(seed_rgbs)
    avg_g = sum(c[1] for c in seed_rgbs) // len(seed_rgbs)
    avg_b = sum(c[2] for c in seed_rgbs) // len(seed_rgbs)
    is_green_screen = avg_g > avg_r + 25 and avg_g > avg_b + 10

    def is_bg_pixel(r: int, g: int, b: int) -> bool:
        if is_green_screen:
            return g > 120 and g > r + 24 and g > b + 12
        for sr, sg, sb in seed_rgbs:
            if abs(r - sr) + abs(g - sg) + abs(b - sb) <= tolerance * 3:
                return True
        return False

    if is_green_screen:
        for y in range(h):
            for x in range(w):
                r, g, b, _ = opx[x, y]
                if is_bg_pixel(r, g, b):
                    opx[x, y] = (0, 0, 0, 0)
                # Despill dark JPEG chroma border pixels right next to green screen
                elif g > r + 10 and g > b + 6 and max(r, g, b) < 110:
                    opx[x, y] = (16, 16, 24, 255)
        return out

    # Generic corner + bottom-center floodfill for arbitrary photo backgrounds
    visited = [[False] * w for _ in range(h)]
    q: collections.deque[tuple[int, int]] = collections.deque()
    for sx, sy in corners:
        visited[sy][sx] = True
        q.append((sx, sy))

    while q:
        cx, cy = q.popleft()
        r, g, b, _ = opx[cx, cy]
        if is_bg_pixel(r, g, b):
            opx[cx, cy] = (0, 0, 0, 0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    visited[ny][nx] = True
                    q.append((nx, ny))
    return out


def fit_sprite_canvas(
    cropped: Image.Image, canvas_w: int, canvas_h: int, max_w: int, max_h: int, bottom_pad: int
) -> tuple[Image.Image, list[list[bool]], list[list[bool]]]:
    scale = min(max_w / cropped.width, max_h / cropped.height)
    nw = max(1, int(round(cropped.width * scale)))
    nh = max(1, int(round(cropped.height * scale)))

    # Box/Area downsampling preserves crisp pixel clusters cleanly then sharpens alpha at 50%
    resized = cropped.resize((nw, nh), Image.Resampling.BOX)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    paste_x = (canvas_w - nw) // 2
    paste_y = canvas_h - nh - bottom_pad
    canvas.paste(resized, (paste_x, paste_y), resized)

    cpx = canvas.load()
    opaque = [[cpx[x, y][3] >= 145 for x in range(canvas_w)] for y in range(canvas_h)]

    # Ensure crisp 1px dark GBA contour around silhouette where needed
    outline = [[False] * canvas_w for _ in range(canvas_h)]
    for y in range(canvas_h):
        for x in range(canvas_w):
            if opaque[y][x]:
                r, g, b, a = cpx[x, y]
                # Un-premultiply edge blend if semi-transparent
                if a < 250 and a > 0:
                    r = min(255, int(r * 255 / a))
                    g = min(255, int(g * 255 / a))
                    b = min(255, int(b * 255 / a))
                    cpx[x, y] = (r, g, b, 255)
            else:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < canvas_w and 0 <= ny < canvas_h and opaque[ny][nx]:
                        nr, ng, nb, _ = cpx[nx, ny]
                        if max(nr, ng, nb) > 55:
                            outline[y][x] = True
                            break
    return canvas, opaque, outline


def quantize_foreground_palette(
    cpx, opaque: list[list[bool]], w: int, h: int, target_colors: int
) -> list[tuple[int, int, int]]:
    fg_pixels: list[tuple[int, int, int]] = []
    for y in range(h):
        for x in range(w):
            if opaque[y][x]:
                r, g, b, _ = cpx[x, y]
                if max(r, g, b) >= 36:
                    fg_pixels.append((gba_snap(r), gba_snap(g), gba_snap(b)))

    if not fg_pixels:
        return [(248, 248, 248)] * target_colors

    # Pin crisp GBA white & Poké Ball red so small eye/cup/Poké Ball details never wash out
    pinned = [(248, 248, 248), (224, 40, 32)]
    rem = max(1, target_colors - len(pinned))
    strip = Image.new("RGB", (len(fg_pixels), 1))
    strip.putdata(fg_pixels)
    quant = strip.quantize(colors=rem, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    qpal = quant.getpalette()[: rem * 3]
    colors = list(pinned)
    for i in range(rem):
        colors.append((gba_snap(qpal[i * 3]), gba_snap(qpal[i * 3 + 1]), gba_snap(qpal[i * 3 + 2])))
    return colors[:target_colors]


def nearest_pal_idx(r: int, g: int, b: int, pal: list[tuple[int, int, int]]) -> int:
    best_i = 0
    best_d = 10**9
    for idx, (pr, pg, pb) in enumerate(pal):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best_d = d
            best_i = idx
    return best_i


def build_oak_speech_sprite(
    cropped: Image.Image, out_dir: pathlib.Path, ref_pic_path: pathlib.Path | None
) -> Image.Image:
    # Red in Oak's speech is ~81px tall grounded at y=94 inside 64x96
    canvas, opaque, outline = fit_sprite_canvas(cropped, 64, 96, max_w=58, max_h=82, bottom_pad=2)
    cpx = canvas.load()

    fg30 = quantize_foreground_palette(cpx, opaque, 64, 96, 30)
    pal32: list[tuple[int, int, int]] = [(115, 197, 164), (16, 16, 24)] + fg30

    full_pal = [0] * (256 * 3)
    if ref_pic_path and ref_pic_path.exists():
        ref_pal = Image.open(ref_pic_path).getpalette()
        if ref_pal:
            full_pal[: len(ref_pal)] = ref_pal
    else:
        full_pal[0:3] = [115, 197, 164]

    for idx_32, (r, g, b) in enumerate(pal32):
        pidx = 64 + idx_32
        full_pal[pidx * 3 : pidx * 3 + 3] = [r, g, b]

    out_im = Image.new("P", (64, 96), 0)
    out_im.putpalette(full_pal)
    opx = out_im.load()

    for y in range(96):
        for x in range(64):
            if opaque[y][x]:
                r, g, b, _ = cpx[x, y]
                if max(r, g, b) < 36:
                    opx[x, y] = 65
                else:
                    opx[x, y] = 66 + nearest_pal_idx(r, g, b, fg30)
            elif outline[y][x]:
                opx[x, y] = 65
            else:
                opx[x, y] = 0

    out_dir.mkdir(parents=True, exist_ok=True)
    out_im.save(out_dir / "pic.png")
    jasc = ["JASC-PAL", "0100", "32"] + [f"{r} {g} {b}" for (r, g, b) in pal32]
    (out_dir / "pal.pal").write_text("\n".join(jasc) + "\n", encoding="ascii")
    return out_im


def build_trainer_card_sprite(cropped: Image.Image, overrides_root: pathlib.Path) -> None:
    # Trainer Card / Front Battle Pic is 64x64 4bpp (16 colors: 0=transparent, 1..15=colors)
    canvas, opaque, outline = fit_sprite_canvas(cropped, 64, 64, max_w=52, max_h=60, bottom_pad=1)
    cpx = canvas.load()

    fg14 = quantize_foreground_palette(cpx, opaque, 64, 64, 14)
    pal16: list[tuple[int, int, int]] = [(115, 197, 164), (16, 16, 24)] + fg14

    flat_pal: list[int] = []
    for r, g, b in pal16:
        flat_pal.extend([r, g, b])

    out_im = Image.new("P", (64, 64), 0)
    out_im.putpalette(flat_pal)
    opx = out_im.load()

    for y in range(64):
        for x in range(64):
            if opaque[y][x]:
                r, g, b, _ = cpx[x, y]
                if max(r, g, b) < 36:
                    opx[x, y] = 1
                else:
                    opx[x, y] = 2 + nearest_pal_idx(r, g, b, fg14)
            elif outline[y][x]:
                opx[x, y] = 1
            else:
                opx[x, y] = 0

    pic_dir = overrides_root / "graphics/trainers/front_pics"
    pal_dir = overrides_root / "graphics/trainers/palettes"
    pic_dir.mkdir(parents=True, exist_ok=True)
    pal_dir.mkdir(parents=True, exist_ok=True)
    out_im.save(pic_dir / "red_front_pic.png")
    jasc = ["JASC-PAL", "0100", "16"] + [f"{r} {g} {b}" for (r, g, b) in pal16]
    (pal_dir / "red.pal").write_text("\n".join(jasc) + "\n", encoding="ascii")


def convert_portrait(
    input_path: pathlib.Path,
    overrides_root: pathlib.Path,
    ref_pic_path: pathlib.Path | None = None,
    preview_path: pathlib.Path | None = None,
    bg_tolerance: int = 38,
) -> None:
    src = Image.open(input_path).convert("RGBA")
    cleaned = clean_background(src, tolerance=bg_tolerance)
    bbox = cleaned.getbbox()
    if not bbox:
        raise ValueError("Background removal left an empty image")
    cropped = cleaned.crop(bbox)

    oak_dir = overrides_root / "graphics/oak_speech/red"
    oak_im = build_oak_speech_sprite(cropped, oak_dir, ref_pic_path)
    build_trainer_card_sprite(cropped, overrides_root)

    if preview_path:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        oak_im.convert("RGBA").resize((256, 384), Image.Resampling.NEAREST).save(preview_path)

    print(f"[OK] Generated Joseph Oak Speech (64x96) & Trainer Card (64x64) sprites in {overrides_root}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Joseph image to FireRed GBA sprites")
    parser.add_argument("--input", required=True, type=pathlib.Path, help="Input image path")
    parser.add_argument(
        "--overrides-root",
        default=pathlib.Path("rom/overrides"),
        type=pathlib.Path,
        help="Root overrides directory",
    )
    parser.add_argument(
        "--ref-pic",
        default=pathlib.Path("rom/upstream-pokefirered/graphics/oak_speech/red/pic.png"),
        type=pathlib.Path,
        help="Upstream reference Oak speech pic.png",
    )
    parser.add_argument("--preview", type=pathlib.Path, default=None, help="Optional 4x preview PNG")
    parser.add_argument("--bg-tolerance", type=int, default=38, help="Background tolerance")
    args = parser.parse_args()
    convert_portrait(args.input, args.overrides_root, args.ref_pic, args.preview, args.bg_tolerance)


if __name__ == "__main__":
    main()
