#!/usr/bin/env python3
"""
View a specific font cell from COMM.IMG, showing all 4 bitplanes.

Usage:
    python view_char.py <row> <col>            # row 0-20, col 0-20
    python view_char.py --cell <cell>          # cell 0-440
    python view_char.py <row> <col> --no-plot  # skip matplotlib window
    python view_char.py <row> <col> --no-save  # skip PNG save
    python view_char.py <row> <col> --bit 2   # show only bit 2
"""

import argparse
import os
import re
import sys

from PIL import Image

# === Constants ===
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "COMM.IMG")
CHARS_MD_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "COMM_IMG_chars.md")
ROW_WIDTH = 896  # bytes per scanline in COMM.IMG
GRID_COLS = 21
CELL_SIZE = 12  # 12x12 cell (11x11 glyph + 1px margin)
SPECIAL_CELL = 440
SPECIAL_SIZE = 16
SCALE = 8


def parse_args():
    parser = argparse.ArgumentParser(
        description="View a font cell from COMM.IMG with 4 bitplanes."
    )
    parser.add_argument("row", type=int, nargs="?", help="Grid row (0-20)")
    parser.add_argument("col", type=int, nargs="?", help="Grid col (0-20)")
    parser.add_argument("--cell", type=int, default=None, help="Cell index (0-440)")
    parser.add_argument("--bit", type=int, default=None, choices=[0, 1, 2, 3],
                        help="Show only this bitplane (0-3)")
    parser.add_argument("--no-plot", action="store_true", help="Skip matplotlib display")
    parser.add_argument("--no-save", action="store_true", help="Skip PNG save")
    args = parser.parse_args()

    if args.cell is not None:
        if not 0 <= args.cell <= 440:
            parser.error("--cell must be 0-440")
        args.row = args.cell // GRID_COLS
        args.col = args.cell % GRID_COLS
    elif args.row is None or args.col is None:
        parser.error("Provide row and col, or use --cell")

    if not (0 <= args.row <= 20 and 0 <= args.col <= 20):
        parser.error("row and col must be 0-20")

    args.cell_index = args.row * GRID_COLS + args.col
    return args


def load_char_labels():
    """Parse COMM_IMG_chars.md and return {cell: [bit0, bit1, bit2, bit3]}."""
    labels = {}
    if not os.path.exists(CHARS_MD_PATH):
        return labels
    text = open(CHARS_MD_PATH, "r", encoding="utf-8").read()
    pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*\|"
        r"\s*\(\d+,\d+\)\s*\|\s*\d+\s*\|"
        r"\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    )
    for m in pattern.finditer(text):
        cell = int(m.group(1))
        labels[cell] = [m.group(i).strip() for i in range(2, 6)]
    return labels


def extract_bitplanes(data, row, col):
    """Extract 4 bitplane images for the cell at (row, col)."""
    x0 = col * CELL_SIZE
    y0 = row * CELL_SIZE
    cell_index = row * GRID_COLS + col

    if cell_index == SPECIAL_CELL:
        w, h = SPECIAL_SIZE, SPECIAL_SIZE
    else:
        w, h = CELL_SIZE, CELL_SIZE

    # Decode 4bpp pixel indices for the cell region
    pixels = [[0] * w for _ in range(h)]
    for dy in range(h):
        for dx in range(w):
            px = x0 + dx
            py = y0 + dy
            byte_offset = py * ROW_WIDTH + px // 2
            byte_val = data[byte_offset]
            if px % 2 == 0:
                pixels[dy][dx] = byte_val & 0x0F
            else:
                pixels[dy][dx] = (byte_val >> 4) & 0x0F

    planes = []
    for bit in range(4):
        mask = 1 << bit
        img = Image.new("L", (w, h), 0)
        px = img.load()
        for dy in range(h):
            for dx in range(w):
                if pixels[dy][dx] & mask:
                    px[dx, dy] = 255
        planes.append(img)

    return planes, pixels, w, h


def print_ascii(planes, labels, w, h, bit_filter=None):
    """Print ASCII art for each bitplane."""
    for bit, img in enumerate(planes):
        if bit_filter is not None and bit != bit_filter:
            continue
        px = img.load()
        tag = f"  [{labels[bit]}]" if labels else ""
        print(f"--- Bit {bit}{tag} ---")
        for y in range(h):
            row_str = ""
            for x in range(w):
                row_str += "\u2588" if px[x, y] else "\u00b7"
            print(f"  {row_str}")
        print()


def save_png(planes, labels, cell_index, w, h, bit_filter=None):
    """Save an 8x-scaled PNG with bitplanes side by side."""
    if bit_filter is not None:
        selected = [planes[bit_filter]]
    else:
        selected = planes

    gap = 2
    n = len(selected)
    total_w = n * w * SCALE + (n - 1) * gap
    total_h = h * SCALE
    out = Image.new("L", (total_w, total_h), 0)

    for i, img in enumerate(selected):
        scaled = img.resize((w * SCALE, h * SCALE), Image.NEAREST)
        out.paste(scaled, (i * (w * SCALE + gap), 0))

    output_dir = os.path.join(_SCRIPT_DIR, "..", "..", "output", "font", "extracted")
    os.makedirs(output_dir, exist_ok=True)
    if bit_filter is not None:
        fname = os.path.join(output_dir, f"char_{cell_index:03d}_bit{bit_filter}.png")
    else:
        fname = os.path.join(output_dir, f"char_{cell_index:03d}.png")
    out.save(fname)
    print(f"Saved {fname}")


def show_plot(planes, labels, cell_index, w, h, bit_filter=None):
    """Show matplotlib figure with bitplane subplots."""
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]

    if bit_filter is not None:
        fig, ax = plt.subplots(1, 1, figsize=(3, 3))
        tag = f"\n{labels[bit_filter]}" if labels else ""
        ax.imshow(planes[bit_filter], cmap="gray", interpolation="nearest",
                  vmin=0, vmax=255)
        ax.set_title(f"Bit {bit_filter}{tag}")
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        fig, axes = plt.subplots(1, 4, figsize=(10, 3))
        for i, (ax, img) in enumerate(zip(axes, planes)):
            tag = f"\n{labels[i]}" if labels else ""
            ax.imshow(img, cmap="gray", interpolation="nearest", vmin=0, vmax=255)
            ax.set_title(f"Bit {i}{tag}")
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle(f"Cell {cell_index} ({w}\u00d7{h})", fontsize=14)
    plt.tight_layout()
    plt.show()


def main():
    args = parse_args()
    data = open(COMM_IMG_PATH, "rb").read()

    char_labels = load_char_labels()
    labels = char_labels.get(args.cell_index)

    planes, pixels, w, h = extract_bitplanes(data, args.row, args.col)

    print(f"Cell {args.cell_index}  (row={args.row}, col={args.col})  {w}\u00d7{h}")
    if labels:
        print(f"Doc: {labels}")
    print()

    print_ascii(planes, labels, w, h, bit_filter=args.bit)

    if not args.no_save:
        save_png(planes, labels, args.cell_index, w, h, bit_filter=args.bit)

    if not args.no_plot:
        show_plot(planes, labels, args.cell_index, w, h, bit_filter=args.bit)


if __name__ == "__main__":
    main()
