#!/usr/bin/env python3
"""
Hand-pixels authentic jet-black Squirtle Squad Leader pointed anime sunglasses
onto Squirtle's GBA front.png and back.png (64x64 4bpp indexed, palette-preserving).
"""

from pathlib import Path
from PIL import Image

# Palette indices in graphics/pokemon/squirtle/normal.pal:
#  0: (205, 205, 172) transparent key
#  1: (255, 255, 255) pure white (sharp anime lens glare)
#  5: (213, 205, 205) cool silver (secondary lens sheen)
# 13: (131, 148, 172) slate gray-blue (subtle rim highlight)
# 15: ( 16,  16,  16) jet black (sunglasses frame & dark lens)
WHITE = 1
SILVER = 5
SLATE = 13
BLACK = 15


def load_jasc_pal(pal_path: Path) -> list[int]:
    lines = pal_path.read_text(encoding="utf-8").splitlines()[3:]
    flat: list[int] = []
    for line in lines[:16]:
        r, g, b = map(int, line.strip().split())
        flat.extend([r, g, b])
    flat.extend([0] * (768 - len(flat)))
    return flat


def apply_front_shades(src: Image.Image, palette: list[int]) -> Image.Image:
    im = src.copy()
    pix = im.load()

    # Exact pixel map for Squirtle's 3/4-left tilted head (head x=21..38, eyes at x=21..23 & x=30..34, y=22..26)
    # Rows (y: list of (x, color))
    rows: dict[int, list[tuple[int, int]]] = {
        # Sharp outer-right wing tip rising at temple
        19: [(39, BLACK), (40, BLACK)],
        # Left outer point (x=18..19) & right upper wing (x=36..40)
        20: [
            (18, BLACK), (19, BLACK),
            (36, BLACK), (37, BLACK), (38, WHITE), (39, BLACK), (40, BLACK),
        ],
        # Upper slanted rims converging toward nose bridge
        21: [
            (18, BLACK), (19, WHITE), (20, BLACK), (21, BLACK),
            (33, BLACK), (34, BLACK), (35, BLACK), (36, WHITE), (37, SILVER), (38, BLACK), (39, BLACK),
        ],
        22: [
            (19, BLACK), (20, WHITE), (21, SILVER), (22, BLACK), (23, BLACK),
            (30, BLACK), (31, BLACK), (32, BLACK), (33, BLACK), (34, WHITE), (35, SILVER), (36, BLACK), (37, BLACK), (38, BLACK),
        ],
        # Nose bridge + full mid-lens coverage over both eyes
        23: [
            (19, BLACK), (20, BLACK), (21, WHITE), (22, BLACK), (23, BLACK), (24, BLACK),
            (25, BLACK), (26, BLACK), (27, BLACK), (28, BLACK),
            (29, BLACK), (30, BLACK), (31, BLACK), (32, WHITE), (33, SILVER), (34, BLACK), (35, BLACK), (36, BLACK), (37, BLACK),
        ],
        24: [
            (20, BLACK), (21, BLACK), (22, BLACK), (23, BLACK), (24, BLACK),
            (25, SLATE), (26, BLACK),
            (28, BLACK), (29, BLACK), (30, BLACK), (31, WHITE), (32, BLACK), (33, BLACK), (34, BLACK), (35, BLACK), (36, BLACK),
        ],
        # Lower tapered triangular points covering bottom of eyes
        25: [
            (20, BLACK), (21, BLACK), (22, BLACK), (23, BLACK),
            (29, BLACK), (30, BLACK), (31, BLACK), (32, BLACK), (33, BLACK), (34, BLACK), (35, BLACK),
        ],
        26: [
            (21, BLACK), (22, BLACK),
            (30, BLACK), (31, BLACK), (32, BLACK), (33, BLACK), (34, BLACK),
        ],
    }

    for y, pts in rows.items():
        for x, col in pts:
            pix[x, y] = col

    im.putpalette(palette)
    return im


def apply_back_shades(src: Image.Image, palette: list[int]) -> Image.Image:
    im = src.copy()
    pix = im.load()

    # Profile right eye on back.png is at x=45..47, y=23..27; head spans x=28..48.
    # Add sleek black temple arm (x=39..44) + sharp forward-pointing triangular shade (x=44..51).
    rows: dict[int, list[tuple[int, int]]] = {
        20: [(50, BLACK), (51, BLACK)],
        21: [(48, BLACK), (49, WHITE), (50, BLACK), (51, BLACK)],
        22: [(46, BLACK), (47, BLACK), (48, WHITE), (49, SILVER), (50, BLACK)],
        23: [(44, BLACK), (45, BLACK), (46, BLACK), (47, WHITE), (48, BLACK), (49, BLACK)],
        24: [
            (39, BLACK), (40, BLACK), (41, BLACK), (42, BLACK), (43, BLACK),
            (44, BLACK), (45, BLACK), (46, SILVER), (47, BLACK), (48, BLACK), (49, BLACK),
        ],
        25: [
            (41, BLACK), (42, BLACK), (43, BLACK),
            (44, BLACK), (45, BLACK), (46, BLACK), (47, BLACK), (48, BLACK),
        ],
        26: [(45, BLACK), (46, BLACK), (47, BLACK), (48, BLACK)],
        27: [(46, BLACK), (47, BLACK)],
    }

    for y, pts in rows.items():
        for x, col in pts:
            pix[x, y] = col

    im.putpalette(palette)
    return im


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_dir = repo_root / "rom/upstream-pokefirered/graphics/pokemon/squirtle"
    dst_dir = repo_root / "rom/overrides/graphics/pokemon/squirtle"
    dst_dir.mkdir(parents=True, exist_ok=True)

    pal = load_jasc_pal(src_dir / "normal.pal")
    front = apply_front_shades(Image.open(src_dir / "front.png"), pal)
    back = apply_back_shades(Image.open(src_dir / "back.png"), pal)

    front.save(dst_dir / "front.png")
    back.save(dst_dir / "back.png")
    (dst_dir / "normal.pal").write_bytes((src_dir / "normal.pal").read_bytes())
    print(f"[OK] Wrote Squirtle Squad front.png & back.png to {dst_dir}")


if __name__ == "__main__":
    main()
