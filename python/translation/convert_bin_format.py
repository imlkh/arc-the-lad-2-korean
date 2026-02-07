#!/usr/bin/env python3
"""
Convert non-STG translation files from CSV format to proper decoded format.

Input (wrong):  0x000D2708,엘리멘탈
Output (correct):  0x000D2708 [   7] 엘리멘탈

Usage:
    python convert_bin_format.py SDIC_BIN
    python convert_bin_format.py YGUILD_BIN
    python convert_bin_format.py SMITH_BIN
    python convert_bin_format.py SCPS_100_26
    python convert_bin_format.py --all
"""

import argparse
import re
import sys
from pathlib import Path

# Map of translation file names to decoded file names
FILE_MAPPING = {
    "SCPS_100_26": ("SCPS_100_26.txt", "SCPS_100.26"),
    "SDIC_BIN": ("SDIC_BIN.txt", "SDIC.BIN"),
    "YGUILD_BIN": ("YGUILD_BIN.txt", "YGUILD.BIN"),
    "SMITH_BIN": ("SMITH_BIN.txt", "SMITH.BIN"),
    "BEAM_DAT": ("BEAM_DAT.txt", "BEAM.DAT"),
}


def parse_decoded_file(decoded_path: Path) -> dict:
    """Parse decoded file to get offset -> (length, text) mapping."""
    entries = {}
    pattern = re.compile(r'^\s+0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.*)$')

    with open(decoded_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.match(line)
            if match:
                offset = f"0x{match.group(1).upper()}"
                length = int(match.group(2))
                text = match.group(3)
                entries[offset] = (length, text)

    return entries


def parse_translation_file(trans_path: Path) -> dict:
    """Parse translation file to get offset -> korean_text mapping.

    Supports both CSV format and already-converted format.
    """
    translations = {}

    with open(trans_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_stripped = line.strip()
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue

            # Check if already in new format: 0xOFFSET [LENGTH] text
            match = re.match(r'^\s*0x([0-9A-Fa-f]+)\s+\[\s*\d+\]\s+(.+)$', line)
            if match:
                offset = f"0x{match.group(1).upper()}"
                text = match.group(2)
                translations[offset] = text
                continue

            # Parse CSV format: offset,text
            if ',' in line_stripped:
                parts = line_stripped.split(',', 1)
                if len(parts) == 2:
                    offset = parts[0].strip().upper()
                    if not offset.startswith('0X'):
                        offset = f"0x{offset}"
                    else:
                        offset = f"0x{offset[2:]}"
                    text = parts[1].strip()
                    translations[offset] = text

    return translations


def convert_file(file_key: str, base_dir: Path) -> bool:
    """Convert a single translation file to the new format."""
    if file_key not in FILE_MAPPING:
        print(f"ERROR: Unknown file key: {file_key}")
        print(f"Available: {', '.join(FILE_MAPPING.keys())}")
        return False

    filename, display_name = FILE_MAPPING[file_key]
    decoded_path = base_dir / "output/decoded/bin" / filename
    trans_path = base_dir / "translated/ko" / filename

    if not decoded_path.exists():
        print(f"SKIP: Decoded file not found: {decoded_path}")
        return False

    if not trans_path.exists():
        print(f"SKIP: Translation file not found: {trans_path}")
        return False

    print(f"\n=== Converting {file_key} ===")
    print(f"Reading decoded file: {decoded_path}")
    decoded = parse_decoded_file(decoded_path)
    print(f"  Found {len(decoded)} entries")

    print(f"Reading translation file: {trans_path}")
    translations = parse_translation_file(trans_path)
    print(f"  Found {len(translations)} translations")

    # Build output
    output_lines = []
    output_lines.append(f"# {display_name} — {len(decoded)} strings (Korean translations)")
    output_lines.append("")

    # Merge: for each decoded entry, use Korean if available, else Japanese
    translated_count = 0
    for offset, (length, jp_text) in sorted(decoded.items(), key=lambda x: int(x[0], 16)):
        if offset in translations:
            text = translations[offset]
            translated_count += 1
        else:
            text = jp_text

        # Format: 2 spaces + offset + space + [length right-justified to 4] + space + text
        output_lines.append(f"  {offset} [{length:4d}] {text}")

    print(f"Writing output: {trans_path}")
    print(f"  {translated_count}/{len(decoded)} entries translated")

    with open(trans_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines) + '\n')

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert non-STG translation files from CSV to decoded format"
    )
    parser.add_argument(
        "files", nargs="*",
        help="File keys to convert (e.g., SDIC_BIN, YGUILD_BIN)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Convert all available files"
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent.parent

    if args.all:
        files_to_convert = list(FILE_MAPPING.keys())
    elif args.files:
        files_to_convert = args.files
    else:
        print("Usage: python convert_bin_format.py [FILE_KEY...] [--all]")
        print(f"Available files: {', '.join(FILE_MAPPING.keys())}")
        return 1

    success_count = 0
    for file_key in files_to_convert:
        if convert_file(file_key, base_dir):
            success_count += 1

    print(f"\n=== Done ===")
    print(f"Converted {success_count}/{len(files_to_convert)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
