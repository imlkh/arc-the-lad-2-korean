#!/usr/bin/env python3
"""
Render detailed close-ups of mismatched cells to identify characters.
"""

import os
from PIL import Image, ImageDraw

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "..", "COMM.IMG")
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "validation")
ROW_WIDTH = 896
CHAR_W, CHAR_H = 12, 12  # 12x12 cell (11x11 glyph + 1px margin)
GRID_COLS = 21

os.makedirs(OUTPUT_DIR, exist_ok=True)
data = open(COMM_IMG_PATH, "rb").read()

indices = [[0]*256 for _ in range(256)]
for y in range(256):
    for xb in range(128):
        offset = y * ROW_WIDTH + xb
        byte = data[offset]
        indices[y][xb * 2] = byte & 0x0F
        indices[y][xb * 2 + 1] = (byte >> 4) & 0x0F

def extract_glyph(cell, bit):
    grow = cell // GRID_COLS
    gcol = cell % GRID_COLS
    x0 = gcol * CHAR_W
    y0 = grow * CHAR_H
    if grow == 20 and gcol == 20:
        w, h = 16, 16
    else:
        w, h = CHAR_W, CHAR_H
    mask = 1 << bit
    img = Image.new('L', (w, h), 0)
    px = img.load()
    count = 0
    for dy in range(h):
        for dx in range(w):
            if y0 + dy < 256 and x0 + dx < 256:
                if indices[y0 + dy][x0 + dx] & mask:
                    px[dx, dy] = 255
                    count += 1
    return img, count

def render_cell_strip(cells, bits, filename, scale=10):
    """Render cells x bits in a grid."""
    cell_w = CHAR_W * scale + 4
    cell_h = CHAR_H * scale + 4
    n_cols = len(bits)
    n_rows = len(cells)
    sheet_w = n_cols * cell_w + 60  # extra for cell labels
    sheet_h = n_rows * cell_h + 20  # extra for bit labels
    sheet = Image.new('RGB', (sheet_w, sheet_h), (20, 20, 30))
    draw = ImageDraw.Draw(sheet)

    # Bit labels
    for j, bit in enumerate(bits):
        draw.text((60 + j * cell_w + cell_w//3, 2), f"bit{bit}", fill=(180, 180, 180))

    for i, cell in enumerate(cells):
        # Cell label
        draw.text((2, 20 + i * cell_h + cell_h//3), f"C{cell}", fill=(180, 180, 180))
        for j, bit in enumerate(bits):
            img, count = extract_glyph(cell, bit)
            display = img.resize((CHAR_W * scale, CHAR_H * scale), Image.NEAREST)
            sx = 60 + j * cell_w + 2
            sy = 20 + i * cell_h + 2
            sheet.paste(display, (sx, sy))

    sheet.save(os.path.join(OUTPUT_DIR, filename))
    print(f"Saved {filename}")

# === Row 13 tail: cells 288-293, all 4 bitplanes ===
render_cell_strip(list(range(288, 294)), [0, 1, 2, 3], "row13_tail_detail.png", scale=10)

# === Cell 125 all bitplanes ===
render_cell_strip([124, 125], [0, 1, 2, 3], "cell124_125_detail.png", scale=10)

# === Cell 209, 251, 272 ===
render_cell_strip([208, 209, 250, 251, 271, 272], [0, 1, 2, 3], "cells_209_251_272_detail.png", scale=10)

# === Cell 356 and neighbors ===
render_cell_strip([355, 356, 357], [0, 1, 2, 3], "cell356_neighbors_detail.png", scale=10)

# === Cell 398 and neighbors ===
render_cell_strip([397, 398, 399], [0, 1, 2, 3], "cell398_neighbors_detail.png", scale=10)

# === Cell 414, 415 ===
render_cell_strip([413, 414, 415], [0, 1, 2, 3], "cell414_415_detail.png", scale=10)

# === Row 14 bit2 - all cells ===
render_cell_strip(list(range(294, 315)), [0, 1, 2, 3], "row14_all_bits_detail.png", scale=8)

# === Cell 31 check (documented as ラ but should be ヲ in katakana row) ===
render_cell_strip([30, 31, 32], [0, 1, 2, 3], "cell30_31_32_detail.png", scale=10)

# === Cell 61 bit3 (documented as '.' with only 2 pixels) ===
print("\n=== Cell 61 bit3 detail ===")
img, count = extract_glyph(61, 3)
print(f"Cell 61 bit3: {count}px")
px = img.load()
for y in range(CHAR_H):
    row = ""
    for x in range(CHAR_W):
        row += "█" if px[x, y] > 0 else "·"
    print(f"  {row}")

# === Show ASCII art for Row 14 bit2 cells ===
print("\n=== Row 14 bit2 ASCII art ===")
for cell in range(294, 315):
    img, count = extract_glyph(cell, 2)
    px = img.load()
    print(f"\nCell {cell} bit2 ({count}px):")
    for y in range(CHAR_H):
        row = ""
        for x in range(CHAR_W):
            row += "█" if px[x, y] > 0 else "·"
        print(f"  {row}")

# === Show ASCII art for Cell 125 all bits ===
print("\n=== Cell 125 all bits ASCII art ===")
for bit in range(4):
    img, count = extract_glyph(125, bit)
    px = img.load()
    print(f"\nCell 125 bit{bit} ({count}px):")
    for y in range(CHAR_H):
        row = ""
        for x in range(CHAR_W):
            row += "█" if px[x, y] > 0 else "·"
        print(f"  {row}")

# === Show ASCII art for Cells 290-293 missing bits ===
print("\n=== Cells 290-293 missing bits ASCII art ===")
missing = [(290, 0), (291, 0), (291, 1), (292, 0), (292, 1),
           (293, 0), (293, 1), (293, 2), (293, 3)]
for cell, bit in missing:
    img, count = extract_glyph(cell, bit)
    px = img.load()
    print(f"\nCell {cell} bit{bit} ({count}px):")
    for y in range(CHAR_H):
        row = ""
        for x in range(CHAR_W):
            row += "█" if px[x, y] > 0 else "·"
        print(f"  {row}")
