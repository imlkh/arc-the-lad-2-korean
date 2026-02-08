#!/usr/bin/env python3
"""
Variable-Length Korean Translation Patcher

This script writes Korean translations at NEW positions (not overwriting Japanese),
enabling full-length translations without truncation.

Approach:
1. Parse Korean translations
2. Encode each dialogue (full length)
3. Write to padding region (0xA1000+, after lookup table)
4. Build lookup table pointing to new positions
5. Trampoline hook redirects TextPtr to new locations

Usage:
    python patch_variable_length.py [STG_NAME]
"""

import os
import sys
import struct
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch_korean import (
    load_decode_table, extract_korean_chars, build_korean_mapping,
    encode_korean_text, parse_translation_file,
    GAME_DIR, BASE_DIR, OUTPUT_DIR
)

CHUNK_SIZE = 0xBC800
TEXT_REGION_OFFSET = 0xB4000
LOOKUP_TABLE_OFFSET = 0xA0800
# Start Korean text after lookup table
# Table: 8 header + up to 1000 entries * 4 bytes = ~4008 bytes max
# Table ends at: 0xA0800 + 4008 = 0xA17A8
# Start Korean text at 0xA2000 for safety (16KB gap from 0xA0000)
KOREAN_TEXT_OFFSET = 0xA2000
KOREAN_TEXT_END = 0xB0000  # End of padding region


def parse_chunk_dialogues(stg_data, chunk_idx):
    """Parse original dialogue markers (A9 00) from a chunk."""
    chunk_start = chunk_idx * CHUNK_SIZE
    text_start = chunk_start + TEXT_REGION_OFFSET
    text_end = chunk_start + CHUNK_SIZE

    dialogues = []
    i = text_start
    while i < text_end - 4 and i < len(stg_data) - 4:
        if stg_data[i] == 0xA9 and stg_data[i + 1] == 0x00:
            # Found dialogue marker
            # Get script prefix
            prefix = stg_data[i + 2:i + 4]

            # Find end of text
            # Stop at: null terminator (00) OR next A9 00 marker
            j = i + 4
            next_start = None
            while j < text_end - 1 and j < len(stg_data) - 1:
                # Check for next A9 00 marker (start of next dialogue)
                if stg_data[j] == 0xA9 and stg_data[j + 1] == 0x00:
                    # This is the next dialogue, current one ends here (no null)
                    next_start = j  # Next iteration starts here
                    break
                # Check for null terminator
                if stg_data[j] == 0x00:
                    next_start = j + 1  # Next iteration starts after null
                    break
                j += 1

            # Original offset from text region start
            orig_offset = i - text_start
            orig_length = j - i  # Including marker, prefix, text, but not null

            dialogues.append({
                'orig_offset': orig_offset,
                'orig_length': orig_length,
                'prefix': prefix,
                'file_offset': i,
            })
            i = next_start if next_start else j + 1
        else:
            i += 1

    return dialogues


def create_lookup_table(entries):
    """Create lookup table with new offsets."""
    table = bytearray()
    table.extend(b'VLUT')
    table.extend(struct.pack('<I', len(entries)))

    for offset in entries:
        table.extend(struct.pack('<I', offset))

    return bytes(table)


def patch_chunk_variable_length(stg_data, chunk_idx, translations, korean_mapping, decode_table):
    """
    Patch a single chunk with variable-length translations.

    Returns: (patched_data, stats)
    """
    chunk_start = chunk_idx * CHUNK_SIZE
    data = bytearray(stg_data)

    # Parse original dialogues
    dialogues = parse_chunk_dialogues(stg_data, chunk_idx)

    if not dialogues:
        return bytes(data), {'dialogues': 0, 'patched': 0, 'skipped': 0}

    # Build translation lookup by original file offset
    # Translation offset points to script prefix, marker is 2 bytes before
    trans_by_offset = {}
    for entry in translations:
        offset = entry['offset']
        text = entry['text']
        prefix = entry.get('script_prefix', b'\x00\x00')
        # Key by marker offset (offset - 2), or by prefix offset
        trans_by_offset[offset] = (prefix, text)
        trans_by_offset[offset - 2] = (prefix, text)  # Also key by marker offset

    # Write Korean text to padding region
    korean_text_start = chunk_start + KOREAN_TEXT_OFFSET
    korean_text_end = chunk_start + KOREAN_TEXT_END
    write_pos = korean_text_start

    lookup_offsets = []
    patched = 0
    skipped = 0

    for dlg in dialogues:
        orig_file_offset = dlg['file_offset']
        prefix = dlg['prefix']

        # Check if we have a translation (try both marker offset and prefix offset)
        trans_entry = trans_by_offset.get(orig_file_offset) or trans_by_offset.get(orig_file_offset + 2)

        if trans_entry:
            trans_prefix, korean_text = trans_entry

            # Encode Korean text
            encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

            # Calculate space needed: marker(2) + prefix(2) + text + null(1)
            total_size = 2 + 2 + len(encoded) + 1

            # Check if fits in padding region
            if write_pos + total_size > korean_text_end:
                print(f"    WARNING: Chunk {chunk_idx} overflow at dialogue {len(lookup_offsets)}")
                # Fall back to original offset
                lookup_offsets.append(dlg['orig_offset'] + 2)  # Point to prefix
                skipped += 1
                continue

            # Write to padding region: [A9 00] [prefix] [encoded text] [00]
            data[write_pos] = 0xA9
            data[write_pos + 1] = 0x00
            data[write_pos + 2:write_pos + 4] = prefix
            data[write_pos + 4:write_pos + 4 + len(encoded)] = encoded
            data[write_pos + 4 + len(encoded)] = 0x00

            # Store offset (relative to text region start)
            new_offset = write_pos - chunk_start - TEXT_REGION_OFFSET + KOREAN_TEXT_OFFSET - TEXT_REGION_OFFSET
            # Actually, let's store offset relative to where trampoline expects
            # The trampoline does: chunk_base + TEXT_REGION_OFFSET + offset
            # So we need: offset = (write_pos - chunk_start) - TEXT_REGION_OFFSET
            # But write_pos is in padding (0xA1000), not text region (0xB4000)
            # So offset would be negative... that won't work.

            # Better approach: store absolute offset from chunk start
            # Then trampoline does: chunk_base + offset
            # We need to modify the trampoline to not add TEXT_REGION_OFFSET

            # For now, let's use a different format:
            # Store offset from chunk start (not from text region)
            new_offset = write_pos - chunk_start + 2  # +2 to skip A9 00 marker

            lookup_offsets.append(new_offset)
            write_pos += total_size
            patched += 1
        else:
            # No translation, use original offset (relative to chunk start)
            # Original text is at text_region + orig_offset, so we need:
            # chunk_base + TEXT_REGION_OFFSET + orig_offset + 2 (to skip A9 00)
            # But our new format is chunk_base + offset, so:
            orig_abs_offset = TEXT_REGION_OFFSET + dlg['orig_offset'] + 2
            lookup_offsets.append(orig_abs_offset)
            skipped += 1

    # Write lookup table
    table = create_lookup_table(lookup_offsets)
    table_offset = chunk_start + LOOKUP_TABLE_OFFSET
    data[table_offset:table_offset + len(table)] = table

    stats = {
        'dialogues': len(dialogues),
        'patched': patched,
        'skipped': skipped,
        'table_size': len(table),
        'korean_bytes': write_pos - korean_text_start,
    }

    return bytes(data), stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Variable-length Korean patcher")
    parser.add_argument("stg_name", nargs="?", default="S100",
                        help="STG file name (default: S100)")
    parser.add_argument("--chunk", type=int, default=None,
                        help="Patch only specific chunk (default: all)")
    args = parser.parse_args()

    stg_name = args.stg_name.upper()

    print("=== Variable-Length Korean Patcher ===")
    print()

    # Load character table
    print("Loading character table...")
    decode_table = load_decode_table()

    # Load translation file
    trans_path = os.path.join(BASE_DIR, "translated", "ko", f"{stg_name}_STG.txt")
    if not os.path.exists(trans_path):
        print(f"ERROR: Translation file not found: {trans_path}")
        return 1

    print(f"Loading translations: {trans_path}")
    translations = parse_translation_file(trans_path)
    print(f"  Found {len(translations)} translations")

    # Extract Korean characters and build mapping
    print("Building Korean character mapping...")
    korean_chars = set()
    for entry in translations:
        text = entry['text']
        for ch in text:
            if '\uAC00' <= ch <= '\uD7A3':
                korean_chars.add(ch)

    korean_mapping = build_korean_mapping(list(korean_chars), decode_table)
    print(f"  Mapped {len(korean_mapping)} Korean characters")

    # Load STG file - prefer already-patched file from output if it exists
    stg_dst = os.path.join(OUTPUT_DIR, f"{stg_name}.STG")
    stg_src_patched = stg_dst  # Try patched file first
    stg_src_original = os.path.join(GAME_DIR, f"{stg_name}.STG")

    if os.path.exists(stg_src_patched):
        stg_src = stg_src_patched
        print(f"\nLoading (already patched): {stg_src}")
    else:
        stg_src = stg_src_original
        print(f"\nLoading (original): {stg_src}")

    with open(stg_src, "rb") as f:
        stg_data = f.read()

    num_chunks = len(stg_data) // CHUNK_SIZE
    print(f"  Chunks: {num_chunks}")

    # Patch chunks
    print("\nPatching chunks (variable-length)...")

    total_patched = 0
    total_skipped = 0

    if args.chunk is not None:
        chunks_to_patch = [args.chunk]
    else:
        chunks_to_patch = range(num_chunks)

    for chunk_idx in chunks_to_patch:
        stg_data, stats = patch_chunk_variable_length(
            stg_data, chunk_idx, translations, korean_mapping, decode_table
        )

        if stats['dialogues'] > 0:
            print(f"  Chunk {chunk_idx:2d}: {stats['patched']:4d} patched, "
                  f"{stats['skipped']:4d} skipped, "
                  f"{stats['korean_bytes']:5d} bytes Korean text")
            total_patched += stats['patched']
            total_skipped += stats['skipped']

    print(f"\nTotal: {total_patched} patched, {total_skipped} skipped")

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(stg_dst, "wb") as f:
        f.write(stg_data)
    print(f"\nSaved: {stg_dst}")

    print("\n" + "=" * 50)
    print("IMPORTANT: The lookup table format has changed!")
    print("Offsets are now relative to CHUNK START, not text region.")
    print("The trampoline needs to be updated to handle this.")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
