#!/usr/bin/env python3
"""Find BEAM.DAT dialogue entries that are decoded but missing from the translation file.

Compares the decoded output (output/decoded/bin/BEAM_DAT.txt) against the
translation file (translated/ko/BEAM_DAT.txt) and reports entries that
exist in the decoded binary but have no corresponding translation entry.

Usage:
    python find_missing_beam.py              # show all missing entries
    python find_missing_beam.py --regen      # re-decode BEAM.DAT first, then compare
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))

DECODED_PATH = os.path.join(PROJECT_DIR, "output", "decoded", "bin", "BEAM_DAT.txt")
TRANSLATED_PATH = os.path.join(PROJECT_DIR, "translated", "ko", "BEAM_DAT.txt")

# Regex to match entry lines: "  0xOFFSET [SIZE] text"
LINE_RE = re.compile(r'^\s+0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$')


def parse_entries(filepath):
    """Parse a decoded/translated file and return dict of offset -> (size, text)."""
    entries = {}
    if not os.path.exists(filepath):
        return entries
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            m = LINE_RE.match(line.rstrip())
            if m:
                offset = int(m.group(1), 16)
                size = int(m.group(2))
                text = m.group(3)
                entries[offset] = (size, text)
    return entries


def is_japanese_text(text):
    """Check if text contains Japanese characters (hiragana, katakana, kanji).

    This helps identify entries that still need translation vs entries that
    are pure control codes or already translated.
    """
    for ch in text:
        cp = ord(ch)
        # Hiragana: U+3040-U+309F, Katakana: U+30A0-U+30FF
        # CJK Unified Ideographs: U+4E00-U+9FFF
        if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF or 0x4E00 <= cp <= 0x9FFF:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Find BEAM.DAT entries missing from the translation file."
    )
    parser.add_argument("--regen", action="store_true",
                        help="Re-run decode_all_bin.py to regenerate decoded output first")
    parser.add_argument("--show-translated", action="store_true",
                        help="Also show entries that ARE translated (for full coverage view)")
    args = parser.parse_args()

    if args.regen:
        print("Re-decoding BEAM.DAT...")
        import subprocess
        decode_script = os.path.join(SCRIPT_DIR, "decode_all_bin.py")
        subprocess.run([sys.executable, decode_script], check=True)
        print()

    if not os.path.exists(DECODED_PATH):
        print(f"Error: Decoded file not found: {DECODED_PATH}", file=sys.stderr)
        print("Run 'python decode_all_bin.py' first to generate it.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(TRANSLATED_PATH):
        print(f"Error: Translation file not found: {TRANSLATED_PATH}", file=sys.stderr)
        sys.exit(1)

    decoded = parse_entries(DECODED_PATH)
    translated = parse_entries(TRANSLATED_PATH)

    print(f"Decoded entries:    {len(decoded)}")
    print(f"Translated entries: {len(translated)}")

    # Find entries in decoded that are missing from translated
    missing = {}
    for offset, (size, text) in sorted(decoded.items()):
        if offset not in translated:
            missing[offset] = (size, text)

    # Find entries in translated that are NOT in decoded (extra translations)
    extra = {}
    for offset, (size, text) in sorted(translated.items()):
        if offset not in decoded:
            extra[offset] = (size, text)

    # Categorize missing entries
    missing_japanese = {}  # Contains Japanese text - needs translation
    missing_garbled = {}   # Contains garbled kanji (from overlay) - needs translation
    missing_other = {}     # Control codes, numbers, etc.

    for offset, (size, text) in missing.items():
        # Strip control codes for analysis
        clean = re.sub(r'\[.*?\]', '', text).replace('\\n', '')
        if is_japanese_text(text):
            missing_japanese[offset] = (size, text)
        elif clean.strip():
            # Has visible characters but no recognized Japanese
            # Could be garbled overlay kanji
            missing_garbled[offset] = (size, text)
        else:
            missing_other[offset] = (size, text)

    print(f"\n=== Missing from translation file: {len(missing)} entries ===")
    print(f"  Japanese text (needs translation): {len(missing_japanese)}")
    print(f"  Garbled/other text:                {len(missing_garbled)}")
    print(f"  Control codes only:                {len(missing_other)}")

    if missing_japanese:
        print(f"\n--- Japanese text entries ({len(missing_japanese)}) ---")
        for offset, (size, text) in sorted(missing_japanese.items()):
            print(f"  0x{offset:08X} [{size:4d}] {text}")

    if missing_garbled:
        print(f"\n--- Garbled/other text entries ({len(missing_garbled)}) ---")
        for offset, (size, text) in sorted(missing_garbled.items()):
            print(f"  0x{offset:08X} [{size:4d}] {text}")

    if missing_other:
        print(f"\n--- Control-code-only entries ({len(missing_other)}) ---")
        for offset, (size, text) in sorted(missing_other.items()):
            print(f"  0x{offset:08X} [{size:4d}] {text}")

    if extra:
        print(f"\n=== Extra translations (not in decoded output): {len(extra)} ===")
        for offset, (size, text) in sorted(extra.items()):
            print(f"  0x{offset:08X} [{size:4d}] {text}")

    if args.show_translated:
        matched = {off for off in decoded if off in translated}
        print(f"\n=== Translated entries: {len(matched)} ===")
        for offset in sorted(matched):
            d_size, d_text = decoded[offset]
            t_size, t_text = translated[offset]
            print(f"  0x{offset:08X} [{d_size:4d}] {d_text}")
            print(f"            -> [{t_size:4d}] {t_text}")

    # Summary
    total_decoded = len(decoded)
    total_translated_matching = len([o for o in decoded if o in translated])
    coverage = total_translated_matching / total_decoded * 100 if total_decoded else 0
    print(f"\n=== Coverage Summary ===")
    print(f"  Total decoded:     {total_decoded}")
    print(f"  Translated:        {total_translated_matching} ({coverage:.1f}%)")
    print(f"  Missing:           {len(missing)} ({100 - coverage:.1f}%)")
    if extra:
        print(f"  Extra (not decoded): {len(extra)}")


if __name__ == '__main__':
    main()
