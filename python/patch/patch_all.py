#!/usr/bin/env python3
"""
Patch all translation files with a unified character mapping.

This ensures COMM.IMG contains ALL Korean characters needed across
all translation files (S100, SG00, system, SDIC, YGUILD).

Supported files:
- S*.STG: Stage dialogue files
- SCPS_100.26: Main executable (system messages)
- SDIC.BIN: Monster/character descriptions
- YGUILD.BIN: Guild quest descriptions
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch_korean import (
    load_decode_table, extract_korean_chars, build_korean_mapping,
    patch_comm_img, patch_stg_file, patch_exe_file, patch_bin_file,
    parse_translation_file, parse_bin_translation_file, validate_translation_lengths,
    save_mapping, GAME_DIR, BASE_DIR, OUTPUT_DIR
)

import shutil


def save_validation_report(all_warnings, report_path):
    """Save detailed validation report to file.

    Args:
        all_warnings: dict mapping filename -> list of warning dicts
        report_path: path to save report
    """
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        total_warnings = sum(len(w) for w in all_warnings.values())
        f.write(f"## Summary\n\n")
        f.write(f"Total truncation warnings: {total_warnings}\n\n")

        for filename, warnings in all_warnings.items():
            if not warnings:
                continue
            f.write(f"## {filename} ({len(warnings)} truncations)\n\n")
            f.write("| Offset | Original | Korean | Overflow | Text |\n")
            f.write("|--------|----------|--------|----------|------|\n")
            for w in warnings:
                # Escape pipe characters in text
                text = w.get('text', '')[:40].replace('|', '\\|')
                f.write(f"| 0x{w['offset']:08X} | {w['orig_length']} | {w['new_length']} | +{w['overflow']} | {text} |\n")
            f.write("\n")

    return total_warnings


def main():
    print("=== Arc the Lad 2 Korean Patcher (Combined) ===")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Collect all validation warnings for report
    all_validation_warnings = {}

    # Load character table
    print("Loading character table...")
    decode_table = load_decode_table()
    print(f"  Loaded {len(decode_table)} characters")

    # Collect ALL translation files
    translation_files = []

    # Read from output/patched/translation/ (copied by patch_workflow.py)
    trans_dir = os.path.join(BASE_DIR, "output", "patched", "translation")
    system_path = os.path.join(trans_dir, "SCPS_100_26.txt")
    sdic_path = os.path.join(trans_dir, "SDIC_BIN.txt")
    yguild_path = os.path.join(trans_dir, "YGUILD_BIN.txt")
    smith_path = os.path.join(trans_dir, "SMITH_BIN.txt")
    beam_path = os.path.join(trans_dir, "BEAM_DAT.txt")

    # Include all staged STG translation files (S100, SG00, S200, ...)
    for filename in sorted(os.listdir(trans_dir)):
        if not filename.endswith("_STG.txt"):
            continue
        stage_name = filename[:-8].upper()  # Remove "_STG.txt"
        stage_path = os.path.join(trans_dir, filename)
        translation_files.append((stage_name, stage_path))
    if os.path.exists(system_path):
        translation_files.append(("SYSTEM", system_path))
    if os.path.exists(sdic_path):
        translation_files.append(("SDIC", sdic_path))
    if os.path.exists(yguild_path):
        translation_files.append(("YGUILD", yguild_path))
    if os.path.exists(smith_path):
        translation_files.append(("SMITH", smith_path))
    if os.path.exists(beam_path):
        translation_files.append(("BEAM", beam_path))

    if not translation_files:
        print("ERROR: No translation files found!")
        return 1

    # Extract ALL Korean characters from ALL files
    # Separate frequency counting: non-STG files use fixed-length replacement
    # (single-byte encoding prevents truncation), STG files use variable-length
    print("\nExtracting Korean characters from all translations...")
    all_korean_chars = set()
    non_stg_frequency = {}  # SCPS, SDIC, YGUILD, SMITH, BEAM
    stg_frequency = {}      # S*_STG files

    NON_STG_NAMES = {"SYSTEM", "SDIC", "YGUILD", "SMITH", "BEAM"}

    for name, path in translation_files:
        chars = extract_korean_chars(path)
        all_korean_chars.update(chars)
        print(f"  {name}: {len(chars)} unique chars")

        # Count frequency into the appropriate dict
        freq_dict = non_stg_frequency if name in NON_STG_NAMES else stg_frequency
        with open(path, "r", encoding="utf-8") as f:
            for ch in f.read():
                if '\uAC00' <= ch <= '\uD7A3':
                    freq_dict[ch] = freq_dict.get(ch, 0) + 1

    print(f"  Total unique Korean characters: {len(all_korean_chars)}")
    non_stg_char_count = len([c for c in all_korean_chars if c in non_stg_frequency])
    print(f"  Non-STG characters: {non_stg_char_count} (prioritized for single-byte slots)")
    print(f"  STG-only characters: {len(all_korean_chars) - non_stg_char_count}")

    # Build unified mapping
    print("\nBuilding unified character mapping...")
    korean_mapping = build_korean_mapping(
        list(all_korean_chars), decode_table,
        non_stg_frequency=non_stg_frequency, stg_frequency=stg_frequency
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
        if name in ("SYSTEM", "SDIC", "YGUILD", "SMITH", "BEAM"):
            continue  # Handle separately (non-STG files)

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
        sys_entries = parse_bin_translation_file(system_path)  # New format with length field
        print(f"  Found {len(sys_entries)} system message entries")

        # Validate translation lengths
        valid_count, warn_count, warnings = validate_translation_lengths(
            sys_entries, korean_mapping, decode_table, "SCPS_100.26"
        )
        all_validation_warnings["SCPS_100.26"] = warnings
        print(f"  Validation: {valid_count} OK, {warn_count} will be truncated")
        if warn_count > 0:
            for w in warnings[:5]:  # Show first 5 warnings
                print(f"    0x{w['offset']:08X}: {w['orig_length']} -> {w['new_length']} (+{w['overflow']} bytes)")
            if warn_count > 5:
                print(f"    ... and {warn_count - 5} more")

        print(f"Patching EXE file: {exe_dst}")
        patch_exe_file(exe_dst, sys_entries, korean_mapping, decode_table)

    # Patch SDIC.BIN file
    if os.path.exists(sdic_path):
        print(f"\n=== SDIC.BIN (Monster/Character Descriptions) ===")

        sdic_src = os.path.join(GAME_DIR, "SDIC.BIN")
        sdic_dst = os.path.join(OUTPUT_DIR, "SDIC.BIN")

        print(f"Copying {sdic_src} -> {sdic_dst}")
        shutil.copy2(sdic_src, sdic_dst)

        print(f"Parsing SDIC translation file...")
        sdic_entries = parse_bin_translation_file(sdic_path)  # Supports both formats
        print(f"  Found {len(sdic_entries)} SDIC entries")

        # Validate translation lengths
        valid_count, warn_count, warnings = validate_translation_lengths(
            sdic_entries, korean_mapping, decode_table, "SDIC.BIN"
        )
        all_validation_warnings["SDIC.BIN"] = warnings
        print(f"  Validation: {valid_count} OK, {warn_count} will be truncated")
        if warn_count > 0:
            for w in warnings[:5]:
                print(f"    0x{w['offset']:08X}: {w['orig_length']} -> {w['new_length']} (+{w['overflow']} bytes)")
            if warn_count > 5:
                print(f"    ... and {warn_count - 5} more")

        print(f"Patching BIN file: {sdic_dst}")
        patch_bin_file(sdic_dst, sdic_entries, korean_mapping, decode_table)

    # Patch YGUILD.BIN file
    if os.path.exists(yguild_path):
        print(f"\n=== YGUILD.BIN (Guild Quest Descriptions) ===")

        yguild_src = os.path.join(GAME_DIR, "YGUILD.BIN")
        yguild_dst = os.path.join(OUTPUT_DIR, "YGUILD.BIN")

        print(f"Copying {yguild_src} -> {yguild_dst}")
        shutil.copy2(yguild_src, yguild_dst)

        print(f"Parsing YGUILD translation file...")
        yguild_entries = parse_bin_translation_file(yguild_path)  # Supports both formats
        print(f"  Found {len(yguild_entries)} YGUILD entries")

        # Validate translation lengths
        valid_count, warn_count, warnings = validate_translation_lengths(
            yguild_entries, korean_mapping, decode_table, "YGUILD.BIN"
        )
        all_validation_warnings["YGUILD.BIN"] = warnings
        print(f"  Validation: {valid_count} OK, {warn_count} will be truncated")
        if warn_count > 0:
            for w in warnings[:5]:
                print(f"    0x{w['offset']:08X}: {w['orig_length']} -> {w['new_length']} (+{w['overflow']} bytes)")
            if warn_count > 5:
                print(f"    ... and {warn_count - 5} more")

        print(f"Patching BIN file: {yguild_dst}")
        patch_bin_file(yguild_dst, yguild_entries, korean_mapping, decode_table)

    # Patch SMITH.BIN file
    if os.path.exists(smith_path):
        print(f"\n=== SMITH.BIN (Equipment Descriptions) ===")

        smith_src = os.path.join(GAME_DIR, "SMITH.BIN")
        smith_dst = os.path.join(OUTPUT_DIR, "SMITH.BIN")

        print(f"Copying {smith_src} -> {smith_dst}")
        shutil.copy2(smith_src, smith_dst)

        print(f"Parsing SMITH translation file...")
        smith_entries = parse_bin_translation_file(smith_path)  # Supports both formats
        print(f"  Found {len(smith_entries)} SMITH entries")

        # Validate translation lengths
        valid_count, warn_count, warnings = validate_translation_lengths(
            smith_entries, korean_mapping, decode_table, "SMITH.BIN"
        )
        all_validation_warnings["SMITH.BIN"] = warnings
        print(f"  Validation: {valid_count} OK, {warn_count} will be truncated")
        if warn_count > 0:
            for w in warnings[:5]:
                print(f"    0x{w['offset']:08X}: {w['orig_length']} -> {w['new_length']} (+{w['overflow']} bytes)")
            if warn_count > 5:
                print(f"    ... and {warn_count - 5} more")

        print(f"Patching BIN file: {smith_dst}")
        patch_bin_file(smith_dst, smith_entries, korean_mapping, decode_table)

    # Patch BEAM.DAT file
    if os.path.exists(beam_path):
        print(f"\n=== BEAM.DAT (Battle/Event Dialogues) ===")

        beam_src = os.path.join(GAME_DIR, "BEAM.DAT")
        beam_dst = os.path.join(OUTPUT_DIR, "BEAM.DAT")

        print(f"Copying {beam_src} -> {beam_dst}")
        shutil.copy2(beam_src, beam_dst)

        print(f"Parsing BEAM translation file...")
        beam_entries = parse_bin_translation_file(beam_path)  # Supports both formats
        print(f"  Found {len(beam_entries)} BEAM entries")

        # Validate translation lengths
        valid_count, warn_count, warnings = validate_translation_lengths(
            beam_entries, korean_mapping, decode_table, "BEAM.DAT"
        )
        all_validation_warnings["BEAM.DAT"] = warnings
        print(f"  Validation: {valid_count} OK, {warn_count} will be truncated")
        if warn_count > 0:
            for w in warnings[:5]:
                print(f"    0x{w['offset']:08X}: {w['orig_length']} -> {w['new_length']} (+{w['overflow']} bytes)")
            if warn_count > 5:
                print(f"    ... and {warn_count - 5} more")

        print(f"Patching BIN file: {beam_dst}")
        patch_bin_file(beam_dst, beam_entries, korean_mapping, decode_table)

    # Save validation report if there are any warnings
    report_path = os.path.join(OUTPUT_DIR, "validation_report.md")
    total_warnings = save_validation_report(all_validation_warnings, report_path)
    if total_warnings > 0:
        print(f"\nValidation report saved: {report_path}")
        print(f"  Total truncation warnings: {total_warnings}")

    print(f"\n=== Done ===")
    print(f"Output directory: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
