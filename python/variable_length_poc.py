#!/usr/bin/env python3
"""
Variable-Length Translation Proof of Concept

This script demonstrates the hook mechanism for variable-length Korean translations
in Arc the Lad 2.

SIMPLIFIED APPROACH FOR POC:
Instead of complex runtime lookup, we patch the text advance handler to:
1. Read dialogue index from state->SeqIndex (offset 0x9A)
2. Look up the dialogue offset from a table stored at a KNOWN RAM address
3. Add this to the text base to get the new TextPtr

The lookup table is stored in a fixed RAM location that we reserve.

Usage:
    python variable_length_poc.py

Output:
    output/patched_vl/SCPS_100.26  - Patched executable with trampoline
    output/patched_vl/S100.STG     - Original (patched separately with translations)
    output/patched_vl/analysis.txt - Detailed analysis of what was done
"""

import os
import struct
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GAME_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "patched_vl")

# File paths
SCPS_PATH = os.path.join(GAME_DIR, "SCPS_100.26")
STG_PATH = os.path.join(GAME_DIR, "S100.STG")

# Constants
CHUNK_SIZE = 0xBC800
TEXT_REGION_OFFSET = 0xB4000
PADDING_OFFSET = 0xA0000
LOOKUP_TABLE_OFFSET = 0xA0800  # After the ~0x700 bytes of actual data

# SCPS_100.26 addresses
JUMP_TABLE_ENTRY5_FILE = 0x0C2F74  # Entry 5 in jump table (points to handler)
ORIGINAL_HANDLER = 0x80101560
TRAMPOLINE_FILE = 0x0D8A54  # 668 bytes available
TRAMPOLINE_RAM = 0x80199654

def file_to_ram(offset):
    """Convert SCPS_100.26 file offset to RAM address"""
    return offset - 0x800 + 0x800C1400

def ram_to_file(addr):
    """Convert RAM address to SCPS_100.26 file offset"""
    return addr - 0x800C1400 + 0x800


def assemble_trampoline():
    """
    Generate MIPS machine code for the lookup trampoline.

    The trampoline:
    1. Gets current dialogue index from state->SeqIndex (+0x9A)
    2. Calculates chunk base from state->TextPtr (+0x78)
    3. Looks up new text offset from table
    4. Updates state->TextPtr
    5. Increments state->SeqIndex
    6. Returns

    Register usage:
    - $a0: State structure pointer (passed in)
    - $v0, $v1, $t0, $t1: Temporaries
    """

    code = []

    # Function prologue
    code.append(0x27BDFFF0)  # addiu $sp, $sp, -16
    code.append(0xAFBF000C)  # sw $ra, 12($sp)
    code.append(0xAFA40000)  # sw $a0, 0($sp)  ; Save state pointer

    # Load current TextPtr to calculate chunk base
    # TextPtr is somewhere in chunk + 0xB4000 to + 0xBC7FF
    # Chunk base = (TextPtr & 0xFFF00000) | ((TextPtr >> 20) << 20)
    # Actually simpler: chunk base = TextPtr - (TextPtr & 0xFFFFF) + some offset
    #
    # Better approach: Store chunk base in a known RAM location when chunk loads
    # For POC, we'll use a fixed approach assuming chunk 0 loads at a known address
    #
    # Actually, let's check the TextPtr value and derive chunk base from it.
    # TextPtr points into text region (chunk + 0xB4000 to chunk + 0xBC7FF)
    # So: chunk_base = TextPtr - (TextPtr & 0x000FFFFF)  -- clear lower 20 bits
    # Wait, that's not right either because chunk size is 0xBC800 not a power of 2.
    #
    # Simplest for POC: Assume we know chunk base is stored at a fixed RAM location.
    # We'll patch the chunk loader to store this.
    #
    # For now, let's use a REALLY simple approach:
    # - The lookup table is at a fixed offset in the chunk (0xA0800)
    # - TextPtr & 0xFFF00000 gives us the chunk's RAM base approximately
    # - We add 0xA0800 to get the table

    # Actually, TextPtr points into 0xB4xxx area of chunk
    # If chunk loads at 0x80xxxxxx, then TextPtr = chunk_base + 0xB4xxx
    # We need chunk_base + 0xA0800 for the table
    #
    # chunk_base = TextPtr - 0xB4xxx = TextPtr - (TextPtr & 0x0FFFF) + adjustment
    # This is getting complicated. Let me use a simpler method.
    #
    # For POC: Hard-code the table address based on where chunk 0 loads.
    # We'll figure out dynamic loading later.

    # Let's check where STG chunks load in RAM...
    # Actually, we should just put the lookup table address directly in the code.
    # For Phase 1 POC, we'll patch per-chunk with the correct address.

    # SIMPLIFIED APPROACH FOR POC:
    # 1. Load SeqIndex
    # 2. Load hardcoded table base (we'll patch this per chunk)
    # 3. Lookup and update TextPtr
    # 4. Increment SeqIndex

    # Load state pointer (already in $a0)

    # Load SeqIndex from state+0x9A
    code.append(0x94820098 + 2)  # lhu $v0, 0x9A($a0)  -- SeqIndex

    # Check if index is within bounds (skip lookup if too large)
    # For POC, assume table has magic header with count
    # Actually, let's just do the lookup unconditionally for now

    # Calculate table offset: index * 4
    code.append(0x00021080)  # sll $v0, $v0, 2  ; index * 4

    # Load table base (PLACEHOLDER - will be patched)
    # lui $t0, TABLE_HI
    # ori $t0, $t0, TABLE_LO
    code.append(0x3C080000)  # lui $t0, 0x0000  (PATCH: high 16 bits of table addr)
    code.append(0x35080000)  # ori $t0, $t0, 0x0000  (PATCH: low 16 bits)

    # Skip header (8 bytes): table[0] = magic, table[1] = count
    code.append(0x25080008)  # addiu $t0, $t0, 8  ; Skip header

    # Add index offset
    code.append(0x01024021)  # addu $t0, $t0, $v0  ; &table[index]

    # Load new TextPtr from table
    code.append(0x8D020000)  # lw $v0, 0($t0)  ; new_ptr = table[index]

    # Check if valid (non-zero)
    code.append(0x10400005)  # beq $v0, $zero, skip_update
    code.append(0x00000000)  # nop (delay slot)

    # Update state->TextPtr
    code.append(0xAC820078)  # sw $v0, 0x78($a0)  ; state->TextPtr = new_ptr

    # Increment SeqIndex
    code.append(0x94820098 + 2)  # lhu $v0, 0x9A($a0)  ; reload SeqIndex
    code.append(0x24420001)  # addiu $v0, $v0, 1
    code.append(0xA4820098 + 2)  # sh $v0, 0x9A($a0)

    # skip_update:
    # Function epilogue
    code.append(0x8FA40000)  # lw $a0, 0($sp)  ; Restore state pointer
    code.append(0x8FBF000C)  # lw $ra, 12($sp)
    code.append(0x27BD0010)  # addiu $sp, $sp, 16
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop (delay slot)

    return code


def patch_scps(scps_data, table_ram_addr):
    """
    Patch SCPS_100.26:
    1. Write trampoline code
    2. Update jump table entry 5 to point to trampoline
    3. Patch trampoline with correct table address
    """
    data = bytearray(scps_data)

    # Generate trampoline code
    trampoline = assemble_trampoline()

    # Patch table address in trampoline
    # Instructions at offset 3 and 4 are lui/ori for table address
    table_hi = (table_ram_addr >> 16) & 0xFFFF
    table_lo = table_ram_addr & 0xFFFF

    trampoline[3] = 0x3C080000 | table_hi  # lui $t0, table_hi
    trampoline[4] = 0x35080000 | table_lo  # ori $t0, $t0, table_lo

    # Write trampoline to executable
    for i, instr in enumerate(trampoline):
        offset = TRAMPOLINE_FILE + i * 4
        struct.pack_into('<I', data, offset, instr)

    # Update jump table entry 5 to point to trampoline
    struct.pack_into('<I', data, JUMP_TABLE_ENTRY5_FILE, TRAMPOLINE_RAM)

    print(f"Patched SCPS_100.26:")
    print(f"  Trampoline at: 0x{TRAMPOLINE_RAM:08X} ({len(trampoline)*4} bytes)")
    print(f"  Jump table entry 5: 0x{TRAMPOLINE_RAM:08X}")
    print(f"  Table address in code: 0x{table_ram_addr:08X}")

    return bytes(data)


def parse_dialogues_from_chunk(stg_data, chunk_idx):
    """
    Parse dialogue offsets from a chunk's text region.
    Returns list of (offset_in_chunk, text_bytes) tuples.
    """
    chunk_start = chunk_idx * CHUNK_SIZE
    text_start = chunk_start + TEXT_REGION_OFFSET
    text_end = chunk_start + CHUNK_SIZE

    dialogues = []

    # Scan for A9 00 markers (dialogue stream markers)
    i = text_start
    while i < text_end - 2:
        if stg_data[i] == 0xA9 and stg_data[i+1] == 0x00:
            # Found a dialogue marker
            # Skip marker (2 bytes) and script prefix (2 bytes)
            text_offset = i + 2  # Offset to script prefix

            # Find the null terminator
            j = i + 4  # Skip marker and prefix
            while j < text_end and stg_data[j] != 0x00:
                j += 1

            # Calculate offset relative to chunk start
            rel_offset = text_offset - chunk_start
            dialogues.append((rel_offset, j - text_offset))

            i = j + 1
        else:
            i += 1

    return dialogues


def create_lookup_table(dialogues, chunk_ram_base):
    """
    Create a lookup table for dialogue offsets.

    Format:
    - 4 bytes: Magic "DLUT"
    - 4 bytes: Entry count
    - N * 4 bytes: RAM addresses of each dialogue
    """
    table = bytearray()

    # Header
    table.extend(b'DLUT')  # Magic
    table.extend(struct.pack('<I', len(dialogues)))  # Count

    # Entries: RAM addresses of each dialogue
    for offset_in_chunk, _ in dialogues:
        ram_addr = chunk_ram_base + offset_in_chunk
        table.extend(struct.pack('<I', ram_addr))

    return bytes(table)


def patch_stg_chunk(stg_data, chunk_idx, lookup_table):
    """
    Patch an STG chunk to include the lookup table in its padding region.
    """
    data = bytearray(stg_data)

    chunk_start = chunk_idx * CHUNK_SIZE
    table_offset = chunk_start + LOOKUP_TABLE_OFFSET

    # Write lookup table
    data[table_offset:table_offset + len(lookup_table)] = lookup_table

    return bytes(data)


def find_chunk_load_address():
    """
    Determine where STG chunks are loaded in RAM.

    For POC, we'll analyze the game's memory layout.
    STG chunks are typically loaded at a fixed address.

    Based on analysis:
    - Main executable: 0x800C1400 - 0x8019EC00
    - Overlays: 0x80026000
    - Chunks likely load around 0x80200000 or use the area before main exe

    For POC, let's assume chunk loads at 0x80040000 (before main exe).
    This will need to be verified with actual emulator testing.
    """
    # This is a guess - needs verification
    # Common PS1 memory layout puts large data before the main executable
    return 0x80040000


def main():
    print("=== Variable-Length Translation POC ===")
    print()

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load files
    print("Loading files...")
    with open(SCPS_PATH, "rb") as f:
        scps_data = f.read()
    with open(STG_PATH, "rb") as f:
        stg_data = f.read()

    # Determine chunk load address (needs verification)
    chunk_ram_base = find_chunk_load_address()
    print(f"Assumed chunk RAM base: 0x{chunk_ram_base:08X}")
    print("  (This needs verification with emulator!)")
    print()

    # Calculate lookup table RAM address
    table_ram_addr = chunk_ram_base + LOOKUP_TABLE_OFFSET
    print(f"Lookup table will be at: 0x{table_ram_addr:08X}")
    print()

    # Parse dialogues from chunk 0
    print("Parsing dialogues from S100.STG chunk 0...")
    dialogues = parse_dialogues_from_chunk(stg_data, 0)
    print(f"  Found {len(dialogues)} dialogue entries")
    print()

    # Create lookup table
    print("Creating lookup table...")
    lookup_table = create_lookup_table(dialogues, chunk_ram_base)
    print(f"  Table size: {len(lookup_table)} bytes")
    print()

    # Patch SCPS_100.26
    print("Patching SCPS_100.26...")
    patched_scps = patch_scps(scps_data, table_ram_addr)

    # Patch S100.STG
    print()
    print("Patching S100.STG chunk 0...")
    patched_stg = patch_stg_chunk(stg_data, 0, lookup_table)
    print(f"  Wrote lookup table at chunk offset 0x{LOOKUP_TABLE_OFFSET:05X}")

    # Save patched files
    print()
    print("Saving patched files...")

    scps_out = os.path.join(OUTPUT_DIR, "SCPS_100.26")
    with open(scps_out, "wb") as f:
        f.write(patched_scps)
    print(f"  Saved: {scps_out}")

    stg_out = os.path.join(OUTPUT_DIR, "S100.STG")
    with open(stg_out, "wb") as f:
        f.write(patched_stg)
    print(f"  Saved: {stg_out}")

    print()
    print("=== POC Complete ===")
    print()
    print("IMPORTANT: The chunk RAM base address is a guess!")
    print("You need to verify this in an emulator by:")
    print("1. Loading the game")
    print("2. Finding where S100.STG chunk 0 loads in memory")
    print("3. Updating find_chunk_load_address() with the correct value")
    print()
    print("To test:")
    print("1. Copy patched files to your game image")
    print("2. Load in emulator (DuckStation recommended)")
    print("3. Watch for crashes or incorrect dialogue display")


if __name__ == "__main__":
    main()
