#!/usr/bin/env python3
"""
Add lookup tables to all chunks in a Korean-patched STG file.

This adds a VLUT lookup table to each chunk's padding region (offset 0xA0800),
enabling the trampoline hook to find dialogue offsets.

Usage:
    python add_lookup_table.py [STG_NAME]

    STG_NAME: S100, SG00, etc. (default: S100)
"""

import os
import struct
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "patched")

CHUNK_SIZE = 0xBC800  # 772,096 bytes
TEXT_REGION_OFFSET = 0xB4000
LOOKUP_TABLE_OFFSET = 0xA0800


def parse_chunk_dialogues(stg_data, chunk_idx):
    """Parse dialogue positions from a single chunk."""
    chunk_start = chunk_idx * CHUNK_SIZE
    text_start = chunk_start + TEXT_REGION_OFFSET
    text_end = chunk_start + CHUNK_SIZE

    if text_start >= len(stg_data):
        return []

    dialogues = []
    i = text_start
    while i < text_end - 4 and i < len(stg_data) - 4:
        if stg_data[i] == 0xA9 and stg_data[i + 1] == 0x00:
            offset = i - text_start
            j = i + 4
            while j < text_end and j < len(stg_data) and stg_data[j] != 0x00:
                j += 1
            dialogues.append((offset, j - (i + 4)))
            i = j + 1
        else:
            i += 1
    return dialogues


def create_lookup_table(dialogues):
    """Create lookup table with relative offsets."""
    table = bytearray()
    table.extend(b'VLUT')
    table.extend(struct.pack('<I', len(dialogues)))
    for offset, _ in dialogues:
        # Point to script prefix (after A9 00 marker)
        table.extend(struct.pack('<I', offset + 2))
    return bytes(table)


def add_tables_to_stg(stg_path):
    """Add lookup tables to all chunks in an STG file."""
    print(f"Loading {stg_path}...")
    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    file_size = len(data)
    num_chunks = file_size // CHUNK_SIZE
    print(f"  File size: {file_size:,} bytes")
    print(f"  Chunks: {num_chunks}")
    print()

    total_dialogues = 0
    chunks_with_dialogues = 0

    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * CHUNK_SIZE

        # Parse dialogues
        dialogues = parse_chunk_dialogues(data, chunk_idx)

        if not dialogues:
            print(f"  Chunk {chunk_idx:2d}: No dialogues found, skipping")
            continue

        # Create lookup table
        table = create_lookup_table(dialogues)

        # Write table to chunk
        table_offset = chunk_start + LOOKUP_TABLE_OFFSET
        data[table_offset:table_offset + len(table)] = table

        print(f"  Chunk {chunk_idx:2d}: {len(dialogues):4d} dialogues, table {len(table):5d} bytes at 0x{table_offset:08X}")

        total_dialogues += len(dialogues)
        chunks_with_dialogues += 1

    # Save
    with open(stg_path, "wb") as f:
        f.write(data)

    print()
    print(f"Saved: {stg_path}")
    print(f"  Total: {total_dialogues} dialogues across {chunks_with_dialogues} chunks")

    return total_dialogues, chunks_with_dialogues


def main():
    parser = argparse.ArgumentParser(description="Add lookup tables to STG file")
    parser.add_argument("stg_name", nargs="?", default="S100",
                        help="STG file name without extension (default: S100)")
    args = parser.parse_args()

    stg_name = args.stg_name.upper()
    if not stg_name.endswith(".STG"):
        stg_name = stg_name + ".STG"

    stg_path = os.path.join(OUTPUT_DIR, stg_name)

    print("=== Add Lookup Tables to STG ===")
    print()

    if not os.path.exists(stg_path):
        print(f"ERROR: {stg_path} not found!")
        print("       Run 'python patch_all.py' first.")
        return 1

    total, chunks = add_tables_to_stg(stg_path)

    if total == 0:
        print("WARNING: No dialogues found!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
