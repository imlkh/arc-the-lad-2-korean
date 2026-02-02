#!/usr/bin/env python3
"""
Extract all Japanese characters (hiragana, katakana, kanji) from COMM_IMG_chars.md
with their position information in COMM.IMG.

Output: python/jp_char_positions.json

Each entry contains:
  - char: the Japanese character
  - cell: cell index (0-440)
  - row, col: grid position
  - bitplane: 0-3
  - char_id: encoding ID used in game text (1 + cell*4 + bitplane)
  - pixel_x, pixel_y: top-left pixel of this cell in the 256x256 font area
  - byte_offset: starting byte offset in COMM.IMG for this cell
  - row_stride: 896 bytes per scanline
  - cell_size: 12 (pixels, both width and height; 16 for cell 440)
  - bytes_per_row: 6 (cell_size / 2; 8 for cell 440)

To read/write a glyph in COMM.IMG:
  For each pixel row dy (0..cell_size-1):
    row_offset = byte_offset + dy * row_stride
    For each pixel dx (0..cell_size-1):
      byte_pos = row_offset + dx // 2
      if dx is even: nibble = byte & 0x0F
      if dx is odd:  nibble = (byte >> 4) & 0x0F
    The 4-bit pixel value has one bit per bitplane.
    To set bitplane N: pixel |= (1 << N)  if glyph pixel is on
    To clear bitplane N: pixel &= ~(1 << N)  if glyph pixel is off
"""

import json
import os
import re
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARS_MD_PATH = os.path.join(_SCRIPT_DIR, "..", "COMM_IMG_chars.md")
OUTPUT_PATH = os.path.join(_SCRIPT_DIR, "jp_char_positions.json")

ROW_STRIDE = 896
CELL_SIZE = 12
SPECIAL_CELL = 440
SPECIAL_SIZE = 16


def is_japanese_char(ch):
    """Return True if ch is a Japanese character (hiragana, katakana, or kanji)."""
    cp = ord(ch)
    # Hiragana: U+3040-U+309F
    if 0x3040 <= cp <= 0x309F:
        return True
    # Katakana: U+30A0-U+30FF (includes ー U+30FC)
    if 0x30A0 <= cp <= 0x30FF:
        return True
    # CJK Unified Ideographs: U+4E00-U+9FFF
    if 0x4E00 <= cp <= 0x9FFF:
        return True
    # CJK Unified Ideographs Extension A: U+3400-U+4DBF
    if 0x3400 <= cp <= 0x4DBF:
        return True
    return False


def main():
    text = open(CHARS_MD_PATH, "r", encoding="utf-8").read()
    pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        r"\s*\((\d+),(\d+)\)\s*\|\s*(\d+)\s*\|"
        r"\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    )

    entries = []
    for m in pattern.finditer(text):
        cell = int(m.group(1))
        row = int(m.group(2))
        col = int(m.group(3))
        pixel_x = int(m.group(4))
        pixel_y = int(m.group(5))
        byte_offset = int(m.group(6))
        labels = [m.group(i).strip() for i in range(7, 11)]

        cell_size = SPECIAL_SIZE if cell == SPECIAL_CELL else CELL_SIZE

        for bitplane, label in enumerate(labels):
            if not label or label.lower() in ("(blank)", "blank"):
                continue
            clean = label.rstrip("?").strip()
            if not clean or len(clean) != 1:
                continue
            if not is_japanese_char(clean):
                continue

            char_id = 1 + cell * 4 + bitplane

            entries.append({
                "char": clean,
                "cell": cell,
                "row": row,
                "col": col,
                "bitplane": bitplane,
                "char_id": char_id,
                "pixel_x": pixel_x,
                "pixel_y": pixel_y,
                "byte_offset": byte_offset,
                "row_stride": ROW_STRIDE,
                "cell_size": cell_size,
                "bytes_per_row": cell_size // 2,
            })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    # Stats
    hiragana = sum(1 for e in entries if 0x3040 <= ord(e["char"]) <= 0x309F)
    katakana = sum(1 for e in entries if 0x30A0 <= ord(e["char"]) <= 0x30FF)
    kanji = sum(1 for e in entries if ord(e["char"]) >= 0x3400)
    unique_chars = len(set(e["char"] for e in entries))

    print(f"Extracted {len(entries)} Japanese character slots:")
    print(f"  Hiragana: {hiragana}")
    print(f"  Katakana: {katakana}")
    print(f"  Kanji:    {kanji}")
    print(f"  Unique:   {unique_chars}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
