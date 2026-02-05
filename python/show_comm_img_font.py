#!/usr/bin/env python3
"""
Visualize the COMM.IMG font area before and after bitplane separation.

Generates a single image showing:
  - Left: Raw 4bpp composite (all 4 characters overlaid per cell)
  - Right: 4 separated bitplane layers (one character per layer)

COMM.IMG layout:
  - 896 bytes per row, 512 rows
  - Font area: top-left 256x256 pixels (128 bytes wide, 4bpp)
  - 4bpp: 2 pixels per byte (low nibble = left, high nibble = right)
  - 21x21 grid of 12x12 cells, 4 bitplanes per cell = 1,764 characters
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'COMM.IMG')

ROW_WIDTH = 896
FONT_W = 256
FONT_H = 256
CELL_SIZE = 12
GRID_COLS = 21
GRID_ROWS = 21

SCALE = 3          # upscale factor for display
GRID_COLOR = 80    # grid line brightness (0-255)
LABEL_H = 24       # pixels for label text above each panel
PADDING = 12       # pixels between panels
BG_COLOR = 32      # dark background


def read_font_indices(filepath):
    """Read COMM.IMG and return 256x256 list-of-lists of 4bpp index values."""
    with open(filepath, 'rb') as f:
        data = f.read()

    indices = [[0] * FONT_W for _ in range(FONT_H)]
    for y in range(FONT_H):
        for xb in range(FONT_W // 2):
            offset = y * ROW_WIDTH + xb
            byte = data[offset]
            indices[y][xb * 2] = byte & 0x0F
            indices[y][xb * 2 + 1] = (byte >> 4) & 0x0F
    return indices


def indices_to_composite(indices):
    """Convert 4bpp indices (0-15) to a grayscale image (0→0, 15→255)."""
    img = Image.new('L', (FONT_W, FONT_H), 0)
    px = img.load()
    for y in range(FONT_H):
        for x in range(FONT_W):
            px[x, y] = indices[y][x] * 17  # 0..15 → 0..255
    return img


def indices_to_bitplane(indices, bit):
    """Extract one bitplane as a white-on-black image."""
    mask = 1 << bit
    img = Image.new('L', (FONT_W, FONT_H), 0)
    px = img.load()
    for y in range(FONT_H):
        for x in range(FONT_W):
            if indices[y][x] & mask:
                px[x, y] = 255
    return img


def draw_cell_grid(img, color=GRID_COLOR):
    """Draw the 21x21 cell grid overlay on an image."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for i in range(GRID_COLS + 1):
        x = i * CELL_SIZE * SCALE
        if x < w:
            draw.line([(x, 0), (x, h - 1)], fill=color, width=1)
    for i in range(GRID_ROWS + 1):
        y = i * CELL_SIZE * SCALE
        if y < h:
            draw.line([(0, y), (w - 1, y)], fill=color, width=1)


def upscale(img, scale=SCALE):
    """Upscale with nearest-neighbor for pixel-art clarity."""
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def add_label(img, text):
    """Return a new image with a text label above the original."""
    w, h = img.size
    labeled = Image.new('L', (w, h + LABEL_H), BG_COLOR)
    draw = ImageDraw.Draw(labeled)
    # Center the label text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (w - tw) // 2
    draw.text((tx, 4), text, fill=230, font=font)
    labeled.paste(img, (0, LABEL_H))
    return labeled


def main():
    comm_img_path = COMM_IMG_PATH
    if len(sys.argv) > 1:
        comm_img_path = sys.argv[1]

    if not os.path.exists(comm_img_path):
        print(f"Error: {comm_img_path} not found")
        sys.exit(1)

    print(f"Reading: {comm_img_path}")
    indices = read_font_indices(comm_img_path)

    # --- Build the 5 panels ---
    # Composite
    composite = indices_to_composite(indices)
    composite_up = upscale(composite)
    draw_cell_grid(composite_up, color=60)
    composite_panel = add_label(composite_up, "Raw 4bpp Composite (all layers overlaid)")

    # 4 bitplanes
    bit_labels = [
        "Bit 0 (& 1) — Character A",
        "Bit 1 (& 2) — Character B",
        "Bit 2 (& 4) — Character C",
        "Bit 3 (& 8) — Character D",
    ]
    bitplane_panels = []
    for bit in range(4):
        bp = indices_to_bitplane(indices, bit)
        bp_up = upscale(bp)
        draw_cell_grid(bp_up, color=50)
        panel = add_label(bp_up, bit_labels[bit])
        bitplane_panels.append(panel)

    # --- Assemble final image ---
    # Layout: composite on top, 4 bitplanes in a 2x2 grid below
    pw = composite_panel.width   # panel width (all same)
    ph = composite_panel.height  # panel height (all same)

    # Top row: composite centered
    # Bottom rows: 2x2 grid of bitplanes
    total_w = pw * 2 + PADDING * 3
    total_h = LABEL_H + ph + PADDING + ph * 2 + PADDING * 2

    canvas = Image.new('L', (total_w, total_h), BG_COLOR)

    # Title
    draw = ImageDraw.Draw(canvas)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        title_font = ImageFont.load_default()
    title = "COMM.IMG Font — Before & After Bitplane Separation"
    tbbox = draw.textbbox((0, 0), title, font=title_font)
    ttw = tbbox[2] - tbbox[0]
    draw.text(((total_w - ttw) // 2, 2), title, fill=255, font=title_font)

    # Composite panel (centered in top row)
    cx = (total_w - pw) // 2
    cy = LABEL_H
    canvas.paste(composite_panel, (cx, cy))

    # Bitplane panels (2x2 grid)
    by_start = cy + ph + PADDING
    for i, panel in enumerate(bitplane_panels):
        col = i % 2
        row = i // 2
        bx = PADDING + col * (pw + PADDING)
        by = by_start + row * (ph + PADDING)
        canvas.paste(panel, (bx, by))

    out_path = os.path.join(SCRIPT_DIR, '..', 'COMM_IMG_font_bitplanes.png')
    canvas.save(out_path)
    print(f"Saved: {os.path.abspath(out_path)}")
    print(f"  Image size: {canvas.size[0]}x{canvas.size[1]} pixels")
    print(f"  Font area: {FONT_W}x{FONT_H} @ {SCALE}x scale")
    print(f"  Grid: {GRID_COLS}x{GRID_ROWS} cells, {CELL_SIZE}x{CELL_SIZE}px each")
    print(f"  Total character slots: {GRID_COLS * GRID_ROWS * 4}")


if __name__ == '__main__':
    main()
