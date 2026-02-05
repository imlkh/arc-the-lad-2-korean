#!/usr/bin/env python3
"""
Validate COMM_IMG_chars.md against actual COMM.IMG binary data.

Checks:
1. Byte offset formula correctness
2. Blank vs non-blank cell detection
3. Renders all 1764 glyphs to a validation sheet
4. Reports discrepancies with the documented table
"""

import re
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# === Configuration ===
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "..", "COMM.IMG")
CHARS_MD_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "COMM_IMG_chars.md")
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "validation")
ROW_WIDTH = 896       # bytes per row in COMM.IMG
CHAR_W, CHAR_H = 12, 12  # 12x12 cell (11x11 glyph + 1px margin)
GRID_COLS, GRID_ROWS = 21, 21
TOTAL_CELLS = GRID_COLS * GRID_ROWS  # 441

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Step 1: Read COMM.IMG and build 256x256 index map ===
data = open(COMM_IMG_PATH, "rb").read()
print(f"COMM.IMG size: {len(data)} bytes")

indices = [[0]*256 for _ in range(256)]
for y in range(256):
    for xb in range(128):
        offset = y * ROW_WIDTH + xb
        byte = data[offset]
        indices[y][xb * 2] = byte & 0x0F
        indices[y][xb * 2 + 1] = (byte >> 4) & 0x0F

# === Step 2: Validate byte offset formula ===
print("\n=== Byte Offset Formula Validation ===")
# Formula from doc: byte_offset = row * 12 * 896 + col * 6
errors_offset = []
for cell in range(TOTAL_CELLS):
    grow = cell // GRID_COLS
    gcol = cell % GRID_COLS
    # Pixel coordinates
    x0 = gcol * CHAR_W  # pixel x
    y0 = grow * CHAR_H  # pixel y
    # Byte offset from pixel coords: y0 * ROW_WIDTH + x0 // 2
    actual_offset = y0 * ROW_WIDTH + x0 // 2
    # Formula from doc
    formula_offset = grow * 12 * ROW_WIDTH + gcol * 6
    # row * 12 * 896: each grid row = 12 pixel rows (12px cell) * 896 bytes
    # col * 6: each grid col = 12 pixels (12px cell), at 4bpp = 6 bytes
    if actual_offset != formula_offset:
        errors_offset.append((cell, grow, gcol, actual_offset, formula_offset))

if errors_offset:
    print(f"  ERRORS: {len(errors_offset)} offset mismatches!")
    for cell, gr, gc, act, form in errors_offset[:5]:
        print(f"    Cell {cell} (row={gr}, col={gc}): actual={act}, formula={form}")
else:
    print(f"  OK: All {TOTAL_CELLS} cell offsets match formula (row*12*896 + col*6)")

# === Step 3: Extract all glyphs and detect blank/non-blank ===
print("\n=== Extracting all 1764 glyphs ===")

glyph_images = {}  # (cell, bit) -> PIL Image
glyph_pixel_counts = {}  # (cell, bit) -> number of set pixels

for cell in range(TOTAL_CELLS):
    grow = cell // GRID_COLS
    gcol = cell % GRID_COLS
    x0 = gcol * CHAR_W
    y0 = grow * CHAR_H

    # Last cell (440) is 16x16
    if grow == 20 and gcol == 20:
        w, h = 16, 16
    else:
        w, h = CHAR_W, CHAR_H

    for bit in range(4):
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
        glyph_images[(cell, bit)] = img
        glyph_pixel_counts[(cell, bit)] = count

# === Step 4: Parse the markdown table ===
print("\n=== Parsing COMM_IMG_chars.md ===")

md_text = open(CHARS_MD_PATH, "r", encoding="utf-8").read()

# Parse table rows: | Cell | Row | Col | Pixel (x,y) | Byte Offset | Bit0 | Bit1 | Bit2 | Bit3 |
table_pattern = re.compile(
    r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|'
    r'\s*\((\d+),(\d+)\)\s*\|\s*(\d+)\s*\|'
    r'\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|'
)

md_entries = {}  # cell -> {row, col, pixel_x, pixel_y, byte_offset, bits: [str, str, str, str]}
for m in table_pattern.finditer(md_text):
    cell = int(m.group(1))
    row = int(m.group(2))
    col = int(m.group(3))
    px_x = int(m.group(4))
    px_y = int(m.group(5))
    byte_off = int(m.group(6))
    bits = [m.group(7).strip(), m.group(8).strip(), m.group(9).strip(), m.group(10).strip()]
    md_entries[cell] = {
        'row': row, 'col': col,
        'pixel_x': px_x, 'pixel_y': px_y,
        'byte_offset': byte_off,
        'bits': bits
    }

print(f"  Parsed {len(md_entries)} cell entries from markdown")

# === Step 5: Validate coordinates and byte offsets ===
print("\n=== Validating Parsed Entries ===")

errors_coord = []
errors_byteoff = []
for cell, entry in sorted(md_entries.items()):
    grow = cell // GRID_COLS
    gcol = cell % GRID_COLS

    # Check row/col
    if entry['row'] != grow or entry['col'] != gcol:
        errors_coord.append((cell, entry['row'], entry['col'], grow, gcol))

    # Check pixel coords
    expected_px = gcol * CHAR_W
    expected_py = grow * CHAR_H
    if entry['pixel_x'] != expected_px or entry['pixel_y'] != expected_py:
        errors_coord.append((cell, f"pixel ({entry['pixel_x']},{entry['pixel_y']}) != expected ({expected_px},{expected_py})"))

    # Check byte offset
    expected_offset = grow * 12 * ROW_WIDTH + gcol * 6
    if entry['byte_offset'] != expected_offset:
        errors_byteoff.append((cell, entry['byte_offset'], expected_offset))

if errors_coord:
    print(f"  COORDINATE ERRORS: {len(errors_coord)}")
    for e in errors_coord[:10]:
        print(f"    {e}")
else:
    print(f"  OK: All coordinates correct")

if errors_byteoff:
    print(f"  BYTE OFFSET ERRORS: {len(errors_byteoff)}")
    for cell, doc, exp in errors_byteoff[:10]:
        print(f"    Cell {cell}: doc={doc}, expected={exp}")
else:
    print(f"  OK: All byte offsets correct")

# === Step 6: Validate blank detection ===
print("\n=== Blank Cell Validation ===")

BLANK_THRESHOLD = 2  # pixels - allow 1-2 noise pixels

blank_mismatches = []
for cell, entry in sorted(md_entries.items()):
    for bit in range(4):
        bit_label = entry['bits'][bit]
        is_doc_blank = bit_label.lower() in ['(blank)', 'blank', '']
        pixel_count = glyph_pixel_counts.get((cell, bit), 0)
        is_actual_blank = pixel_count <= BLANK_THRESHOLD

        if is_doc_blank != is_actual_blank:
            blank_mismatches.append({
                'cell': cell,
                'bit': bit,
                'doc_label': bit_label,
                'doc_blank': is_doc_blank,
                'pixel_count': pixel_count,
                'actual_blank': is_actual_blank
            })

if blank_mismatches:
    print(f"  MISMATCHES: {len(blank_mismatches)}")
    for mm in blank_mismatches:
        status = "doc=blank but has pixels" if mm['doc_blank'] else "doc=char but no pixels"
        print(f"    Cell {mm['cell']} bit{mm['bit']}: {status} "
              f"(doc='{mm['doc_label']}', pixels={mm['pixel_count']})")
else:
    print(f"  OK: All blank/non-blank entries match")

# === Step 7: Check for undocumented cells ===
print("\n=== Coverage Check ===")
undocumented = []
for cell in range(TOTAL_CELLS):
    if cell not in md_entries:
        has_pixels = any(glyph_pixel_counts.get((cell, b), 0) > BLANK_THRESHOLD for b in range(4))
        if has_pixels:
            undocumented.append(cell)

if undocumented:
    print(f"  WARNING: {len(undocumented)} cells with pixels not in markdown: {undocumented[:20]}")
else:
    print(f"  OK: All non-blank cells are documented")

# === Step 8: Detect duplicate characters across bitplanes ===
# In rows 20 (UI elements), all 4 bitplanes should be identical
print("\n=== Row 20 UI Element Bitplane Check ===")
row20_issues = []
for cell in range(420, 441):
    imgs = [glyph_images[(cell, b)] for b in range(4)]
    # Compare pixel data
    base = list(imgs[0].getdata())
    for bit in range(1, 4):
        other = list(imgs[bit].getdata())
        if base != other:
            row20_issues.append((cell, bit))

if row20_issues:
    print(f"  DIFFERENCES: {len(row20_issues)} bitplane mismatches in row 20")
    for cell, bit in row20_issues:
        print(f"    Cell {cell} bit{bit} differs from bit0")
else:
    print(f"  OK: Row 20 cells identical across all bitplanes (as documented)")

# === Step 9: Render validation sheets ===
print("\n=== Rendering Validation Sheets ===")

# Render one sheet per bitplane showing all 441 cells in 21x21 grid
SCALE = 4
LABEL_H = 14  # height for cell number label
CELL_RENDER_W = CHAR_W * SCALE
CELL_RENDER_H = CHAR_H * SCALE + LABEL_H

for bit in range(4):
    sheet_w = GRID_COLS * (CELL_RENDER_W + 2) + 2
    sheet_h = GRID_ROWS * (CELL_RENDER_H + 2) + 2
    sheet = Image.new('RGB', (sheet_w, sheet_h), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)

    for cell in range(TOTAL_CELLS):
        grow = cell // GRID_COLS
        gcol = cell % GRID_COLS

        sx = gcol * (CELL_RENDER_W + 2) + 2
        sy = grow * (CELL_RENDER_H + 2) + 2

        img = glyph_images[(cell, bit)]
        # Resize to display size
        display_img = img.resize((CELL_RENDER_W, CHAR_H * SCALE), Image.NEAREST)
        sheet.paste(display_img, (sx, sy))

        # Label
        pc = glyph_pixel_counts[(cell, bit)]
        label = f"{cell}"
        color = (100, 100, 100) if pc <= BLANK_THRESHOLD else (200, 200, 200)
        draw.text((sx, sy + CHAR_H * SCALE), label, fill=color)

        # Mark documented label if available
        if cell in md_entries:
            doc_label = md_entries[cell]['bits'][bit]
            if doc_label and '?' in doc_label:
                # Draw yellow border for uncertain chars
                draw.rectangle([sx-1, sy-1, sx+CELL_RENDER_W, sy+CHAR_H*SCALE],
                              outline=(255, 255, 0))

    sheet.save(os.path.join(OUTPUT_DIR, f"validation_bit{bit}.png"))
    print(f"  Saved validation_bit{bit}.png")

# === Step 10: Render a combined sheet with doc labels ===
# Create a more detailed sheet for first 3 rows (hiragana, katakana, latin)
# where we can most easily validate
print("\n=== Detailed Validation for Rows 0-3 ===")

DETAIL_SCALE = 6
for bit in range(4):
    # 21 cols x 4 rows (rows 0-3)
    n_rows = 4
    cell_w = CHAR_W * DETAIL_SCALE + 4
    cell_h = CHAR_H * DETAIL_SCALE + 20  # room for label
    sheet_w = GRID_COLS * cell_w + 4
    sheet_h = n_rows * cell_h + 4
    sheet = Image.new('RGB', (sheet_w, sheet_h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)

    for row_idx in range(n_rows):
        for col_idx in range(GRID_COLS):
            cell = row_idx * GRID_COLS + col_idx
            sx = col_idx * cell_w + 4
            sy = row_idx * cell_h + 4

            img = glyph_images[(cell, bit)]
            display_img = img.resize((CHAR_W * DETAIL_SCALE, CHAR_H * DETAIL_SCALE), Image.NEAREST)
            sheet.paste(display_img, (sx, sy))

            if cell in md_entries:
                doc_label = md_entries[cell]['bits'][bit]
                pc = glyph_pixel_counts[(cell, bit)]
                info = f"{cell}:{doc_label}" if doc_label else f"{cell}:?"
                color = (150, 255, 150) if pc > BLANK_THRESHOLD else (255, 100, 100)
                draw.text((sx, sy + CHAR_H * DETAIL_SCALE + 2), info, fill=color)

    sheet.save(os.path.join(OUTPUT_DIR, f"detail_rows0-3_bit{bit}.png"))
    print(f"  Saved detail_rows0-3_bit{bit}.png")

# === Step 11: Statistics summary ===
print("\n=== Summary Statistics ===")
total_blank = sum(1 for c in range(TOTAL_CELLS) for b in range(4)
                  if glyph_pixel_counts.get((c, b), 0) <= BLANK_THRESHOLD)
total_nonblank = TOTAL_CELLS * 4 - total_blank
print(f"  Total slots: {TOTAL_CELLS * 4}")
print(f"  Non-blank: {total_nonblank}")
print(f"  Blank: {total_blank}")
print(f"  Documented slots: {len(md_entries) * 4}")

# Count uncertain entries
uncertain = sum(1 for entry in md_entries.values()
                for b in entry['bits'] if '?' in b)
print(f"  Uncertain (?): {uncertain}")

# Count documented blanks
doc_blanks = sum(1 for entry in md_entries.values()
                 for b in entry['bits']
                 if b.lower() in ['(blank)', 'blank', ''])
print(f"  Documented blanks: {doc_blanks}")

# === Step 12: Per-row pixel density analysis ===
print("\n=== Per-Row Average Pixel Density ===")
for grow in range(GRID_ROWS):
    row_counts = []
    for gcol in range(GRID_COLS):
        cell = grow * GRID_COLS + gcol
        for bit in range(4):
            row_counts.append(glyph_pixel_counts.get((cell, bit), 0))
    avg = sum(row_counts) / len(row_counts)
    non_blank = sum(1 for c in row_counts if c > BLANK_THRESHOLD)
    print(f"  Row {grow:2d}: avg={avg:5.1f}px, non-blank={non_blank}/{len(row_counts)}")

# === Step 13: Check hiragana ordering ===
print("\n=== Hiragana Ordering Check (Row 0) ===")
expected_hiragana = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉゃゅょっ")
actual_from_doc = []
for cell in range(21):  # cells 0-20
    if cell in md_entries:
        actual_from_doc.extend(md_entries[cell]['bits'])

# Compare character by character
mismatches = []
for i, (exp, act) in enumerate(zip(expected_hiragana, actual_from_doc)):
    act_clean = act.strip().replace('?', '')
    if exp != act_clean and act_clean:
        mismatches.append((i, exp, act_clean))

if mismatches:
    print(f"  Hiragana order mismatches: {len(mismatches)}")
    for idx, exp, act in mismatches:
        cell = idx // 4
        bit = idx % 4
        print(f"    Index {idx} (cell {cell}, bit{bit}): expected '{exp}', got '{act}'")
else:
    print(f"  OK: Hiragana in expected あいうえお order (first {len(expected_hiragana)} chars)")

# Check if last 4 in row 0 are actually katakana (cell 20 = ア イ ウ エ)
cell20 = md_entries.get(20, {}).get('bits', [])
if cell20:
    print(f"  Cell 20 (last in row 0): {cell20}")
    print(f"    Note: These are katakana (ア イ ウ エ), bridging to row 1")

# === Step 14: Check katakana ordering ===
print("\n=== Katakana Ordering Check (Cell 20 + Row 1) ===")
expected_katakana = list("アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワ")
# Cell 20 has ア イ ウ エ, then cells 21-41 continue
katakana_from_doc = []
if 20 in md_entries:
    katakana_from_doc.extend(md_entries[20]['bits'])
for cell in range(21, 40):  # cells 21-39
    if cell in md_entries:
        katakana_from_doc.extend(md_entries[cell]['bits'])

mismatches_k = []
for i, (exp, act) in enumerate(zip(expected_katakana, katakana_from_doc)):
    act_clean = act.strip().replace('?', '').replace('  ', ' ')
    if exp != act_clean and act_clean:
        mismatches_k.append((i, exp, act_clean))

if mismatches_k:
    print(f"  Katakana order mismatches: {len(mismatches_k)}")
    for idx, exp, act in mismatches_k:
        print(f"    Index {idx}: expected '{exp}', got '{act}'")
else:
    print(f"  OK: Katakana in expected order (first {min(len(expected_katakana), len(katakana_from_doc))} chars)")

# === Step 15: Check Latin/digit ordering ===
print("\n=== Latin/Digit Ordering Check (Cells 40-55) ===")
expected_latin = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
latin_from_doc = []
for cell in range(40, 56):  # cells 40-55
    if cell in md_entries:
        latin_from_doc.extend(md_entries[cell]['bits'])

mismatches_l = []
for i, (exp, act) in enumerate(zip(expected_latin, latin_from_doc)):
    act_clean = act.strip().replace('?', '')
    if exp != act_clean and act_clean:
        mismatches_l.append((i, exp, act_clean))

if mismatches_l:
    print(f"  Latin/digit order mismatches: {len(mismatches_l)}")
    for idx, exp, act in mismatches_l:
        print(f"    Index {idx}: expected '{exp}', got '{act}'")
else:
    print(f"  OK: Latin A-Z, a-z, 0-9 in expected order")

print("\n=== Validation Complete ===")
