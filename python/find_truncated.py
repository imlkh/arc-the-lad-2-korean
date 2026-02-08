#!/usr/bin/env python3
"""
Find dialogues that would be truncated using EXACT encoding.

Usage:
    python find_truncated.py S100
    python find_truncated.py S100 --output truncated.txt
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from patch_korean import (
    load_decode_table, extract_korean_chars, build_korean_mapping,
    encode_korean_text, parse_translation_file,
    BASE_DIR, GAME_DIR
)


def find_truncated_exact(stg_path, translation_entries, korean_mapping, decode_table):
    """Find dialogues that would be truncated using exact encoding."""
    with open(stg_path, "rb") as f:
        stg_data = f.read()

    truncated = []

    for entry in translation_entries:
        offset = entry["offset"]
        script_prefix = entry["script_prefix"]
        korean_text = entry["text"]

        if offset >= len(stg_data):
            continue

        # Find original text length (from end of script prefix to null)
        orig_start = offset + len(script_prefix)
        orig_end = orig_start
        while orig_end < len(stg_data) and stg_data[orig_end] != 0x00:
            orig_end += 1

        orig_text_len = orig_end - orig_start

        # Encode Korean text with exact mapping
        encoded = encode_korean_text(korean_text, korean_mapping, decode_table)
        korean_len = len(encoded)

        if korean_len > orig_text_len:
            over_by = korean_len - orig_text_len
            truncated.append({
                "offset": offset,
                "opcode": entry["opcode"],
                "script_prefix": script_prefix.hex(" "),
                "text": korean_text,
                "orig_len": orig_text_len,
                "korean_len": korean_len,
                "over_by": over_by
            })

    return truncated


def main():
    parser = argparse.ArgumentParser(description="Find truncated dialogues (exact encoding)")
    parser.add_argument("stage", help="Stage name (e.g., S100, SG00)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--all-translations", action="store_true",
                        help="Use unified mapping from all translation files")
    args = parser.parse_args()

    stage = args.stage.upper()
    translation_path = os.path.join(BASE_DIR, "translated", "ko", f"{stage}_STG.txt")
    stg_path = os.path.join(GAME_DIR, f"{stage}.STG")

    if not os.path.exists(translation_path):
        print(f"ERROR: Translation file not found: {translation_path}")
        return 1

    if not os.path.exists(stg_path):
        print(f"ERROR: STG file not found: {stg_path}")
        return 1

    print(f"Analyzing {stage} with exact encoding...")
    print()

    # Load resources
    decode_table = load_decode_table()

    # Collect Korean characters
    all_korean_chars = set()
    char_frequency = {}

    if args.all_translations:
        # Use all translation files for unified mapping
        for fname in ["S100_STG.txt", "SG00_STG.txt", "SCPS_100_26_system.txt"]:
            fpath = os.path.join(BASE_DIR, "translated", "ko", fname)
            if os.path.exists(fpath):
                chars = extract_korean_chars(fpath)
                all_korean_chars.update(chars)
                with open(fpath, "r", encoding="utf-8") as f:
                    for ch in f.read():
                        if '\uAC00' <= ch <= '\uD7A3':
                            char_frequency[ch] = char_frequency.get(ch, 0) + 1
    else:
        # Use only this translation file
        chars = extract_korean_chars(translation_path)
        all_korean_chars.update(chars)
        with open(translation_path, "r", encoding="utf-8") as f:
            for ch in f.read():
                if '\uAC00' <= ch <= '\uD7A3':
                    char_frequency[ch] = char_frequency.get(ch, 0) + 1

    korean_mapping = build_korean_mapping(
        list(all_korean_chars), decode_table, char_frequency=char_frequency
    )
    print(f"Character mapping: {len(korean_mapping)} Korean chars")

    # Parse translation file
    entries = parse_translation_file(translation_path)
    print(f"Total translations: {len(entries)}")

    # Find truncated
    truncated = find_truncated_exact(stg_path, entries, korean_mapping, decode_table)

    print(f"Would be truncated: {len(truncated)} ({100*len(truncated)/len(entries):.1f}%)")
    print()

    if not truncated:
        print("All translations fit!")
        return 0

    # Sort by how much over
    truncated.sort(key=lambda x: -x["over_by"])

    output_lines = []
    output_lines.append(f"# Truncated dialogues for {stage}")
    output_lines.append(f"# Total: {len(truncated)} dialogues need shortening")
    output_lines.append(f"#")
    output_lines.append(f"# To fix: Shorten the Korean text to remove 'over_by' bytes")
    output_lines.append(f"# Each Korean char = 1-2 bytes, control codes = 4 bytes")
    output_lines.append("")

    for item in truncated:
        output_lines.append(f"# Over by {item['over_by']} bytes (orig: {item['orig_len']}, korean: {item['korean_len']})")
        output_lines.append(f"  0x{item['offset']:08X} [0x{item['opcode']:04X}] [script:{item['script_prefix']}]{item['text']}")
        output_lines.append("")

    output_text = "\n".join(output_lines)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"Saved to: {args.output}")
    else:
        # Print top entries to console
        print("Most over-length dialogues (need shortening):")
        print("-" * 70)
        for item in truncated[:15]:
            print(f"+{item['over_by']:2d} bytes: {item['text'][:55]}...")
        if len(truncated) > 15:
            print(f"... and {len(truncated) - 15} more")
        print()
        print("Run with --output <file> to save full list.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
