#!/usr/bin/env python3
"""
Decode translatable Japanese text from all non-STG binary game files.

Extracts text from BEAM.DAT, Y*.BIN overlays, SDIC.BIN, SMITH.BIN,
SCPS_100.26 (main executable), and CHA.BIN using scan_file() with
a quality filter to reject false positives from MIPS machine code.

Usage:
    python decode_all_bin.py              # decode all binary files
    python decode_all_bin.py --find "エルク"  # filter by text pattern

Output: output/decoded/bin/<filename>.txt for each file.
"""

import argparse
import os
import sys

from decode_text import build_decode_table, scan_file, filter_real_text

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "..")  # Arc_The_Lad2/
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "decoded", "bin")

# Files to decode, in processing order.
# (filename, description, ff08_only)
# ff08_only=True for large files where byte-by-byte scan is too slow;
# uses only the fast FF 08 dialogue marker pass.
TARGET_FILES = [
    ("BEAM.DAT", "Battle/event dialogue", True),
    ("SDIC.BIN", "Dictionary — character profiles, monster descriptions", False),
    ("YGUILD.BIN", "Guild overlay — quest descriptions, job board text", False),
    ("YSHOP.BIN", "Shop overlay — shop/item text", False),
    ("YPROP.BIN", "Items overlay — item descriptions", False),
    ("YSEG.BIN", "Characters overlay — character text", False),
    ("YEND.BIN", "Credits overlay — ending/credits text", False),
    ("SMITH.BIN", "Equipment/smithing data", False),
    ("SCPS_100.26", "Main executable — system messages, menu text", False),
    ("CHA.BIN", "Character data — embedded text", True),
]


def safe_output_name(filename):
    """Convert a filename to a safe output basename (e.g. SCPS_100.26 -> SCPS_100_26)."""
    return filename.replace(".", "_")


def decode_one(filepath, decode_table, ff08_only=False, find=None):
    """Decode a single binary file. Returns (lines, count_raw, count_filtered)."""
    data = open(filepath, "rb").read()

    # Scan for text strings
    results = scan_file(data, decode_table, ff08_only=ff08_only)
    count_raw = len(results)

    # For ff08_only files, the FF 08 marker itself provides high confidence,
    # so no quality filter is needed.  For full-scan files, apply the kanji
    # filter (>= 2 kanji) to reject machine-code false positives.
    if ff08_only:
        count_filtered = count_raw
    else:
        results = filter_real_text(results)
        count_filtered = len(results)

    # Apply text search filter if specified
    if find:
        results = [(off, con, txt) for off, con, txt in results if find in txt]

    lines = []
    for offset, consumed, text in results:
        display = text.replace("\n", "\\n")
        lines.append(f"  0x{offset:08X} [{consumed:4d}] {display}")

    return lines, count_raw, count_filtered


def main():
    parser = argparse.ArgumentParser(
        description="Decode translatable text from non-STG binary game files."
    )
    parser.add_argument("--find", metavar="TEXT",
                        help="Only include strings containing this text")
    args = parser.parse_args()

    # Find which target files exist
    existing = []
    missing = []
    for filename, desc, ff08_only in TARGET_FILES:
        filepath = os.path.join(BIN_DIR, filename)
        if os.path.exists(filepath):
            existing.append((filename, desc, ff08_only, filepath))
        else:
            missing.append(filename)

    if not existing:
        print(f"No target binary files found in {BIN_DIR}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading character table...")
    decode_table = build_decode_table()
    print(f"  {len(decode_table)} characters loaded")
    print(f"Found {len(existing)} target files", end="")
    if missing:
        print(f" ({len(missing)} missing: {', '.join(missing)})")
    else:
        print()
    print()

    total_strings = 0

    for filename, desc, ff08_only, filepath in existing:
        filesize = os.path.getsize(filepath)
        size_label = f"{filesize / 1024:.0f} KB" if filesize < 1024 * 1024 else f"{filesize / (1024 * 1024):.1f} MB"
        mode = "FF08 markers" if ff08_only else "full scan"
        print(f"  {filename} ({size_label}, {mode}) — {desc}...", end="", flush=True)

        lines, count_raw, count_filtered = decode_one(filepath, decode_table,
                                                       ff08_only=ff08_only,
                                                       find=args.find)

        out_name = safe_output_name(filename) + ".txt"
        out_path = os.path.join(OUTPUT_DIR, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# {filename} — {count_filtered} strings "
                    f"({count_raw} raw, {count_raw - count_filtered} filtered out)\n\n")
            f.write("\n".join(lines))
            f.write("\n")

        total_strings += count_filtered
        print(f" {count_filtered} strings ({count_raw} raw) -> {out_name}")

    print(f"\nTotal: {total_strings} strings from {len(existing)} files")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
