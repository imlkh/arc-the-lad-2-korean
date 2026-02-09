#!/usr/bin/env python3
"""Catalog every non-dialogue byte sequence in STG text regions.

Scans all 19 STG files and classifies byte runs in the text region
(0xB4000-0xBC800 per chunk) that are NOT templates or script opcodes.

Output: JSON catalog + summary statistics showing structural signatures
of event triggers, MIPS fragments, and data tables.

Usage:
    python catalog_text_region.py              # scan all STG files
    python catalog_text_region.py S100.STG     # scan one file
    python catalog_text_region.py --verbose    # show all byte runs
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

# Add parent to path for imports
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from decode_text import (
    build_decode_table, decode_string, _find_templates, _find_script_ranges,
    _is_garbage_text, _has_mips_opcode_signature,
    STG_CHUNK_SIZE, STG_TEXT_REGION_OFFSET, STG_TEXT_REGION_SIZE,
    TEMPLATE_SIZE, SCRIPT_BLOCK_SIZE
)

STG_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "..")
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "decoded", "stg")


def classify_byte_run(data, start, end):
    """Classify a non-null byte run by its structural signature.

    Returns (type_name, detail_dict).
    """
    raw = data[start:end]
    length = end - start

    # Check for 0xFF control codes (text encoding marker)
    has_ff = b'\xff' in raw
    has_ef = b'\xef' in raw
    has_f0_fe = any(0xF0 <= b <= 0xFE for b in raw)
    has_text_ctrl = has_ff or has_ef or has_f0_fe

    # Event trigger: starts with 67 00
    if length >= 6 and raw[0:2] == b'\x67\x00':
        return 'event_trigger', {
            'bytes': raw[:min(16, length)].hex(),
            'has_80plus': sum(1 for b in raw[2:min(14, length)] if b >= 0x80),
        }

    # Data table reference: starts with A9 00 or AA 00
    if length >= 4 and raw[0] in (0xA9, 0xAA) and raw[1] == 0x00:
        if has_text_ctrl:
            return 'dialogue_with_marker', {
                'marker': f'{raw[0]:02X} 00',
                'bytes': raw[:min(8, length)].hex(),
            }
        return 'data_table_ref', {
            'marker': f'{raw[0]:02X} 00',
            'bytes': raw[:min(16, length)].hex(),
        }

    # Has text control sequences → likely dialogue
    if has_text_ctrl:
        return 'dialogue', {
            'bytes': raw[:min(8, length)].hex(),
        }

    # Check for MIPS-like patterns
    # Common MIPS signatures: high density of 0x80, 0x8C, 0x01, 0x00
    byte_80_count = sum(1 for b in raw if b == 0x80)
    byte_8c_count = sum(1 for b in raw if b == 0x8C)
    byte_01_count = sum(1 for b in raw if b == 0x01)

    if length >= 6:
        marker_density = (byte_80_count + byte_8c_count) / length
        if marker_density >= 0.15:
            return 'mips_code', {
                'bytes': raw[:min(20, length)].hex(),
                'marker_density': round(marker_density, 2),
                '80_count': byte_80_count,
                '8c_count': byte_8c_count,
            }

    # Short runs with no text control = binary fragment
    if length <= 4:
        return 'short_binary', {
            'bytes': raw.hex(),
        }

    # Longer runs without text control = unclassified binary
    return 'unclassified_binary', {
        'bytes': raw[:min(20, length)].hex(),
        'byte_01_count': byte_01_count,
    }


def find_non_null_runs(data, start, end):
    """Find all non-null byte runs in data[start:end].

    Returns list of (run_start, run_end) where data[run_start:run_end]
    contains no null bytes and is bounded by nulls or region edges.
    """
    runs = []
    pos = start
    while pos < end:
        if data[pos] == 0x00:
            pos += 1
            continue
        run_start = pos
        while pos < end and data[pos] != 0x00:
            pos += 1
        runs.append((run_start, pos))
    return runs


def ranges_cover(offset, ranges):
    """Check if offset falls within any of the given ranges."""
    for rs, re_ in ranges:
        if rs <= offset < re_:
            return True
        if rs > offset:
            break
    return False


def scan_chunk_text_region(data, chunk_idx, decode_table, verbose=False):
    """Scan one chunk's text region and catalog all byte runs."""
    chunk_start = chunk_idx * STG_CHUNK_SIZE
    text_start = chunk_start + STG_TEXT_REGION_OFFSET
    text_end = min(chunk_start + STG_CHUNK_SIZE, len(data))

    if text_start >= len(data):
        return []

    # Find known structures in this region
    all_templates = _find_templates(data)
    templates_in_region = [(t[0], t[0] + TEMPLATE_SIZE)
                           for t in all_templates
                           if text_start <= t[0] < text_end]

    script_ranges = _find_script_ranges(data, text_start, text_end)

    # Build set of covered byte ranges
    covered = sorted(templates_in_region + script_ranges)

    # Find all non-null byte runs
    runs = find_non_null_runs(data, text_start, text_end)

    results = []
    for run_start, run_end in runs:
        # Skip if entirely covered by template or script opcode
        if any(cs <= run_start and run_end <= ce for cs, ce in covered):
            continue

        # Skip if run starts inside a template
        in_template = any(cs <= run_start < ce for cs, ce in templates_in_region)
        if in_template:
            continue

        # Skip if run starts inside a script opcode block
        in_script = any(cs <= run_start < ce for cs, ce in script_ranges)
        if in_script:
            continue

        chunk_offset = run_start - chunk_start
        length = run_end - run_start

        type_name, detail = classify_byte_run(data, run_start, run_end)

        # Try to decode as text for comparison
        text_decoded = None
        garbage_rule = None
        mips_sig = None
        if type_name not in ('dialogue', 'dialogue_with_marker'):
            text_decoded_str, consumed = decode_string(data, run_start,
                                                        decode_table, prefix=0)
            if text_decoded_str:
                text_decoded = text_decoded_str
                if _is_garbage_text(text_decoded_str):
                    garbage_rule = "caught by _is_garbage_text"
                if _has_mips_opcode_signature(data, run_start, consumed, prefix=0):
                    mips_sig = "caught by _has_mips_opcode_signature"

        entry = {
            'chunk': chunk_idx,
            'offset': f'0x{run_start:08X}',
            'chunk_offset': f'0x{chunk_offset:05X}',
            'length': length,
            'type': type_name,
            'detail': detail,
        }
        if text_decoded:
            entry['decoded_text'] = text_decoded[:80]
        if garbage_rule:
            entry['garbage_filter'] = garbage_rule
        if mips_sig:
            entry['mips_filter'] = mips_sig

        results.append(entry)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Catalog non-dialogue byte sequences in STG text regions"
    )
    parser.add_argument("files", nargs="*",
                        help="STG file(s) to scan (default: all)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show all byte runs including dialogues")
    parser.add_argument("--json", action="store_true",
                        help="Output full JSON catalog")
    args = parser.parse_args()

    if args.files:
        stg_files = []
        for f in args.files:
            path = os.path.join(STG_DIR, f) if not os.path.isabs(f) else f
            if os.path.exists(path):
                stg_files.append(path)
            else:
                print(f"Not found: {path}", file=sys.stderr)
    else:
        stg_files = sorted(glob.glob(os.path.join(STG_DIR, "*.STG")))

    if not stg_files:
        print("No STG files found", file=sys.stderr)
        sys.exit(1)

    decode_table = build_decode_table()

    all_results = []
    type_counts = Counter()
    type_by_file = defaultdict(Counter)
    # Track unique MIPS byte signatures across files
    mips_signatures = defaultdict(set)
    event_trigger_patterns = defaultdict(set)
    data_table_patterns = defaultdict(set)

    for filepath in stg_files:
        basename = os.path.basename(filepath)
        data = open(filepath, "rb").read()
        num_chunks = len(data) // STG_CHUNK_SIZE

        file_results = []
        for chunk_idx in range(num_chunks):
            chunk_results = scan_chunk_text_region(data, chunk_idx,
                                                    decode_table,
                                                    verbose=args.verbose)
            file_results.extend(chunk_results)

        for r in file_results:
            type_counts[r['type']] += 1
            type_by_file[basename][r['type']] += 1

            # Collect signatures
            if r['type'] == 'mips_code':
                # Use first 8 bytes as signature key
                sig = r['detail']['bytes'][:16]  # 8 bytes = 16 hex chars
                mips_signatures[sig].add(basename)
            elif r['type'] == 'event_trigger':
                sig = r['detail']['bytes'][:4]  # first 2 bytes
                event_trigger_patterns[sig].add(basename)
            elif r['type'] == 'data_table_ref':
                sig = r['detail']['bytes'][:4]
                data_table_patterns[sig].add(basename)

        all_results.extend(file_results)

        non_dialogue = [r for r in file_results
                        if r['type'] not in ('dialogue', 'dialogue_with_marker')]
        print(f"{basename}: {len(file_results)} byte runs "
              f"({len(non_dialogue)} non-dialogue)")

    # Summary
    print(f"\n=== Type Summary ===")
    for type_name, count in type_counts.most_common():
        print(f"  {type_name:30s} {count:6d}")

    # MIPS signatures shared across files
    shared_mips = {sig: files for sig, files in mips_signatures.items()
                   if len(files) >= 2}
    if shared_mips:
        print(f"\n=== Shared MIPS Signatures (in 2+ files) ===")
        for sig, files in sorted(shared_mips.items(),
                                  key=lambda x: -len(x[1])):
            print(f"  {sig}: {len(files)} files")
            if args.verbose:
                for f in sorted(files):
                    print(f"    {f}")

    # Event trigger patterns
    if event_trigger_patterns:
        print(f"\n=== Event Trigger Patterns ===")
        for sig, files in sorted(event_trigger_patterns.items(),
                                  key=lambda x: -len(x[1])):
            print(f"  {sig}: {len(files)} files")

    # Non-dialogue entries NOT caught by existing filters
    uncaught = [r for r in all_results
                if r['type'] not in ('dialogue', 'dialogue_with_marker')
                and 'garbage_filter' not in r and 'mips_filter' not in r]
    print(f"\n=== Non-dialogue entries NOT caught by existing filters: "
          f"{len(uncaught)} ===")
    if uncaught and args.verbose:
        for r in uncaught[:50]:
            print(f"  {r['offset']} chunk{r['chunk']} "
                  f"{r['type']:25s} len={r['length']:3d} "
                  f"{r['detail'].get('bytes', '')[:40]}")
            if 'decoded_text' in r:
                print(f"    text: {r['decoded_text'][:60]}")

    # JSON output
    if args.json:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        json_path = os.path.join(OUTPUT_DIR, 'text_region_catalog.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': dict(type_counts),
                'shared_mips_signatures': {k: sorted(v) for k, v in shared_mips.items()},
                'entries': all_results,
            }, f, indent=2, ensure_ascii=False)
        print(f"\nJSON catalog written to: {json_path}")


if __name__ == '__main__':
    main()
