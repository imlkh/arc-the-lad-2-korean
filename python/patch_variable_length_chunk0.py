#!/usr/bin/env python3
"""
Variable-Length Korean Translation Patcher - Chunk 0 Only

This script patches chunk 0 of S100.STG with variable-length Korean translations.
Korean text is written to the padding region (0xA2000) and VLUT table at 0xA0800.

Usage:
    python patch_variable_length_chunk0.py

Prerequisites:
    - Run patch_all.py first to set up Korean font in COMM.IMG
"""

import os
import sys
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from patch_korean import (
    load_decode_table, build_korean_mapping, encode_korean_text,
    parse_translation_file, BASE_DIR, OUTPUT_DIR
)

CHUNK_SIZE = 0xBC800
TEXT_REGION_OFFSET = 0xB4000
LOOKUP_TABLE_OFFSET = 0xA0800
KOREAN_TEXT_OFFSET = 0xA2000
KOREAN_TEXT_END = 0xB0000


def parse_chunk_dialogues(stg_data, chunk_idx):
    """Parse dialogue markers from a chunk."""
    chunk_start = chunk_idx * CHUNK_SIZE
    text_start = chunk_start + TEXT_REGION_OFFSET
    text_end = chunk_start + CHUNK_SIZE

    dialogues = []
    i = text_start
    while i < text_end - 4 and i < len(stg_data) - 4:
        if stg_data[i] == 0xA9 and stg_data[i + 1] == 0x00:
            offset = i - text_start
            prefix = bytes(stg_data[i+2:i+4])
            j = i + 4
            while j < text_end - 1 and j < len(stg_data) - 1:
                if stg_data[j] == 0xA9 and stg_data[j + 1] == 0x00:
                    break
                if stg_data[j] == 0x00:
                    break
                j += 1
            dialogues.append({
                'offset': offset,
                'file_offset': i,
                'prefix': prefix,
                'length': j - i
            })
            i = j + 1 if stg_data[j] == 0x00 else j
        else:
            i += 1
    return dialogues


def main():
    print("=== Variable-Length Patcher (Chunk 0) ===")
    print()

    # Load resources
    print("Loading resources...")
    decode_table = load_decode_table()

    trans_path = os.path.join(BASE_DIR, "translated", "ko", "S100_STG.txt")
    if not os.path.exists(trans_path):
        print(f"ERROR: Translation file not found: {trans_path}")
        return 1

    translations = parse_translation_file(trans_path)
    print(f"  Translations: {len(translations)}")

    # Build Korean char mapping
    korean_chars = set()
    for entry in translations:
        for ch in entry['text']:
            if '\uAC00' <= ch <= '\uD7A3':
                korean_chars.add(ch)
    korean_mapping = build_korean_mapping(list(korean_chars), decode_table)
    print(f"  Korean chars: {len(korean_mapping)}")

    # Load STG file
    stg_path = os.path.join(OUTPUT_DIR, "S100.STG")
    if not os.path.exists(stg_path):
        print(f"ERROR: {stg_path} not found. Run patch_all.py first.")
        return 1

    print(f"  Loading: {stg_path}")
    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    # Parse dialogues in chunk 0
    chunk_idx = 0
    chunk_start = chunk_idx * CHUNK_SIZE
    dialogues = parse_chunk_dialogues(data, chunk_idx)
    print(f"  Dialogues in chunk 0: {len(dialogues)}")

    # Build translation lookup
    trans_by_offset = {}
    for entry in translations:
        offset = entry['offset']
        trans_by_offset[offset] = entry
        trans_by_offset[offset - 2] = entry

    # Write Korean text to padding region
    print()
    print("Patching chunk 0...")
    write_pos = chunk_start + KOREAN_TEXT_OFFSET
    korean_region_start = write_pos
    vlut_entries = []
    patched = 0
    skipped = 0

    for dlg in dialogues:
        orig_file_offset = dlg['file_offset']
        prefix = dlg['prefix']

        trans = trans_by_offset.get(orig_file_offset) or trans_by_offset.get(orig_file_offset + 2)

        if trans:
            korean_text = trans['text']
            encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

            total_size = 2 + 2 + len(encoded) + 1

            if write_pos + total_size > chunk_start + KOREAN_TEXT_END:
                orig_abs_offset = TEXT_REGION_OFFSET + dlg['offset'] + 2
                vlut_entries.append(orig_abs_offset)
                skipped += 1
                continue

            # Write: [A9 00] [prefix] [encoded] [00]
            data[write_pos] = 0xA9
            data[write_pos + 1] = 0x00
            data[write_pos + 2:write_pos + 4] = prefix
            data[write_pos + 4:write_pos + 4 + len(encoded)] = encoded
            data[write_pos + 4 + len(encoded)] = 0x00

            # Offset from chunk start
            new_offset = (write_pos + 2) - chunk_start
            vlut_entries.append(new_offset)

            write_pos += total_size
            patched += 1
        else:
            orig_abs_offset = TEXT_REGION_OFFSET + dlg['offset'] + 2
            vlut_entries.append(orig_abs_offset)
            skipped += 1

    korean_bytes = write_pos - korean_region_start

    # Write VLUT table
    vlut = bytearray()
    vlut.extend(b'VLUT')
    vlut.extend(struct.pack('<I', len(vlut_entries)))
    for offset in vlut_entries:
        vlut.extend(struct.pack('<I', offset))

    table_offset = chunk_start + LOOKUP_TABLE_OFFSET
    data[table_offset:table_offset + len(vlut)] = vlut

    # Save
    with open(stg_path, "wb") as f:
        f.write(data)

    print(f"  Patched: {patched} dialogues")
    print(f"  Skipped: {skipped} dialogues (no translation)")
    print(f"  Korean text: {korean_bytes} bytes at 0x{KOREAN_TEXT_OFFSET:X}")
    print(f"  VLUT table: {len(vlut)} bytes at 0x{LOOKUP_TABLE_OFFSET:X}")
    print()
    print(f"Saved: {stg_path}")
    print()
    print("Next steps:")
    print("  1. python apply_hook.py --variable-length")
    print("  2. python patch_bin.py <disc_image>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
