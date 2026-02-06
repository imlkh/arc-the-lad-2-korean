#!/usr/bin/env python3
"""
Decode all *.STG files using template-driven dialogue extraction.

Usage:
    python decode_all_stg.py                # decode all STG files
    python decode_all_stg.py --find "エルク"  # filter by text pattern

Output: output/decoded/stg/<basename>.txt for each STG file.
"""

import argparse
import glob
import os
import sys

from decode_text import build_decode_table, scan_stg

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STG_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "..")  # Arc_The_Lad2/
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "decoded", "stg")


def decode_one(filepath, decode_table, find=None):
    """Decode a single STG file. Returns (lines, dialogue_count, stats)."""
    data = open(filepath, "rb").read()
    dialogues, templates, stats = scan_stg(data, decode_table)

    if find:
        dialogues = [d for d in dialogues if find in d[2]]

    lines = []
    prev_opcode = None
    for offset, consumed, text, context_opcode in dialogues:
        if prev_opcode is not None and context_opcode != prev_opcode:
            lines.append(
                f"  --- context: 0x{prev_opcode:04X} -> "
                f"0x{context_opcode:04X} ---"
            )
        prev_opcode = context_opcode
        display = text.replace("\n", "\\n")
        lines.append(f"  0x{offset:08X} [0x{context_opcode:04X}] {display}")

    return lines, len(dialogues), stats


def main():
    parser = argparse.ArgumentParser(
        description="Decode all STG files using template-driven extraction."
    )
    parser.add_argument("--find", metavar="TEXT",
                        help="Only include dialogues containing this text")
    args = parser.parse_args()

    stg_files = sorted(glob.glob(os.path.join(STG_DIR, "*.STG")))
    if not stg_files:
        print(f"No STG files found in {STG_DIR}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading character table...")
    decode_table = build_decode_table()
    print(f"  {len(decode_table)} characters loaded")
    print(f"Found {len(stg_files)} STG files\n")

    total_dialogues = 0
    total_templates = 0

    for filepath in stg_files:
        basename = os.path.basename(filepath)
        lines, dialogue_count, stats = decode_one(filepath, decode_table, find=args.find)

        out_path = os.path.join(OUTPUT_DIR, basename.replace(".STG", "_STG.txt"))

        orphan_menus = stats.get('orphan_menus_found', 0)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# {basename} — {dialogue_count} dialogues, "
                    f"{stats['total_templates']} templates "
                    f"({stats['bare']} bare, {stats['missed']} missed, "
                    f"{orphan_menus} orphan menus)\n\n")
            f.write("\n".join(lines))
            f.write("\n")

        total_dialogues += dialogue_count
        total_templates += stats['total_templates']

        print(f"  {basename}: {dialogue_count} dialogues / "
              f"{stats['total_templates']} templates "
              f"({stats['bare']} bare, {stats['missed']} missed, "
              f"{orphan_menus} orphan menus) "
              f"-> {out_path}")

    print(f"\nTotal: {total_dialogues} dialogues across "
          f"{total_templates} templates in {len(stg_files)} files")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
