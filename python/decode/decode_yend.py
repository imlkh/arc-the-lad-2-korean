#!/usr/bin/env python3
"""
Decode ASCII credit strings from YEND.BIN (ending credits module).

YEND.BIN uses plain ASCII encoding (not the game's custom text encoding).
Credit strings are stored at file offset 0x0000-0x0B23 as null-terminated,
4-byte aligned ASCII strings.

Usage:
    python decode_yend.py                  # decode all credit strings
    python decode_yend.py --find "Producer"  # filter by text pattern

Output: output/decoded/bin/YEND_BIN.txt
"""

import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YEND_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "..", "YEND.BIN")
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "decoded", "bin")

# Credit string region in YEND.BIN
STRING_REGION_START = 0x0000
STRING_REGION_END = 0x0B24  # 2,852 bytes


def extract_ascii_strings(data, start, end):
    """Extract null-terminated ASCII strings from a byte region.

    Returns list of (offset, string) tuples.
    """
    strings = []
    pos = start

    while pos < end:
        # Find start of string (skip null padding)
        while pos < end and data[pos] == 0x00:
            pos += 1

        if pos >= end:
            break

        string_start = pos

        # Read until null terminator
        chars = []
        while pos < end and data[pos] != 0x00:
            byte = data[pos]
            # Valid printable ASCII range (0x20-0x7E)
            if 0x20 <= byte <= 0x7E:
                chars.append(chr(byte))
            else:
                chars.append(f"[{byte:02X}]")
            pos += 1

        if chars:
            strings.append((string_start, "".join(chars)))

        pos += 1  # Skip the null terminator

    return strings


def categorize_string(text):
    """Categorize a credit string by its content."""
    if text.endswith(":"):
        return "header"
    elif text.startswith(" ") and "(" in text:
        return "staff"
    elif text in ("ELC", "LIEZA", "SHU", "SHANTE", "DIECBECK", "GRUGA",
                  "SANIA", "ARC", "KUKURU", "POCO", "TOSH", "IGA",
                  "GOGEN", "CHONGARA"):
        return "character"
    elif "Song" in text or "Musicman" in text:
        return "song"
    else:
        return "name"


def main():
    parser = argparse.ArgumentParser(
        description="Decode ASCII credit strings from YEND.BIN."
    )
    parser.add_argument("--find", metavar="TEXT",
                        help="Only include strings containing this text")
    parser.add_argument("--file", metavar="PATH",
                        help="Path to YEND.BIN (default: auto-detect)")
    args = parser.parse_args()

    # Resolve file path
    yend_path = args.file if args.file else YEND_PATH
    if not os.path.exists(yend_path):
        print(f"Error: YEND.BIN not found at {yend_path}", file=sys.stderr)
        sys.exit(1)

    # Read file
    data = open(yend_path, "rb").read()
    print(f"Reading {yend_path} ({len(data):,} bytes)")

    # Extract strings from credit region
    strings = extract_ascii_strings(data, STRING_REGION_START, STRING_REGION_END)
    print(f"Found {len(strings)} ASCII credit strings\n")

    # Apply filter if specified
    if args.find:
        strings = [(off, txt) for off, txt in strings if args.find.lower() in txt.lower()]
        print(f"Filtered to {len(strings)} strings containing \"{args.find}\"\n")

    # Categorize and display
    categories = {"header": [], "staff": [], "character": [], "song": [], "name": []}

    for offset, text in strings:
        cat = categorize_string(text)
        categories[cat].append((offset, text))

    # Output to console
    print("=" * 60)
    print("CREDIT STRINGS BY CATEGORY")
    print("=" * 60)

    for cat_name, cat_label in [("header", "Section Headers"),
                                 ("character", "Character Names (Voice Cast)"),
                                 ("song", "Song Credits"),
                                 ("staff", "Staff Names"),
                                 ("name", "Other Names")]:
        cat_strings = categories[cat_name]
        if cat_strings:
            print(f"\n### {cat_label} ({len(cat_strings)})")
            for offset, text in cat_strings:
                print(f"  0x{offset:04X}: {text}")

    # Write to output file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "YEND_BIN.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# YEND.BIN — {len(strings)} ASCII credit strings\n")
        f.write(f"# Encoding: Plain ASCII (not game custom encoding)\n")
        f.write(f"# String region: 0x{STRING_REGION_START:04X}-0x{STRING_REGION_END:04X}\n\n")

        f.write("## All Strings (by file offset)\n\n")
        for offset, text in strings:
            f.write(f"0x{offset:04X}: {text}\n")

        f.write("\n\n## Strings by Category\n")

        for cat_name, cat_label in [("header", "Section Headers"),
                                     ("character", "Character Names"),
                                     ("song", "Song Credits"),
                                     ("staff", "Staff Names"),
                                     ("name", "Other Names")]:
            cat_strings = categories[cat_name]
            if cat_strings:
                f.write(f"\n### {cat_label}\n")
                for offset, text in cat_strings:
                    f.write(f"0x{offset:04X}: {text}\n")

    print(f"\n\nOutput written to: {out_path}")

    # Summary
    print(f"\nSummary:")
    print(f"  Section headers: {len(categories['header'])}")
    print(f"  Character names: {len(categories['character'])}")
    print(f"  Song credits:    {len(categories['song'])}")
    print(f"  Staff names:     {len(categories['staff'])}")
    print(f"  Other names:     {len(categories['name'])}")
    print(f"  Total:           {len(strings)}")


if __name__ == "__main__":
    main()
