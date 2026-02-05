#!/usr/bin/env python3
"""
Check for duplicate characters between bitplanes within the same cell.
Rows 15 and 18 show suspicious bit1==bit3 and bit2==bit3 patterns.
"""

import os
from PIL import Image

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "..", "COMM.IMG")
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "validation")
ROW_WIDTH = 896
CHAR_W, CHAR_H = 12, 12  # 12x12 cell (11x11 glyph + 1px margin)
GRID_COLS = 21

data = open(COMM_IMG_PATH, "rb").read()

indices = [[0]*256 for _ in range(256)]
for y in range(256):
    for xb in range(128):
        offset = y * ROW_WIDTH + xb
        byte = data[offset]
        indices[y][xb * 2] = byte & 0x0F
        indices[y][xb * 2 + 1] = (byte >> 4) & 0x0F

def extract_glyph_data(cell, bit):
    grow = cell // GRID_COLS
    gcol = cell % GRID_COLS
    x0 = gcol * CHAR_W
    y0 = grow * CHAR_H
    if grow == 20 and gcol == 20:
        w, h = 16, 16
    else:
        w, h = CHAR_W, CHAR_H
    mask = 1 << bit
    pixels = []
    for dy in range(h):
        for dx in range(w):
            if y0 + dy < 256 and x0 + dx < 256:
                pixels.append(1 if indices[y0 + dy][x0 + dx] & mask else 0)
            else:
                pixels.append(0)
    return tuple(pixels)

# === Check Row 15 (cells 330-335): doc shows bit1==bit3 ===
print("=== Row 15 bit1 vs bit3 comparison (cells 330-335) ===")
for cell in range(330, 336):
    b1 = extract_glyph_data(cell, 1)
    b3 = extract_glyph_data(cell, 3)
    match = b1 == b3
    diff_count = sum(1 for a, b in zip(b1, b3) if a != b)
    print(f"  Cell {cell}: bit1==bit3? {match}, diff_pixels={diff_count}")

# === Check Row 18 (cells 387-398): doc shows bit2==bit3 ===
print("\n=== Row 18 bit2 vs bit3 comparison (cells 387-398) ===")
for cell in range(387, 399):
    b2 = extract_glyph_data(cell, 2)
    b3 = extract_glyph_data(cell, 3)
    match = b2 == b3
    diff_count = sum(1 for a, b in zip(b2, b3) if a != b)
    print(f"  Cell {cell}: bit2==bit3? {match}, diff_pixels={diff_count}")

# === Comprehensive duplicate check across ALL cells ===
print("\n=== Full duplicate check (all 441 cells, all bit pairs) ===")
exact_dupes = []
near_dupes = []  # differ by <= 5 pixels
for cell in range(441):
    for b1 in range(4):
        d1 = extract_glyph_data(cell, b1)
        pc1 = sum(d1)
        if pc1 <= 2:
            continue  # skip blanks
        for b2 in range(b1 + 1, 4):
            d2 = extract_glyph_data(cell, b2)
            pc2 = sum(d2)
            if pc2 <= 2:
                continue
            diff = sum(1 for a, b in zip(d1, d2) if a != b)
            if diff == 0:
                exact_dupes.append((cell, b1, b2))
            elif diff <= 5:
                near_dupes.append((cell, b1, b2, diff))

print(f"  Exact duplicates (same pixels): {len(exact_dupes)}")
for cell, b1, b2 in exact_dupes:
    print(f"    Cell {cell}: bit{b1} == bit{b2}")

print(f"  Near duplicates (<=5 pixel diff): {len(near_dupes)}")
for cell, b1, b2, diff in near_dupes:
    print(f"    Cell {cell}: bit{b1} ~= bit{b2} (diff={diff})")

# === Render Row 15 cells 330-335 and Row 18 cells 387-398 ===
SCALE = 8
def render_comparison(cells, filename):
    cell_w = CHAR_W * SCALE + 2
    n_cols = 4  # 4 bitplanes
    n_rows = len(cells)
    sheet_w = 50 + n_cols * cell_w + 4
    sheet_h = n_rows * (CHAR_H * SCALE + 20) + 4
    sheet = Image.new('RGB', (sheet_w, sheet_h), (20, 20, 30))

    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)

    for j in range(4):
        draw.text((50 + j * cell_w + cell_w//3, 2), f"b{j}", fill=(180, 180, 180))

    for i, cell in enumerate(cells):
        sy = i * (CHAR_H * SCALE + 20) + 16
        draw.text((2, sy + CHAR_H * SCALE // 3), f"C{cell}", fill=(180, 180, 180))

        for bit in range(4):
            grow = cell // GRID_COLS
            gcol = cell % GRID_COLS
            x0 = gcol * CHAR_W
            y0 = grow * CHAR_H
            mask = 1 << bit
            img = Image.new('L', (CHAR_W, CHAR_H), 0)
            px = img.load()
            for dy in range(CHAR_H):
                for dx in range(CHAR_W):
                    if indices[y0+dy][x0+dx] & mask:
                        px[dx, dy] = 255
            display = img.resize((CHAR_W * SCALE, CHAR_H * SCALE), Image.NEAREST)
            sx = 50 + bit * cell_w + 2
            sheet.paste(display, (sx, sy))

    sheet.save(os.path.join(OUTPUT_DIR, filename))
    print(f"\nSaved {filename}")

render_comparison(list(range(330, 336)), "row15_dupes_check.png")
render_comparison(list(range(387, 399)), "row18_dupes_check.png")

# === Check Cell 288 doc vs actual ===
print("\n=== Cell 288 verification ===")
# Doc says: 徹 | 町 | 潮 | 町
# Image looks like: 忠 | 注 | 抽 | 著
for bit in range(4):
    d = extract_glyph_data(288, bit)
    pc = sum(d)
    print(f"  bit{bit}: {pc}px")
