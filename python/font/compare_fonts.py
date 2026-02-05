#!/usr/bin/env python3
"""
Compare original vs patched COMM.IMG font.

Generates side-by-side comparison images showing which glyphs changed.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

# === Constants ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "..", "..")
ORIGINAL_PATH = os.path.join(BASE_DIR, "..", "COMM.IMG")
PATCHED_PATH = os.path.join(BASE_DIR, "output", "patched", "COMM.IMG")
CHARMAP_PATH = os.path.join(BASE_DIR, "output", "patched", "S100_charmap.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "font", "comparison")

ROW_WIDTH = 896  # bytes per scanline
GRID_COLS = 21
GRID_ROWS = 21
CELL_SIZE = 12
SCALE = 4


def extract_cell(data, cell_index, bitplane=0):
    """Extract a single cell from COMM.IMG as a PIL Image."""
    row = cell_index // GRID_COLS
    col = cell_index % GRID_COLS
    x0 = col * CELL_SIZE
    y0 = row * CELL_SIZE

    img = Image.new("L", (CELL_SIZE, CELL_SIZE), 0)
    pixels = img.load()

    mask = 1 << bitplane

    for dy in range(CELL_SIZE):
        for dx in range(CELL_SIZE):
            px = x0 + dx
            py = y0 + dy
            byte_offset = py * ROW_WIDTH + px // 2
            if byte_offset >= len(data):
                continue
            byte_val = data[byte_offset]
            if px % 2 == 0:
                pix_val = byte_val & 0x0F
            else:
                pix_val = (byte_val >> 4) & 0x0F

            if pix_val & mask:
                pixels[dx, dy] = 255

    return img


def cells_differ(orig_data, patch_data, cell_index):
    """Check if a cell differs between original and patched."""
    row = cell_index // GRID_COLS
    col = cell_index % GRID_COLS
    x0 = col * CELL_SIZE
    y0 = row * CELL_SIZE

    for dy in range(CELL_SIZE):
        for dx in range(CELL_SIZE):
            px = x0 + dx
            py = y0 + dy
            byte_offset = py * ROW_WIDTH + px // 2
            if byte_offset >= len(orig_data) or byte_offset >= len(patch_data):
                continue
            if orig_data[byte_offset] != patch_data[byte_offset]:
                return True
    return False


def load_charmap():
    """Load character mapping from charmap.txt."""
    mapping = {}
    if not os.path.exists(CHARMAP_PATH):
        return mapping

    with open(CHARMAP_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Format: char -> charID -> hex
            parts = line.split(' -> ')
            if len(parts) >= 2:
                char = parts[0]
                try:
                    char_id = int(parts[1])
                    mapping[char_id] = char
                except:
                    pass
    return mapping


def generate_comparison():
    """Generate comparison images."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading font files...")
    orig_data = open(ORIGINAL_PATH, "rb").read()
    patch_data = open(PATCHED_PATH, "rb").read()

    print("Loading character mapping...")
    charmap = load_charmap()

    # Find all cells that differ
    print("Finding changed cells...")
    changed_cells = []
    for cell in range(GRID_ROWS * GRID_COLS):
        if cells_differ(orig_data, patch_data, cell):
            changed_cells.append(cell)

    print(f"Found {len(changed_cells)} changed cells out of {GRID_ROWS * GRID_COLS}")

    # Generate individual comparison for changed cells
    print("\nGenerating comparison images...")

    # Create a summary grid (8 columns, many rows)
    cols = 8
    rows = (len(changed_cells) + cols - 1) // cols

    cell_w = CELL_SIZE * SCALE
    cell_h = CELL_SIZE * SCALE
    label_h = 20
    pair_w = cell_w * 2 + 10  # orig + patched + gap
    pair_h = cell_h + label_h

    grid_w = cols * pair_w + 10
    grid_h = rows * pair_h + 30

    grid_img = Image.new("RGB", (grid_w, grid_h), (40, 40, 40))
    draw = ImageDraw.Draw(grid_img)

    # Try to use a font that supports Korean
    try:
        font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 14)
    except:
        font = ImageFont.load_default()

    draw.text((10, 5), "Original vs Patched COMM.IMG Comparison (bitplane 0)", fill=(255, 255, 255), font=font)

    for i, cell in enumerate(changed_cells):
        col_idx = i % cols
        row_idx = i // cols

        x = col_idx * pair_w + 5
        y = row_idx * pair_h + 30

        # Extract cells from both
        orig_cell = extract_cell(orig_data, cell, bitplane=0)
        patch_cell = extract_cell(patch_data, cell, bitplane=0)

        # Scale up
        orig_scaled = orig_cell.resize((cell_w, cell_h), Image.NEAREST)
        patch_scaled = patch_cell.resize((cell_w, cell_h), Image.NEAREST)

        # Paste
        grid_img.paste(orig_scaled, (x, y))
        grid_img.paste(patch_scaled, (x + cell_w + 10, y))

        # Label
        char = charmap.get(cell, "")
        label = f"{cell}: {char}" if char else f"{cell}"
        draw.text((x, y + cell_h + 2), label, fill=(200, 200, 200), font=font)

    output_path = os.path.join(OUTPUT_DIR, "font_comparison_changed.png")
    grid_img.save(output_path)
    print(f"Saved: {output_path}")

    # Also generate full grid comparison (side by side)
    print("\nGenerating full grid comparison...")
    full_w = GRID_COLS * CELL_SIZE * SCALE
    full_h = GRID_ROWS * CELL_SIZE * SCALE

    orig_full = Image.new("L", (full_w, full_h), 0)
    patch_full = Image.new("L", (full_w, full_h), 0)

    for cell in range(GRID_ROWS * GRID_COLS):
        row = cell // GRID_COLS
        col = cell % GRID_COLS

        orig_cell = extract_cell(orig_data, cell, bitplane=0)
        patch_cell = extract_cell(patch_data, cell, bitplane=0)

        orig_scaled = orig_cell.resize((CELL_SIZE * SCALE, CELL_SIZE * SCALE), Image.NEAREST)
        patch_scaled = patch_cell.resize((CELL_SIZE * SCALE, CELL_SIZE * SCALE), Image.NEAREST)

        x = col * CELL_SIZE * SCALE
        y = row * CELL_SIZE * SCALE

        orig_full.paste(orig_scaled, (x, y))
        patch_full.paste(patch_scaled, (x, y))

    # Save full grids
    orig_path = os.path.join(OUTPUT_DIR, "original_font_grid.png")
    patch_path = os.path.join(OUTPUT_DIR, "patched_font_grid.png")
    orig_full.save(orig_path)
    patch_full.save(patch_path)
    print(f"Saved: {orig_path}")
    print(f"Saved: {patch_path}")

    # Create side-by-side
    combined = Image.new("RGB", (full_w * 2 + 20, full_h + 40), (40, 40, 40))
    draw = ImageDraw.Draw(combined)

    draw.text((10, 5), "Original (Japanese)", fill=(255, 255, 255), font=font)
    draw.text((full_w + 30, 5), "Patched (Korean)", fill=(255, 255, 255), font=font)

    combined.paste(orig_full.convert("RGB"), (0, 40))
    combined.paste(patch_full.convert("RGB"), (full_w + 20, 40))

    combined_path = os.path.join(OUTPUT_DIR, "font_comparison_full.png")
    combined.save(combined_path)
    print(f"Saved: {combined_path}")

    print("\nDone!")
    return changed_cells


if __name__ == "__main__":
    generate_comparison()
