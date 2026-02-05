#!/usr/bin/env python3
"""
Examine specific mismatched cells in detail.
Renders enlarged views of cells that were documented as blank but contain pixels,
or documented as having content but appear blank.
"""

import os
from PIL import Image, ImageDraw

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "..", "COMM.IMG")
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "validation")
ROW_WIDTH = 896
CHAR_W, CHAR_H = 12, 12  # 12x12 cell (11x11 glyph + 1px margin)
GRID_COLS, GRID_ROWS = 21, 21

os.makedirs(OUTPUT_DIR, exist_ok=True)

data = open(COMM_IMG_PATH, "rb").read()

# Build index map
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

# === Cells documented as blank but having pixels ===
false_blanks = [
    (125, 0, "(blank)→?"), (125, 2, "(blank)→?"), (125, 3, "(blank)→?"),
    (209, 2, "(blank)→?"),
    (251, 2, "(blank)→?"), (251, 3, "(blank)→?"),
    (272, 1, "(blank)→?"), (272, 3, "(blank)→?"),
    (290, 0, "(blank)→?"),
    (291, 0, "(blank)→?"), (291, 1, "(blank)→?"),
    (292, 0, "(blank)→?"), (292, 1, "(blank)→?"),
    (293, 0, "(blank)→?"), (293, 1, "(blank)→?"), (293, 2, "(blank)→?"), (293, 3, "(blank)→?"),
    # Row 14 bit2 - systematic miss
    (298, 2, "Row14 bit2"), (299, 2, "Row14 bit2"), (300, 2, "Row14 bit2"),
    (301, 2, "Row14 bit2"), (302, 2, "Row14 bit2"), (303, 2, "Row14 bit2"),
    (304, 2, "Row14 bit2"), (305, 2, "Row14 bit2"), (306, 2, "Row14 bit2"),
    (307, 2, "Row14 bit2"), (308, 2, "Row14 bit2"), (309, 2, "Row14 bit2"),
    (310, 2, "Row14 bit2"), (311, 2, "Row14 bit2"), (312, 2, "Row14 bit2"),
    (313, 2, "Row14 bit2"), (314, 2, "Row14 bit2"),
    # Others
    (356, 0, "(blank)→?"), (356, 2, "(blank)→?"), (356, 3, "(blank)→?"),
    (398, 1, "(blank)→?"),
    (414, 3, "(blank)→?"),
    (440, 0, "cursor?"), (440, 1, "cursor?"), (440, 2, "cursor?"), (440, 3, "cursor?"),
]

# Render all false blanks in a grid
SCALE = 8
cols_per_row = 10
n_items = len(false_blanks)
n_rows = (n_items + cols_per_row - 1) // cols_per_row

cell_render_w = CHAR_W * SCALE + 4
cell_render_h = CHAR_H * SCALE + 30  # room for labels

sheet_w = cols_per_row * cell_render_w + 4
sheet_h = n_rows * cell_render_h + 4
sheet = Image.new('RGB', (sheet_w, sheet_h), (20, 20, 40))
draw = ImageDraw.Draw(sheet)

for idx, (cell, bit, label) in enumerate(false_blanks):
    row = idx // cols_per_row
    col = idx % cols_per_row
    sx = col * cell_render_w + 4
    sy = row * cell_render_h + 4

    img, count = extract_glyph(cell, bit)
    display = img.resize((CHAR_W * SCALE, CHAR_H * SCALE), Image.NEAREST)
    sheet.paste(display, (sx, sy))

    draw.text((sx, sy + CHAR_H * SCALE + 2), f"C{cell}b{bit}", fill=(200, 200, 200))
    draw.text((sx, sy + CHAR_H * SCALE + 14), f"{count}px", fill=(150, 150, 255))

sheet.save(os.path.join(OUTPUT_DIR, "false_blanks.png"))
print(f"Saved false_blanks.png ({n_items} cells)")

# === Render Row 14 all 4 bitplanes side by side ===
print("\n=== Row 14 Detail (all 4 bitplanes) ===")
n_cells = 21  # cells 294-314
cell_w = (CHAR_W * SCALE + 2) * 4 + 8  # 4 bitplanes per cell
cell_h = CHAR_H * SCALE + 30

sheet_w = 7 * cell_w + 4  # 7 cells per row
sheet_h = 3 * cell_h + 4  # 3 rows of 7
sheet = Image.new('RGB', (sheet_w, sheet_h), (20, 20, 40))
draw = ImageDraw.Draw(sheet)

for i in range(21):
    cell = 294 + i
    row = i // 7
    col = i % 7
    base_x = col * cell_w + 4
    base_y = row * cell_h + 4

    for bit in range(4):
        img, count = extract_glyph(cell, bit)
        display = img.resize((CHAR_W * SCALE, CHAR_H * SCALE), Image.NEAREST)
        bx = base_x + bit * (CHAR_W * SCALE + 2)
        sheet.paste(display, (bx, base_y))

        color = (100, 255, 100) if count > 2 else (255, 80, 80)
        draw.text((bx, base_y + CHAR_H * SCALE + 2), f"b{bit}:{count}", fill=color)

    draw.text((base_x, base_y + CHAR_H * SCALE + 14), f"Cell {cell}", fill=(200, 200, 200))

sheet.save(os.path.join(OUTPUT_DIR, "row14_detail.png"))
print("Saved row14_detail.png")

# === Render Row 13 last cells (290-293) all bitplanes ===
print("\n=== Row 13 tail (cells 288-293) all bitplanes ===")
for cell in range(288, 294):
    for bit in range(4):
        img, count = extract_glyph(cell, bit)
        img_scaled = img.resize((CHAR_W * SCALE, CHAR_H * SCALE), Image.NEAREST)
        img_scaled.save(os.path.join(OUTPUT_DIR, f"cell{cell}_bit{bit}_{count}px.png"))
        print(f"  Cell {cell} bit{bit}: {count}px")

# === Cell 440 (16x16 cursor) ===
print("\n=== Cell 440 (16x16) all bitplanes ===")
for bit in range(4):
    img, count = extract_glyph(440, bit)
    img_scaled = img.resize((16 * SCALE, 16 * SCALE), Image.NEAREST)
    img_scaled.save(os.path.join(OUTPUT_DIR, f"cell440_bit{bit}_{count}px.png"))
    print(f"  Cell 440 bit{bit}: {count}px, size={img.size}")

# === Cell 439 (documented as cursor) ===
print("\n=== Cell 439 (documented as cursor) ===")
for bit in range(4):
    img, count = extract_glyph(439, bit)
    print(f"  Cell 439 bit{bit}: {count}px")
    # Also check raw index values
    grow = 439 // 21
    gcol = 439 % 21
    x0 = gcol * CHAR_W
    y0 = grow * CHAR_H
    print(f"    Position: ({x0},{y0}) = row {grow}, col {gcol}")
    raw_vals = set()
    for dy in range(CHAR_H):
        for dx in range(CHAR_W):
            raw_vals.add(indices[y0+dy][x0+dx])
    print(f"    Raw index values: {sorted(raw_vals)}")

# === Cell 125 ===
print("\n=== Cell 125 all bitplanes ===")
for bit in range(4):
    img, count = extract_glyph(125, bit)
    img_scaled = img.resize((CHAR_W * SCALE, CHAR_H * SCALE), Image.NEAREST)
    img_scaled.save(os.path.join(OUTPUT_DIR, f"cell125_bit{bit}_{count}px.png"))
    print(f"  Cell 125 bit{bit}: {count}px")

# === Cell 356 ===
print("\n=== Cell 356 all bitplanes ===")
for bit in range(4):
    img, count = extract_glyph(356, bit)
    img_scaled = img.resize((CHAR_W * SCALE, CHAR_H * SCALE), Image.NEAREST)
    img_scaled.save(os.path.join(OUTPUT_DIR, f"cell356_bit{bit}_{count}px.png"))
    print(f"  Cell 356 bit{bit}: {count}px")

print("\n=== Done ===")
