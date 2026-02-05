#!/usr/bin/env python3
"""
Find duplicated Japanese character slots in COMM.IMG font table
and output a report file + visual comparison image.

Output:
  output/font/duplicate_slots.json
  output/validation/duplicate_slots.png
"""

import json
import os
from collections import Counter

from PIL import Image, ImageDraw, ImageFont
from view_char import (
    COMM_IMG_PATH, GRID_COLS, CELL_SIZE, SPECIAL_CELL, SPECIAL_SIZE,
    ROW_WIDTH, extract_bitplanes,
)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSITIONS_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "output", "font", "jp_char_positions.json")
OUTPUT_JSON = os.path.join(_SCRIPT_DIR, "..", "..", "output", "font", "duplicate_slots.json")
OUTPUT_IMG = os.path.join(_SCRIPT_DIR, "..", "..", "output", "validation", "duplicate_slots.png")

SCALE = 4
GLYPH_PX = CELL_SIZE * SCALE  # 48
REFERENCE_FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
REFERENCE_FONT_SIZE = 36


def main():
    # Load positions
    with open(POSITIONS_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    # Find duplicates
    char_counts = Counter(e["char"] for e in entries)
    dupe_chars = sorted(
        [ch for ch, count in char_counts.items() if count > 1],
        key=lambda ch: min(e["cell"] for e in entries if e["char"] == ch),
    )

    # Build duplicate groups
    groups = []
    for ch in dupe_chars:
        slots = [e for e in entries if e["char"] == ch]
        slots.sort(key=lambda e: (e["cell"], e["bitplane"]))
        groups.append({
            "char": ch,
            "unicode": f"U+{ord(ch):04X}",
            "count": len(slots),
            "slots": slots,
        })

    # Save JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(groups)} duplicate groups to {OUTPUT_JSON}")

    if not groups:
        print("\nNo duplicates found.")
        return

    # --- Generate comparison image ---
    os.makedirs(os.path.dirname(OUTPUT_IMG), exist_ok=True)

    data = open(COMM_IMG_PATH, "rb").read()
    ref_font = ImageFont.truetype(REFERENCE_FONT_PATH, REFERENCE_FONT_SIZE)
    label_font = ImageFont.truetype(REFERENCE_FONT_PATH, 10)

    # Layout: one row per duplicate character
    # Columns: [reference char] [slot1 glyph] [slot2 glyph] ...
    max_slots = max(g["count"] for g in groups)
    col_w = GLYPH_PX + 4
    ref_col_w = GLYPH_PX + 8
    label_h = 14
    row_h = GLYPH_PX + label_h + 6
    img_w = ref_col_w + max_slots * col_w + 8
    img_h = len(groups) * row_h + 4

    sheet = Image.new("RGB", (img_w, img_h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)

    for gi, group in enumerate(groups):
        y = gi * row_h + 2

        # Draw reference character
        ref_img = Image.new("L", (GLYPH_PX, GLYPH_PX), 0)
        ref_draw = ImageDraw.Draw(ref_img)
        ref_draw.text(
            (GLYPH_PX // 2, GLYPH_PX // 2),
            group["char"], font=ref_font, fill=255, anchor="mm",
        )
        sheet.paste(ref_img, (4, y))
        draw.text(
            (4, y + GLYPH_PX), group["char"],
            fill=(200, 200, 200), font=label_font,
        )

        # Draw divider
        draw.line(
            [(ref_col_w - 2, y), (ref_col_w - 2, y + GLYPH_PX - 1)],
            fill=(80, 80, 80),
        )

        # Draw each slot's extracted glyph
        for si, slot in enumerate(group["slots"]):
            cell = slot["cell"]
            bit = slot["bitplane"]
            row = cell // GRID_COLS
            col = cell % GRID_COLS

            planes, _, w, h = extract_bitplanes(data, row, col)
            glyph = planes[bit].resize((GLYPH_PX, GLYPH_PX), Image.NEAREST)

            sx = ref_col_w + si * col_w
            sheet.paste(glyph, (sx, y))

            label = f"c{cell}b{bit}"
            draw.text(
                (sx, y + GLYPH_PX), label,
                fill=(180, 180, 100), font=label_font,
            )

    sheet.save(OUTPUT_IMG)
    print(f"Saved comparison image to {OUTPUT_IMG}")
    print(f"\n{len(groups)} duplicated characters ({sum(g['count'] for g in groups)} total slots)")


if __name__ == "__main__":
    main()
