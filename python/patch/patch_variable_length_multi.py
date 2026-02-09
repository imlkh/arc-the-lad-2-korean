#!/usr/bin/env python3
"""
Variable-Length Korean Translation Patcher - Multi-Chunk Support

This script patches ALL chunks with variable-length Korean translations,
using per-chunk VLUT offsets based on where actual data ends in each chunk.

Key insight: Each chunk has different amounts of data in the "padding" region
(0xA0000-0xB0000), so VLUT must be placed at different offsets.

Solution: Store a "master pointer" at fixed offset 0xAFF00 that points to
the VLUT location for that chunk. The trampoline reads this pointer first.

Usage:
    python patch_variable_length_multi.py [STG_NAME]

Prerequisites:
    - Run patch_all.py first to set up Korean font in COMM.IMG
"""

import os
import sys
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)  # python/
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(PYTHON_DIR, "decode"))

from patch_korean import (
    load_decode_table, build_korean_mapping, encode_korean_text,
    parse_translation_file, BASE_DIR, OUTPUT_DIR, GAME_DIR
)
from decode_text import scan_stg, build_decode_table


def load_unified_charmap():
    """Load the unified Korean character mapping from unified_charmap.txt.

    This ensures variable-length patching uses the SAME character IDs
    as the font glyphs in COMM.IMG (created by patch_all.py).

    Returns:
        dict: Korean character -> charID mapping
    """
    charmap_path = os.path.join(OUTPUT_DIR, "unified_charmap.txt")
    if not os.path.exists(charmap_path):
        print(f"WARNING: unified_charmap.txt not found at {charmap_path}")
        print("         Run patch_all.py first to create the unified character mapping.")
        return None

    korean_mapping = {}
    with open(charmap_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                try:
                    korean_char = parts[0]
                    char_id = int(parts[1])
                    korean_mapping[korean_char] = char_id
                except (ValueError, IndexError):
                    continue

    return korean_mapping

CHUNK_SIZE = 0xBC800
TEXT_REGION_OFFSET = 0xB4000

# Master pointer location - fixed for all chunks
# Trampoline reads this to find VLUT offset
MASTER_PTR_OFFSET = 0xAFF00

# Per-chunk VLUT offsets for S100.STG
VLUT_OFFSETS_S100 = {
    0: 0xA0800,   # Data ends ~0xA0700, 63KB available
    1: 0xA3D00,   # Data ends ~0xA3C00, 50KB available
    2: 0xA0500,   # Data ends ~0xA0400, 64KB available
    3: 0xA0100,   # Data ends ~0xA0000, 65KB available
    4: 0xA9500,   # Gap at 0xA94EA-0xAE87C, 20KB available (between data regions)
    5: 0xAA400,   # Data ends ~0xAA300, 23KB available
    6: 0xA2E00,   # Data ends ~0xA2D00, 54KB available
    7: 0xA0100,   # Data ends ~0xA0000, 65KB available
    8: 0,         # NO SPACE - fully packed data to 0xAFFFF
    9: 0xA0100,   # Data ends ~0xA0000, 65KB available
    10: 0xAD400,  # Data ends ~0xAD300, 11KB available
}

# Per-chunk VLUT offsets for SG00.STG (56 chunks)
VLUT_OFFSETS_SG00 = {
    0: 0,  # NO SPACE
    1: 0,  # NO SPACE
    2: 0xA0100,
    3: 0,  # NO SPACE
    4: 0,  # NO SPACE
    5: 0,  # NO SPACE
    6: 0,  # NO SPACE
    7: 0xA9800,
    8: 0,  # NO SPACE
    9: 0,  # NO SPACE
    10: 0,  # NO SPACE
    11: 0,  # NO SPACE
    12: 0xAB500,
    13: 0xA0100,
    14: 0xA0100,
    15: 0xA0100,
    16: 0xA0100,
    17: 0xA4600,
    18: 0xA0100,
    19: 0xA0100,
    20: 0xA0100,
    21: 0xAE900,
    22: 0,  # NO SPACE
    23: 0xA0100,
    24: 0,  # NO SPACE
    25: 0xA4100,
    26: 0xA0100,
    27: 0xA0100,
    28: 0xA2500,
    29: 0xA0100,
    30: 0xA0100,
    31: 0,  # NO SPACE
    32: 0xA0100,
    33: 0,  # NO SPACE
    34: 0xA8C00,
    35: 0xA0100,
    36: 0xA0100,
    37: 0xA0100,
    38: 0xA0100,
    39: 0,  # NO SPACE
    40: 0,  # NO SPACE
    41: 0xA0100,
    42: 0xA0100,
    43: 0xA0300,
    44: 0xA0100,
    45: 0xA0100,
    46: 0,  # NO SPACE
    47: 0xA0300,
    48: 0xA0100,
    49: 0xA7C00,
    50: 0xA5B00,
    51: 0xA0100,
    52: 0,  # NO SPACE
    53: 0,  # NO SPACE
    54: 0xA1E00,
    55: 0xA2E00,
}

# Per-chunk VLUT offsets for S200.STG (17 chunks)
# Full mapping: all chunks with verified free padding space.
# Chunks 0, 5, 9, 10, 14, 15, 16 have no space (fixed-length fallback).
VLUT_OFFSETS_S200 = {
    1: 0xA0100,   # 64KB free, empty padding
    2: 0xA0F00,   # 60KB free, data at 0xA0000-0xA0F00
    3: 0xA2800,   # 54KB free, data at 0xA0000-0xA2800
    4: 0xA7100,   # 35KB free, data at 0xA0000-0xA7100
    6: 0xA0100,   # 64KB free, empty padding
    7: 0xADC00,   # 9KB free (tight: ~5KB after VLUT gap)
    8: 0xA0100,   # 64KB free, empty padding
    11: 0xA9000,  # 28KB free, data at 0xA0000-0xA9000
    12: 0xA0100,  # 64KB free, empty padding
    13: 0xA9E00,  # 24KB free, data at 0xA0000-0xA9E00
}

# Korean text starts 0x1000 after VLUT (4KB for up to 1000 entries)
KOREAN_TEXT_GAP = 0x1000

# Per-chunk end boundaries (where Korean text must stop)
# Must not overwrite dialogue data in the padding region
KOREAN_TEXT_END_S100 = {
    4: 0xAE800,   # S100 Chunk 4: Dialogues at 0xAE87C (7 dialogues)
}
KOREAN_TEXT_END_SG00 = {
    41: 0xACB00,  # SG00 Chunk 41: Dialogues at 0xACCCC (51 dialogues)
}
DEFAULT_KOREAN_TEXT_END = 0xB0000


def auto_detect_vlut_offsets(data, num_chunks):
    """Scan each chunk's padding region (0xA0000-0xB0000) for free space.

    Finds the largest contiguous all-zero region in 256-byte blocks.
    Returns (vlut_offsets, korean_text_ends) where:
      - vlut_offsets: chunk_idx -> offset of VLUT start within chunk
      - korean_text_ends: chunk_idx -> end boundary (only if < 0xB0000)
    """
    PADDING_START = 0xA0000
    PADDING_END = 0xB0000
    MIN_FREE_SPACE = 0x2000  # 8KB minimum for VLUT + Korean text
    BLOCK_SIZE = 0x100       # 256-byte scan granularity

    vlut_offsets = {}
    korean_text_ends = {}

    for chunk_idx in range(num_chunks):
        chunk_base = chunk_idx * CHUNK_SIZE

        # Scan 256-byte blocks, marking each as zero or non-zero
        num_blocks = (PADDING_END - PADDING_START) // BLOCK_SIZE
        is_zero = []
        for b in range(num_blocks):
            block_start = chunk_base + PADDING_START + b * BLOCK_SIZE
            block_end = block_start + BLOCK_SIZE
            is_zero.append(all(x == 0 for x in data[block_start:block_end]))

        # Find the largest contiguous run of zero blocks
        best_start = -1
        best_len = 0
        cur_start = -1
        cur_len = 0
        for b in range(num_blocks):
            if is_zero[b]:
                if cur_start < 0:
                    cur_start = b
                    cur_len = 1
                else:
                    cur_len += 1
            else:
                if cur_len > best_len:
                    best_start = cur_start
                    best_len = cur_len
                cur_start = -1
                cur_len = 0
        # Check final run
        if cur_len > best_len:
            best_start = cur_start
            best_len = cur_len

        free_bytes = best_len * BLOCK_SIZE
        if free_bytes >= MIN_FREE_SPACE:
            region_start = PADDING_START + best_start * BLOCK_SIZE
            region_end = PADDING_START + (best_start + best_len) * BLOCK_SIZE

            # Align VLUT start to 0x100 boundary (already aligned by block scan)
            vlut_offsets[chunk_idx] = region_start

            # If the free region doesn't extend to 0xB0000, record the boundary
            if region_end < PADDING_END:
                korean_text_ends[chunk_idx] = region_end

    return vlut_offsets, korean_text_ends


def get_vlut_config(stg_name, data=None):
    """Get VLUT offsets and Korean text end boundaries for an STG file.

    For S100/SG00/S200: returns hardcoded, tested tables.
    For all others: auto-detects free space in padding region.

    Returns (vlut_offsets, korean_text_ends) tuple.
    """
    if stg_name == "S100":
        return VLUT_OFFSETS_S100, KOREAN_TEXT_END_S100
    elif stg_name == "SG00":
        return VLUT_OFFSETS_SG00, KOREAN_TEXT_END_SG00
    elif stg_name == "S200":
        return VLUT_OFFSETS_S200, {}
    elif data is not None:
        num_chunks = len(data) // CHUNK_SIZE
        return auto_detect_vlut_offsets(data, num_chunks)
    else:
        return {}, {}


def get_dialogues_by_chunk(stg_data, decode_table):
    """Use template-driven extraction to get dialogues grouped by chunk.

    Returns dict mapping chunk_idx -> list of dialogue dicts.
    """
    # Use the proper scan_stg function from decode_text.py
    dialogues, templates, stats = scan_stg(stg_data, decode_table,
                                           use_heuristics=True,
                                           filter_garbage=True)

    orphan = stats.get('orphan_menus_found', 0)
    event_script = stats.get('event_script_dialogues_found', 0)
    padding = stats.get('padding_dialogues_found', 0)
    print(f"  Template scan: {len(dialogues)} dialogues, "
          f"{stats['total_templates']} templates, "
          f"{stats.get('garbage_filtered', 0)} garbage filtered")
    print(f"  Non-template: {orphan} orphan menus, "
          f"{event_script} event-script, {padding} padding")

    # Group dialogues by chunk
    num_chunks = len(stg_data) // CHUNK_SIZE
    by_chunk = {i: [] for i in range(num_chunks)}

    # Bare dialogues (0x00B4) are accessed by game subsystems via direct offset,
    # not through the sequential text advance handler. They must NOT be in the
    # VLUT or they shift all subsequent indices causing freezes.
    # All other types (template, orphan menu, event script, padding) go through
    # the sequential handler and should be in the VLUT.
    SKIP_OPCODES = {0x00B4}
    skipped = 0
    for offset, consumed, text, context_opcode in dialogues:
        # if context_opcode in SKIP_OPCODES:
        #     skipped += 1
        #     continue

        chunk_idx = offset // CHUNK_SIZE
        if chunk_idx < num_chunks:
            # Extract the script prefix (first 2 bytes after [script:XX XX] tag)
            # The offset points to the script prefix, so prefix is at offset:offset+2
            prefix = bytes(stg_data[offset:offset+2])

            by_chunk[chunk_idx].append({
                'file_offset': offset,
                'prefix': prefix,
                'consumed': consumed,
                'text': text,
            })

    if skipped:
        print(f"  Skipped {skipped} bare dialogues (not VLUT-managed)")

    return by_chunk


def patch_chunk(data, chunk_idx, dialogues, translations, korean_mapping, decode_table, vlut_offsets,
                japanese_to_korean=None, korean_text_ends=None):
    """Patch a single chunk with variable-length translations."""
    chunk_start = chunk_idx * CHUNK_SIZE

    # Get VLUT offset for this chunk
    vlut_offset = vlut_offsets.get(chunk_idx, 0)
    if vlut_offset == 0:
        # No space in this chunk. Force master pointer to 0 so the
        # multi-chunk hook falls back to original handler safely.
        master_pos = chunk_start + MASTER_PTR_OFFSET
        struct.pack_into('<I', data, master_pos, 0)
        return data, {'patched': 0, 'skipped': len(dialogues), 'no_space': True}

    # Korean text starts after VLUT
    korean_start = vlut_offset + KOREAN_TEXT_GAP
    korean_end = (korean_text_ends or {}).get(chunk_idx, DEFAULT_KOREAN_TEXT_END)

    # Build translation lookup by file offset
    trans_by_offset = {}
    for entry in translations:
        offset = entry['offset']
        trans_by_offset[offset] = entry
        trans_by_offset[offset - 2] = entry  # Also key by marker offset

    # Use pre-built Japanese -> Korean mapping for cross-chunk matching
    trans_by_text = japanese_to_korean or {}

    write_pos = chunk_start + korean_start
    vlut_entries = []
    patched = 0
    skipped = 0

    for dlg in dialogues:
        orig_file_offset = dlg['file_offset']
        prefix = dlg['prefix']
        orig_text = dlg['text']

        # Try offset-based matching first, then fall back to text-based matching
        trans = trans_by_offset.get(orig_file_offset) or trans_by_offset.get(orig_file_offset + 2)
        if not trans and orig_text in trans_by_text:
            trans = trans_by_text[orig_text]

        if trans:
            korean_text = trans['text']
            encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

            # Size: marker(2) + prefix(2) + text + null(1)
            total_size = 2 + 2 + len(encoded) + 1

            if write_pos + total_size > chunk_start + korean_end:
                # Overflow - use original offset (relative to chunk start)
                orig_abs = orig_file_offset - chunk_start
                vlut_entries.append(orig_abs)
                skipped += 1
                continue

            # Write: [A9 00] [prefix] [encoded] [00]
            data[write_pos] = 0xA9
            data[write_pos + 1] = 0x00
            data[write_pos + 2:write_pos + 4] = prefix
            data[write_pos + 4:write_pos + 4 + len(encoded)] = encoded
            data[write_pos + 4 + len(encoded)] = 0x00

            # Offset from chunk start (skip A9 00 marker)
            new_offset = (write_pos - chunk_start) + 2
            vlut_entries.append(new_offset)

            write_pos += total_size
            patched += 1
        else:
            # No translation - use original offset (relative to chunk start)
            orig_abs = orig_file_offset - chunk_start
            vlut_entries.append(orig_abs)
            skipped += 1

    # Write VLUT table
    vlut = bytearray()
    vlut.extend(b'VLUT')
    vlut.extend(struct.pack('<I', len(vlut_entries)))
    for offset in vlut_entries:
        vlut.extend(struct.pack('<I', offset))

    table_pos = chunk_start + vlut_offset
    data[table_pos:table_pos + len(vlut)] = vlut

    # Write master pointer at fixed location
    master_pos = chunk_start + MASTER_PTR_OFFSET
    struct.pack_into('<I', data, master_pos, vlut_offset)

    korean_bytes = write_pos - (chunk_start + korean_start)

    return data, {
        'patched': patched,
        'skipped': skipped,
        'no_space': False,
        'vlut_offset': vlut_offset,
        'vlut_size': len(vlut),
        'korean_bytes': korean_bytes,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Variable-length Korean patcher (multi-chunk)")
    parser.add_argument("stg_name", nargs="?", default="S100",
                        help="STG file name (default: S100)")
    args = parser.parse_args()

    stg_name = args.stg_name.upper()

    print("=== Variable-Length Patcher (Multi-Chunk) ===")
    print()

    # Load resources
    print("Loading resources...")
    decode_table = load_decode_table()

    # Read from output/patched/translation/ (copied by patch_workflow.py)
    trans_path = os.path.join(BASE_DIR, "output", "patched", "translation", f"{stg_name}_STG.txt")
    if not os.path.exists(trans_path):
        print(f"ERROR: Translation file not found: {trans_path}")
        return 1

    translations = parse_translation_file(trans_path)
    print(f"  Translations: {len(translations)}")

    # Load unified Korean char mapping (must match COMM.IMG font)
    korean_mapping = load_unified_charmap()
    if korean_mapping is None:
        print("ERROR: Cannot proceed without unified_charmap.txt")
        print("       Run 'python patch_all.py' first to create font and charmap.")
        return 1
    print(f"  Loaded unified charmap: {len(korean_mapping)} chars")

    # Load STG file
    stg_path = os.path.join(OUTPUT_DIR, f"{stg_name}.STG")
    if not os.path.exists(stg_path):
        # Try original
        stg_path = os.path.join(GAME_DIR, f"{stg_name}.STG")

    if not os.path.exists(stg_path):
        print(f"ERROR: STG file not found")
        return 1

    print(f"  Loading: {stg_path}")
    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    num_chunks = len(data) // CHUNK_SIZE
    print(f"  Chunks: {num_chunks}")

    # Build decode table for scan_stg (from decode_text.py)
    scanner_decode_table = build_decode_table()

    # Use template-driven dialogue extraction
    print()
    print("Scanning for dialogues using template extraction...")
    dialogues_by_chunk = get_dialogues_by_chunk(bytes(data), scanner_decode_table)

    # Get VLUT offsets for this STG file
    vlut_offsets, korean_text_ends = get_vlut_config(stg_name, data)
    is_auto = stg_name not in ("S100", "SG00", "S200")
    if is_auto and vlut_offsets:
        print(f"  Auto-detected VLUT placement for {len(vlut_offsets)}/{num_chunks} chunks:")
        for ci in sorted(vlut_offsets.keys()):
            end = korean_text_ends.get(ci, DEFAULT_KOREAN_TEXT_END)
            avail = end - (vlut_offsets[ci] + KOREAN_TEXT_GAP)
            end_note = f" (end={end:#x})" if ci in korean_text_ends else ""
            print(f"    Chunk {ci:>2}: VLUT={vlut_offsets[ci]:#07x}  avail={avail // 1024:>2}KB{end_note}")
    else:
        print(f"  VLUT offsets configured for {len(vlut_offsets)} chunks")

    # Build Japanese text -> Korean translation mapping for cross-chunk matching
    # First, create offset -> Japanese text lookup from all dialogues
    offset_to_japanese = {}
    for chunk_idx, dlgs in dialogues_by_chunk.items():
        for dlg in dlgs:
            offset_to_japanese[dlg['file_offset']] = dlg['text']
            offset_to_japanese[dlg['file_offset'] + 2] = dlg['text']

    # Then, build Japanese -> Korean entry mapping from translations
    japanese_to_korean = {}
    for entry in translations:
        offset = entry['offset']
        japanese = offset_to_japanese.get(offset) or offset_to_japanese.get(offset - 2)
        if japanese:
            japanese_to_korean[japanese] = entry

    print(f"  Cross-chunk text mappings: {len(japanese_to_korean)}")

    # Patch all chunks
    print()
    print("Patching chunks...")
    print(f"{'Chunk':>5} {'VLUT':>8} {'Patched':>8} {'Skipped':>8} {'Korean':>8}")
    print("-" * 45)

    total_patched = 0
    total_skipped = 0
    chunks_no_space = []

    for chunk_idx in range(num_chunks):
        dialogues = dialogues_by_chunk.get(chunk_idx, [])

        if not dialogues:
            continue

        data, stats = patch_chunk(
            data, chunk_idx, dialogues, translations, korean_mapping, decode_table, vlut_offsets,
            japanese_to_korean, korean_text_ends
        )

        if stats['no_space']:
            chunks_no_space.append(chunk_idx)
            print(f"{chunk_idx:>5} {'N/A':>8} {0:>8} {stats['skipped']:>8} {'N/A':>8}  (no space)")
        else:
            print(f"{chunk_idx:>5} {stats['vlut_offset']:>#8x} {stats['patched']:>8} {stats['skipped']:>8} {stats['korean_bytes']:>8}")

        total_patched += stats['patched']
        total_skipped += stats['skipped']

    print("-" * 45)
    print(f"{'Total':>5} {'':<8} {total_patched:>8} {total_skipped:>8}")

    if chunks_no_space:
        print(f"\nChunks with no space (using fixed-length fallback): {chunks_no_space}")

    # Save
    out_path = os.path.join(OUTPUT_DIR, f"{stg_name}.STG")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    print(f"\nSaved: {out_path}")
    print()
    print("Next steps:")
    print("  1. python apply_hook.py --variable-length-multi")
    print("  2. python patch_bin.py <disc_image>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
