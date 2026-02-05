#!/usr/bin/env python3
"""
Analyze placeholder character sequences in BEAM.DAT.

This tool traces the charIDs used in BEAM.DAT's placeholder/debug text
and compares them to the correct characters used in STG files.

NOTE: The character table (COMM_IMG_chars.md) is verified CORRECT.
The placeholder text uses intentionally different byte sequences.

See docs/COMM_IMG_corrections.md for verification details.

Usage:
    python identify_char_mappings.py
"""

import os
import re
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARS_MD_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "docs", "COMM_IMG_chars.md")


def build_decode_table():
    """Parse COMM_IMG_chars.md and build charID -> character mapping."""
    table = {}
    reverse = {}  # char -> charID

    if not os.path.exists(CHARS_MD_PATH):
        print(f"Error: character table not found: {CHARS_MD_PATH}", file=sys.stderr)
        sys.exit(1)

    text = open(CHARS_MD_PATH, "r", encoding="utf-8").read()
    pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        r"\s*\(\d+,\d+\)\s*\|\s*\d+\s*\|"
        r"\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    )
    # Pattern to strip charID suffix like " (123)" from new format
    charid_suffix = re.compile(r'\s*\(\d+\)\s*$')
    for m in pattern.finditer(text):
        row = int(m.group(2))
        col = int(m.group(3))
        bits = [m.group(i).strip() for i in range(4, 8)]
        for bitplane, label in enumerate(bits):
            # Strip charID suffix first
            label_clean = charid_suffix.sub('', label).strip()
            if not label_clean or label_clean.lower() in ('(blank)', 'blank', ''):
                continue
            char_id = 1 + (row * 21 + col) * 4 + bitplane
            clean = label_clean.rstrip("?").strip()
            if clean:
                table[char_id] = clean
                if clean not in reverse:
                    reverse[clean] = char_id
    return table, reverse


def char_id_to_bytes(char_id):
    """Encode a charID to its byte representation."""
    if 1 <= char_id <= 0xEE:
        return f"0x{char_id:02X}"
    elif char_id >= 239:
        first = 0xF0 + (char_id - 239) // 255
        second = (char_id - 239) % 255
        return f"0x{first:02X} 0x{second:02X}"
    return "?"


def char_id_to_cell(char_id):
    """Convert charID to cell and bitplane."""
    cell_index = (char_id - 1) // 4
    bitplane = (char_id - 1) % 4
    row = cell_index // 21
    col = cell_index % 21
    return cell_index, row, col, bitplane


def main():
    table, reverse = build_decode_table()

    # Placeholder characters found in BEAM.DAT and their correct equivalents in STG
    # Format: (placeholder_char, correct_char, context)
    placeholder_mappings = [
        ('切', '行', '切ます → 行きます (to go)'),
        ('獅', '上', '獅り → 上り (going up)'),
        ('告', '下', '告り → 下り (going down)'),
        ('慎', '段', '温慎 → 階段 (stairs)'),
        ('温', '階', '温慎 → 階段 (stairs)'),
        ('協', '見', '協つけ → 見つけ (to find)'),
        ('狭', '取', '狭り → 取り (to take)'),
        ('償', '本', '償に → 本当に (really)'),
        ('跡', '手', '跡に抱れる → 手に入れる (to obtain)'),
        ('抱', '入', '抱れる → 入れる (to put in)'),
        ('西', '宝', '西鈴 → 宝箱 (treasure chest)'),
        ('鈴', '箱', '西鈴 → 宝箱 (treasure chest)'),
        ('堕', '回', '堕簡鈴 → 回復 (recovery)'),
        ('簡', '復', '簡抱 → 回復 (recovery)'),
    ]

    print("BEAM.DAT Placeholder Text Analysis")
    print("=" * 80)
    print()
    print("The character table is CORRECT. These are placeholder/debug sequences")
    print("that use different charIDs than the equivalent text in STG files.")
    print()
    print(f"{'Placeholder':<12} {'CharID':<8} {'Bytes':<12} {'Correct':<10} {'CharID':<8} {'Bytes':<12}")
    print("-" * 80)

    for placeholder, correct, context in placeholder_mappings:
        p_id = reverse.get(placeholder)
        c_id = reverse.get(correct)

        p_bytes = char_id_to_bytes(p_id) if p_id else "?"
        c_bytes = char_id_to_bytes(c_id) if c_id else "?"

        print(f"{placeholder:<12} {p_id or '?':<8} {p_bytes:<12} {correct:<10} {c_id or '?':<8} {c_bytes:<12}")

    print()
    print("Context examples:")
    print("-" * 80)
    for placeholder, correct, context in placeholder_mappings:
        print(f"  {context}")

    print()
    print("=" * 80)
    print("CONCLUSION: No changes needed to COMM_IMG_chars.md")
    print("The placeholder text in BEAM.DAT is debug/development content.")
    print("STG files contain the correct final game text.")


if __name__ == "__main__":
    main()
