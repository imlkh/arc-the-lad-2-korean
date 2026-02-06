#!/usr/bin/env python3
"""
Patch all translation files with a unified character mapping.

This ensures COMM.IMG contains ALL Korean characters needed across
all translation files (S100, SG00, system).
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch_korean import (
    load_decode_table, extract_korean_chars, build_korean_mapping,
    patch_comm_img, patch_stg_file, patch_exe_file,
    parse_translation_file, parse_system_translation_file,
    save_mapping, GAME_DIR, BASE_DIR, OUTPUT_DIR
)

import shutil


def main():
    print("=== Arc the Lad 2 Korean Patcher (Combined) ===")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load character table
    print("Loading character table...")
    decode_table = load_decode_table()
    print(f"  Loaded {len(decode_table)} characters")

    # Collect ALL translation files
    translation_files = []

    s100_path = os.path.join(BASE_DIR, "translated", "ko", "S100_STG.txt")
    sg00_path = os.path.join(BASE_DIR, "translated", "ko", "SG00_STG.txt")
    system_path = os.path.join(BASE_DIR, "translated", "ko", "SCPS_100_26_system.txt")

    if os.path.exists(s100_path):
        translation_files.append(("S100", s100_path))
    if os.path.exists(sg00_path):
        translation_files.append(("SG00", sg00_path))
    if os.path.exists(system_path):
        translation_files.append(("SYSTEM", system_path))

    if not translation_files:
        print("ERROR: No translation files found!")
        return 1

    # Extract ALL Korean characters from ALL files
    print("\nExtracting Korean characters from all translations...")
    all_korean_chars = set()
    char_frequency = {}

    for name, path in translation_files:
        chars = extract_korean_chars(path)
        all_korean_chars.update(chars)
        print(f"  {name}: {len(chars)} unique chars")

        # Count frequency
        with open(path, "r", encoding="utf-8") as f:
            for ch in f.read():
                if '\uAC00' <= ch <= '\uD7A3':
                    char_frequency[ch] = char_frequency.get(ch, 0) + 1

    print(f"  Total unique Korean characters: {len(all_korean_chars)}")
    print("  Using frequency-based encoding (most used chars get single-byte)")

    # Build unified mapping
    print("\nBuilding unified character mapping...")
    korean_mapping = build_korean_mapping(
        list(all_korean_chars), decode_table, char_frequency=char_frequency
    )
    print(f"  Mapped {len(korean_mapping)} Korean characters to font slots")

    # Patch COMM.IMG once with all characters
    comm_src = os.path.join(GAME_DIR, "COMM.IMG")
    comm_dst = os.path.join(OUTPUT_DIR, "COMM.IMG")

    print(f"\nCopying {comm_src} -> {comm_dst}")
    shutil.copy2(comm_src, comm_dst)

    print(f"Patching COMM.IMG: {comm_dst}")
    patch_comm_img(comm_dst, korean_mapping)
    print(f"  Patched {len(korean_mapping)} Korean glyphs into font")

    # Save unified mapping
    mapping_path = os.path.join(OUTPUT_DIR, "unified_charmap.txt")
    save_mapping(korean_mapping, mapping_path)

    # Patch each STG file
    for name, trans_path in translation_files:
        if name == "SYSTEM":
            continue  # Handle separately

        print(f"\n=== Stage: {name} ===")

        stg_src = os.path.join(GAME_DIR, f"{name}.STG")
        stg_dst = os.path.join(OUTPUT_DIR, f"{name}.STG")

        if not os.path.exists(stg_src):
            print(f"  ERROR: {stg_src} not found")
            continue

        print(f"Copying {stg_src} -> {stg_dst}")
        shutil.copy2(stg_src, stg_dst)

        print(f"Parsing translation file...")
        entries = parse_translation_file(trans_path)
        print(f"  Found {len(entries)} translation entries")

        print(f"Patching STG file: {stg_dst}")
        patch_stg_file(stg_dst, entries, korean_mapping, decode_table)

    # Patch system file
    if os.path.exists(system_path):
        print(f"\n=== System Messages ===")

        exe_src = os.path.join(GAME_DIR, "SCPS_100.26")
        exe_dst = os.path.join(OUTPUT_DIR, "SCPS_100.26")

        print(f"Copying {exe_src} -> {exe_dst}")
        shutil.copy2(exe_src, exe_dst)

        print(f"Parsing system translation file...")
        sys_entries = parse_system_translation_file(system_path)
        print(f"  Found {len(sys_entries)} system message entries")

        print(f"Patching EXE file: {exe_dst}")
        patch_exe_file(exe_dst, sys_entries, korean_mapping, decode_table)

    print(f"\n=== Done ===")
    print(f"Output directory: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
