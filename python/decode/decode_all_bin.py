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

from decode_text import (build_decode_table, scan_file, filter_real_text,
                         scan_executable, scan_text_regions,
                         SCPS_TEXT_REGIONS, BEAM_TEXT_REGIONS)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "..")  # Arc_The_Lad2/
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "decoded", "bin")

# Files to decode, in processing order.
# (filename, description, ff08_only, scan_mode)
# ff08_only=True for large files where byte-by-byte scan is too slow;
# uses only the fast FF 08 dialogue marker pass.
# scan_mode: "normal" (default), "strict" (sentence endings required),
#            "region" (region-aware for executables with known text regions),
#            "beam" (FF08 markers + character/monster name regions for BEAM.DAT)
#
# NOTE: YEND.BIN is excluded because it uses ASCII encoding (not game encoding).
# Use decode_yend.py to extract YEND.BIN credit strings.
TARGET_FILES = [
    ("BEAM.DAT", "Battle/event dialogue + character names", False, "beam"),
    ("SDIC.BIN", "Dictionary — character profiles, monster descriptions", False, "normal"),
    ("YGUILD.BIN", "Guild overlay — quest descriptions, job board text", False, "normal"),
    ("YSHOP.BIN", "Shop overlay — shop/item text", False, "normal"),
    ("YPROP.BIN", "Items overlay — item descriptions", False, "normal"),
    ("YSEG.BIN", "Characters overlay — character text", False, "normal"),
    ("SMITH.BIN", "Equipment/smithing data", False, "normal"),
    ("SCPS_100.26", "Main executable — system messages, menu text", False, "region"),
    ("CHA.BIN", "Character data — embedded text", True, "normal"),
]


def safe_output_name(filename):
    """Convert a filename to a safe output basename (e.g. SCPS_100.26 -> SCPS_100_26)."""
    return filename.replace(".", "_")


def decode_one(filepath, decode_table, ff08_only=False, scan_mode="normal", find=None):
    """Decode a single binary file. Returns (lines, count_raw, count_filtered, menu_count)."""
    data = open(filepath, "rb").read()

    # Scan for text strings based on mode
    if scan_mode == "region":
        # Region-aware scanning for executables with known text regions
        # This captures all strings in text regions without strict filtering
        results = scan_executable(data, decode_table, SCPS_TEXT_REGIONS)
        count_raw = len(results)
        count_filtered = count_raw  # Already filtered during scan
    elif scan_mode == "beam":
        # BEAM.DAT: combine FF08 marker scanning with character/monster name regions
        # FF08 scanning catches dialogues, region scanning catches name tables
        ff08_results = scan_file(data, decode_table, ff08_only=True)
        region_results = scan_text_regions(data, decode_table, BEAM_TEXT_REGIONS)
        # Merge results, avoiding duplicates by offset
        seen_offsets = {r[0] for r in ff08_results}
        results = list(ff08_results)
        for r in region_results:
            if r[0] not in seen_offsets:
                results.append(r)
        results.sort(key=lambda r: r[0])
        count_raw = len(results)
        count_filtered = count_raw
    elif ff08_only:
        # FF 08 marker-based scan (fast, high confidence)
        results = scan_file(data, decode_table, ff08_only=True)
        count_raw = len(results)
        count_filtered = count_raw
    else:
        # Full scan with optional filtering
        results = scan_file(data, decode_table, ff08_only=False)
        count_raw = len(results)
        if scan_mode == "strict":
            results = filter_real_text(results, strict=True)
        else:
            results = filter_real_text(results, strict=False)
        count_filtered = len(results)

    # Apply text search filter if specified
    if find:
        results = [(off, con, txt) for off, con, txt in results if find in txt]

    # Count menu options ([opt] tags)
    menu_count = sum(1 for _, _, txt in results if '[opt]' in txt)

    lines = []
    for offset, consumed, text in results:
        display = text.replace("\n", "\\n")
        lines.append(f"  0x{offset:08X} [{consumed:4d}] {display}")

    return lines, count_raw, count_filtered, menu_count


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
    for filename, desc, ff08_only, scan_mode in TARGET_FILES:
        filepath = os.path.join(BIN_DIR, filename)
        if os.path.exists(filepath):
            existing.append((filename, desc, ff08_only, scan_mode, filepath))
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
    total_menus = 0

    for filename, desc, ff08_only, scan_mode, filepath in existing:
        filesize = os.path.getsize(filepath)
        size_label = f"{filesize / 1024:.0f} KB" if filesize < 1024 * 1024 else f"{filesize / (1024 * 1024):.1f} MB"
        mode_label = {"normal": "full scan", "strict": "strict scan",
                      "region": "region scan", "beam": "FF08 + regions"}.get(scan_mode, scan_mode)
        if ff08_only:
            mode_label = "FF08 markers"
        print(f"  {filename} ({size_label}, {mode_label}) — {desc}...", end="", flush=True)

        lines, count_raw, count_filtered, menu_count = decode_one(filepath, decode_table,
                                                                   ff08_only=ff08_only,
                                                                   scan_mode=scan_mode,
                                                                   find=args.find)

        out_name = safe_output_name(filename) + ".txt"
        out_path = os.path.join(OUTPUT_DIR, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# {filename} — {count_filtered} strings, {menu_count} menu options "
                    f"({count_raw} raw, {count_raw - count_filtered} filtered out)\n\n")
            f.write("\n".join(lines))
            f.write("\n")

        total_strings += count_filtered
        total_menus += menu_count
        menu_label = f", {menu_count} menus" if menu_count > 0 else ""
        print(f" {count_filtered} strings{menu_label} ({count_raw} raw) -> {out_name}")

    print(f"\nTotal: {total_strings} strings, {total_menus} menu options from {len(existing)} files")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
