#!/usr/bin/env python3
"""
Generate COMM.IMG vs documented character comparison images.

For each bitplane, renders a 21x21 grid where each cell shows:
  - Left: extracted glyph from COMM.IMG (4x scaled)
  - Right: reference Unicode character rendered from font (same scale)
  - Below: label (cell number + documented character)

Skips blank/(blank) entries. Marks uncertain (?) entries with yellow border.

Output: output/validation/char_comparison_bit{0-3}.png
"""

import os
from PIL import Image, ImageDraw, ImageFont

from view_char import (
    COMM_IMG_PATH, GRID_COLS, CELL_SIZE, SPECIAL_CELL, SPECIAL_SIZE,
    extract_bitplanes, load_char_labels,
)

# === Configuration ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "..", "output", "validation", "comparison")

COMM_IMG_KOR_PATH = os.path.join(SCRIPT_DIR, "..", "..", "COMM_IMG_KR.IMG")

GRID_ROWS = 21
TOTAL_CELLS = GRID_COLS * GRID_ROWS  # 441

SCALE = 4              # 12x12 -> 48x48
GLYPH_PX = CELL_SIZE * SCALE   # 48
GAP = 4                # gap between extracted and reference glyph
LABEL_H = 14           # height for label text below glyphs
PAIR_W = GLYPH_PX + GAP + GLYPH_PX  # 100
PAIR_H = GLYPH_PX + LABEL_H          # 62
CELL_PAD = 4           # padding between cells in the grid

def find_japanese_font():
    """Find a Japanese font for reference rendering."""
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",  # macOS Hiragino
        "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS alternative
        "/Library/Fonts/Arial Unicode.ttf",  # macOS
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",  # Linux alternative
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

REFERENCE_FONT_PATH = find_japanese_font()
REFERENCE_FONT_SIZE = 36  # renders into 48x48 area

BLANK_THRESHOLD = 2    # pixels - cells with <= this many pixels are "blank"


def render_reference_char(char_label, ref_font):
    """Render a reference character into a GLYPH_PX x GLYPH_PX image.

    Returns None if the label is blank, purely uncertain, or a multi-char UI label.
    """
    if not char_label:
        return None

    low = char_label.lower().strip()
    if low in ('(blank)', 'blank', ''):
        return None

    # Strip trailing ? for uncertain chars — still render the base character
    clean = char_label.rstrip('?').strip()
    if not clean:
        return None

    # Skip multi-character UI labels like "+1", "SS", "cursor"
    if clean.startswith('+') or clean.lower() in ('ss', 'cursor'):
        return None

    # Render the character
    img = Image.new('L', (GLYPH_PX, GLYPH_PX), 0)
    draw = ImageDraw.Draw(img)
    draw.text((GLYPH_PX // 2, GLYPH_PX // 2), clean, font=ref_font, fill=255, anchor="mm")
    return img


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load COMM.IMG binary data
    print("Reading COMM.IMG...")
    data = open(COMM_IMG_PATH, "rb").read()
    # data = open(COMM_IMG_KOR_PATH, "rb").read()

    # Extract all glyphs using view_char's extraction
    print("Extracting glyphs...")
    glyph_images = {}       # (cell, bit) -> PIL Image
    glyph_pixel_counts = {} # (cell, bit) -> int

    for cell in range(TOTAL_CELLS):
        row = cell // GRID_COLS
        col = cell % GRID_COLS
        planes, _pixels, w, h = extract_bitplanes(data, row, col)
        for bit in range(4):
            glyph_images[(cell, bit)] = planes[bit]
            glyph_pixel_counts[(cell, bit)] = sum(
                1 for p in planes[bit].getdata() if p > 0
            )

    # Parse character labels from markdown
    print("Parsing COMM_IMG_chars.md...")
    char_labels = load_char_labels()  # {cell: [bit0, bit1, bit2, bit3]}
    print(f"  Parsed {len(char_labels)} cell entries")

    # Load reference font
    print(f"Loading reference font: {REFERENCE_FONT_PATH}")
    ref_font = ImageFont.truetype(REFERENCE_FONT_PATH, REFERENCE_FONT_SIZE)

    try:
        label_font = ImageFont.truetype(REFERENCE_FONT_PATH, 10)
    except Exception:
        label_font = ImageFont.load_default()

    # Render comparison sheets (one per bitplane)
    print("Rendering comparison sheets...")

    for bit in range(4):
        sheet_w = GRID_COLS * (PAIR_W + CELL_PAD) + CELL_PAD
        sheet_h = GRID_ROWS * (PAIR_H + CELL_PAD) + CELL_PAD
        sheet = Image.new('RGB', (sheet_w, sheet_h), (30, 30, 30))
        draw = ImageDraw.Draw(sheet)

        rendered_count = 0
        skipped_count = 0

        for cell in range(TOTAL_CELLS):
            grow = cell // GRID_COLS
            gcol = cell % GRID_COLS

            # Position in the output sheet
            sx = gcol * (PAIR_W + CELL_PAD) + CELL_PAD
            sy = grow * (PAIR_H + CELL_PAD) + CELL_PAD

            # Get extracted glyph, scale to display size
            ext_img = glyph_images[(cell, bit)]
            ext_scaled = ext_img.resize((GLYPH_PX, GLYPH_PX), Image.NEAREST)

            # Get documented label
            labels = char_labels.get(cell)
            doc_label = labels[bit] if labels else ""

            pixel_count = glyph_pixel_counts[(cell, bit)]
            is_blank = pixel_count <= BLANK_THRESHOLD
            is_doc_blank = doc_label.lower().strip() in ('(blank)', 'blank', '')

            # Render reference character
            ref_img = render_reference_char(doc_label, ref_font)

            # Paste extracted glyph (left side)
            sheet.paste(ext_scaled, (sx, sy))

            # Paste reference glyph (right side) if available
            if ref_img is not None:
                sheet.paste(ref_img, (sx + GLYPH_PX + GAP, sy))
                rendered_count += 1
            else:
                # Draw a dark placeholder for the reference side
                draw.rectangle(
                    [sx + GLYPH_PX + GAP, sy,
                     sx + GLYPH_PX + GAP + GLYPH_PX - 1, sy + GLYPH_PX - 1],
                    fill=(20, 20, 20)
                )
                skipped_count += 1

            # Draw dividing line between extracted and reference
            line_x = sx + GLYPH_PX + GAP // 2
            draw.line([(line_x, sy), (line_x, sy + GLYPH_PX - 1)], fill=(60, 60, 60))

            # Label below
            label_text = f"{cell}"
            if doc_label and doc_label.lower() not in ('(blank)', 'blank'):
                label_text += f":{doc_label}"

            if is_blank and is_doc_blank:
                label_color = (80, 80, 80)      # both blank — dim
            elif is_blank != is_doc_blank:
                label_color = (255, 100, 100)    # mismatch — red
            elif '?' in doc_label:
                label_color = (255, 255, 100)    # uncertain — yellow
            else:
                label_color = (200, 200, 200)    # normal

            draw.text((sx, sy + GLYPH_PX + 1), label_text, fill=label_color, font=label_font)

            # Border for uncertain chars
            if '?' in doc_label:
                draw.rectangle(
                    [sx - 1, sy - 1, sx + PAIR_W, sy + GLYPH_PX],
                    outline=(255, 255, 0)
                )

        out_path = os.path.join(OUTPUT_DIR, f"char_comparison_bit{bit}.png")
        # out_path = os.path.join(OUTPUT_DIR, f"char_comparison_bit{bit}_kor.png")
        sheet.save(out_path)
        print(f"  Saved {out_path}")
        print(f"    Rendered: {rendered_count}, Skipped (blank/UI): {skipped_count}")

    print("\nDone!")


if __name__ == "__main__":
    main()
