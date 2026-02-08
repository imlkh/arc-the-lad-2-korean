#!/usr/bin/env python3
"""
POC Step 2: Lookup Table Implementation

This script extends the passthrough hook to actually perform lookup table
redirection for variable-length translations.

APPROACH:
1. Store lookup table at a fixed RAM address (we reserve space in BSS-adjacent area)
2. Trampoline reads SeqIndex, looks up offset, updates TextPtr
3. For dialogues not in table, fall back to original behavior

The lookup table is embedded in SCPS_100.26 at a known offset, loaded into RAM.

Usage:
    python poc_lookup_impl.py [--test-only]

    --test-only: Only analyze, don't write files
"""

import os
import struct
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GAME_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "patched_vl")

SCPS_PATH = os.path.join(GAME_DIR, "SCPS_100.26")
STG_PATH = os.path.join(GAME_DIR, "S100.STG")

# SCPS_100.26 addresses
JUMP_TABLE_FILE = 0x0C2F60
JUMP_TABLE_ENTRY5 = JUMP_TABLE_FILE + 5 * 4
ORIGINAL_HANDLER = 0x80101560

# Trampoline location (in unused area)
TRAMPOLINE_FILE = 0x0D8A54
TRAMPOLINE_RAM = 0x80199654

# Lookup table location (also in unused area, after trampoline)
# We have 668 bytes starting at 0x0D8A54, trampoline uses ~60 bytes
LOOKUP_TABLE_FILE = 0x0D8A80  # 44 bytes after trampoline start
LOOKUP_TABLE_RAM = 0x80199680

# Chunk constants
CHUNK_SIZE = 0xBC800
TEXT_REGION_OFFSET = 0xB4000


def create_lookup_trampoline(table_ram_addr, original_handler):
    """
    Create trampoline that:
    1. Loads SeqIndex from state structure
    2. Checks if within lookup table bounds
    3. If yes: load offset from table, update TextPtr
    4. If no: call original handler
    5. Increment SeqIndex
    6. Return

    Register usage:
    - $a0: State structure pointer (preserved from caller)
    - $v0, $v1: Temporaries
    - $t0, $t1: Table operations

    State structure offsets:
    - 0x78: TextPtr (4 bytes) - we update this
    - 0x9A: SeqIndex (2 bytes) - dialogue counter
    - 0x7C: TextBase (4 bytes) - base address for text

    Lookup table format:
    - [0:4] Magic "VLUT"
    - [4:8] Entry count (N)
    - [8:12] Text base address
    - [12:16+N*4] Offsets (relative to text base)
    """
    code = []

    table_hi = (table_ram_addr >> 16) & 0xFFFF
    table_lo = table_ram_addr & 0xFFFF

    # Adjust for addiu sign extension if low part >= 0x8000
    if table_lo >= 0x8000:
        table_hi += 1
        table_lo = table_lo - 0x10000  # Will be negative

    # Function prologue
    code.append(0x27BDFFF0)  # addiu $sp, $sp, -16
    code.append(0xAFBF000C)  # sw $ra, 12($sp)
    code.append(0xAFA40008)  # sw $a0, 8($sp)    ; Save state pointer

    # Load lookup table base
    code.append(0x3C080000 | table_hi)  # lui $t0, table_hi
    if table_lo < 0:
        code.append(0x25080000 | (table_lo & 0xFFFF))  # addiu $t0, $t0, table_lo
    else:
        code.append(0x35080000 | table_lo)  # ori $t0, $t0, table_lo

    # Check magic (first 4 bytes should be "VLUT" = 0x54554C56)
    code.append(0x8D020000)  # lw $v0, 0($t0)    ; magic
    code.append(0x3C035455)  # lui $v1, 0x5455   ; "UT" in big endian
    code.append(0x34634C56)  # ori $v1, $v1, 0x4C56  ; "LV" in big endian
    # Actually on PS1 (little endian): "VLUT" = 0x54554C56
    # Let me fix this - we need the LE representation
    # 'V' = 0x56, 'L' = 0x4C, 'U' = 0x55, 'T' = 0x54
    # LE 32-bit: first byte at lowest addr = 0x56, then 0x4C, 0x55, 0x54
    # So 32-bit value = 0x544C5556 (reading bytes in order V,L,U,T but as LE word)
    # Wait, let me think again...
    # In memory: addr+0='V'(0x56), addr+1='L'(0x4C), addr+2='U'(0x55), addr+3='T'(0x54)
    # LE lw reads: addr+0 as LSB, addr+3 as MSB
    # So value = 0x54554C56
    # Actually that's what I had. Let me recalculate:
    # "VLUT" as 4 chars: V=0x56, L=0x4C, U=0x55, T=0x54
    # Little endian in memory at offset 0: byte 0=V, 1=L, 2=U, 3=T
    # LW reads it as: bits 0-7 from byte 0, bits 8-15 from byte 1, etc
    # So LW value = T<<24 | U<<16 | L<<8 | V = 0x54554C56
    # Hmm that's different from what I wrote. Let me fix:

    # After loading table base in $t0, redo the magic check
    code = code[:5]  # Keep prologue and table load

    # Load magic and check
    code.append(0x8D020000)  # lw $v0, 0($t0)    ; magic
    code.append(0x3C035455)  # lui $v1, 0x5455   ; high part of 0x54554C56
    code.append(0x34634C56)  # ori $v1, $v1, 0x4C56  ; full magic value

    code.append(0x14430018)  # bne $v0, $v1, fallback (skip ~24 instructions)
    code.append(0x00000000)  # nop

    # Load entry count and SeqIndex
    code.append(0x8D020004)  # lw $v0, 4($t0)    ; entry count
    code.append(0x94830000 | 0x9A)  # lhu $v1, 0x9A($a0) ; SeqIndex

    # Check if SeqIndex < entry_count
    code.append(0x0062082A)  # slt $at, $v1, $v0  ; $at = (SeqIndex < count)
    code.append(0x10200012)  # beq $at, $zero, fallback
    code.append(0x00000000)  # nop

    # Load text base from table
    code.append(0x8D090008)  # lw $t1, 8($t0)    ; text_base

    # Calculate table entry address: &table[12 + SeqIndex*4]
    code.append(0x00031880)  # sll $v1, $v1, 2   ; SeqIndex * 4
    code.append(0x01034021)  # addu $t0, $t0, $v1 ; table + SeqIndex*4
    code.append(0x8D02000C)  # lw $v0, 12($t0)   ; offset = table[12 + SeqIndex*4]

    # Check if offset is valid (non-zero)
    code.append(0x1040000B)  # beq $v0, $zero, fallback
    code.append(0x00000000)  # nop

    # Calculate new TextPtr = text_base + offset
    code.append(0x01221021)  # addu $v0, $t1, $v0 ; new_ptr = text_base + offset

    # Update state->TextPtr
    code.append(0xAC820078)  # sw $v0, 0x78($a0)

    # Increment SeqIndex
    code.append(0x94820000 | 0x9A)  # lhu $v0, 0x9A($a0)
    code.append(0x24420001)  # addiu $v0, $v0, 1
    code.append(0xA4820000 | 0x9A)  # sh $v0, 0x9A($a0)

    # Epilogue and return
    code.append(0x8FA40008)  # lw $a0, 8($sp)
    code.append(0x8FBF000C)  # lw $ra, 12($sp)
    code.append(0x27BD0010)  # addiu $sp, $sp, 16
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop

    # Fallback: call original handler
    # fallback:
    code.append(0x8FA40008)  # lw $a0, 8($sp)    ; Restore $a0 for original
    jal_target = (original_handler >> 2) & 0x03FFFFFF
    code.append(0x0C000000 | jal_target)  # jal original_handler
    code.append(0x00000000)  # nop

    code.append(0x8FBF000C)  # lw $ra, 12($sp)
    code.append(0x27BD0010)  # addiu $sp, $sp, 16
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop

    return code


def parse_stg_dialogues(stg_data, chunk_idx=0):
    """
    Parse dialogue positions from an STG chunk.
    Returns list of (offset_in_text_region, text_length) tuples.
    """
    chunk_start = chunk_idx * CHUNK_SIZE
    text_start = chunk_start + TEXT_REGION_OFFSET
    text_end = chunk_start + CHUNK_SIZE

    dialogues = []

    # Scan for A9 00 markers
    i = text_start
    while i < text_end - 4:
        if stg_data[i] == 0xA9 and stg_data[i+1] == 0x00:
            # A9 00 marker found
            # Text starts after marker (2 bytes) + script prefix (2 bytes)
            text_offset = i - chunk_start  # Offset within chunk

            # Find null terminator
            j = i + 4
            while j < text_end and stg_data[j] != 0x00:
                j += 1

            text_len = j - (i + 4)

            # Store offset relative to text region
            dialogues.append((text_offset - TEXT_REGION_OFFSET, text_len))
            i = j + 1
        else:
            i += 1

    return dialogues


def create_lookup_table(dialogues, text_base_ram):
    """
    Create a lookup table for dialogue offsets.

    Format:
    - [0:4] Magic "VLUT" (0x54554C56 in LE)
    - [4:8] Entry count
    - [8:12] Text base RAM address
    - [12:...] Offsets (4 bytes each, relative to text base)
    """
    table = bytearray()

    # Magic
    table.extend(b'VLUT')

    # Entry count
    table.extend(struct.pack('<I', len(dialogues)))

    # Text base RAM address (placeholder - needs runtime patching or known value)
    table.extend(struct.pack('<I', text_base_ram))

    # Offsets
    for offset, _ in dialogues:
        table.extend(struct.pack('<I', offset))

    return bytes(table)


def main():
    parser = argparse.ArgumentParser(description="POC Step 2: Lookup Implementation")
    parser.add_argument("--test-only", action="store_true", help="Analyze only, don't write")
    args = parser.parse_args()

    print("=" * 60)
    print("POC Step 2: Lookup Table Implementation")
    print("=" * 60)
    print()

    # Load files
    print(f"Loading {SCPS_PATH}...")
    with open(SCPS_PATH, "rb") as f:
        scps_data = f.read()

    print(f"Loading {STG_PATH}...")
    with open(STG_PATH, "rb") as f:
        stg_data = f.read()

    # Parse dialogues from chunk 0
    print("\nParsing S100.STG chunk 0 dialogues...")
    dialogues = parse_stg_dialogues(stg_data, 0)
    print(f"  Found {len(dialogues)} dialogues")

    if dialogues:
        print(f"  First 5 offsets: {[hex(d[0]) for d in dialogues[:5]]}")
        print(f"  Last 5 offsets: {[hex(d[0]) for d in dialogues[-5:]]}")

    # Create lookup table
    # For POC, assume text base is at a known address
    # This will need to be determined at runtime or per-chunk
    TEXT_BASE_PLACEHOLDER = 0x80080000  # Placeholder - needs verification

    print(f"\nCreating lookup table...")
    print(f"  Text base (placeholder): 0x{TEXT_BASE_PLACEHOLDER:08X}")

    lookup_table = create_lookup_table(dialogues, TEXT_BASE_PLACEHOLDER)
    print(f"  Table size: {len(lookup_table)} bytes")
    print(f"  Header: magic='VLUT', count={len(dialogues)}, base=0x{TEXT_BASE_PLACEHOLDER:08X}")

    # Generate trampoline
    print(f"\nGenerating trampoline code...")
    trampoline = create_lookup_trampoline(LOOKUP_TABLE_RAM, ORIGINAL_HANDLER)
    print(f"  Trampoline size: {len(trampoline) * 4} bytes")
    print(f"  Location: RAM 0x{TRAMPOLINE_RAM:08X}")

    # Check if everything fits
    total_size = len(trampoline) * 4 + len(lookup_table)
    available = 668  # From our analysis
    print(f"\nSpace check:")
    print(f"  Trampoline: {len(trampoline) * 4} bytes")
    print(f"  Lookup table: {len(lookup_table)} bytes")
    print(f"  Total: {total_size} bytes")
    print(f"  Available: {available} bytes")
    print(f"  Status: {'OK' if total_size <= available else 'OVERFLOW!'}")

    if total_size > available:
        print("\nERROR: Not enough space for table + trampoline!")
        print("Consider storing lookup table in STG chunk padding instead.")
        return 1

    if args.test_only:
        print("\n[Test mode - not writing files]")
        return 0

    # Patch SCPS_100.26
    print(f"\nPatching SCPS_100.26...")
    data = bytearray(scps_data)

    # Write trampoline
    for i, instr in enumerate(trampoline):
        offset = TRAMPOLINE_FILE + i * 4
        struct.pack_into('<I', data, offset, instr)
    print(f"  Wrote trampoline at 0x{TRAMPOLINE_FILE:06X}")

    # Write lookup table
    table_file_offset = LOOKUP_TABLE_FILE
    data[table_file_offset:table_file_offset + len(lookup_table)] = lookup_table
    print(f"  Wrote lookup table at 0x{table_file_offset:06X}")

    # Update jump table entry
    struct.pack_into('<I', data, JUMP_TABLE_ENTRY5, TRAMPOLINE_RAM)
    print(f"  Updated jump table entry 5 -> 0x{TRAMPOLINE_RAM:08X}")

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "SCPS_100.26")
    with open(output_path, "wb") as f:
        f.write(data)
    print(f"\nSaved: {output_path}")

    print()
    print("=" * 60)
    print("IMPORTANT NOTES")
    print("=" * 60)
    print("""
The lookup table uses a PLACEHOLDER text base address (0x80080000).
This WILL NOT WORK until the correct address is determined.

To find the correct text base address:
1. Run the game in an emulator with debugging (DuckStation)
2. Set a breakpoint at 0x80101560 (original handler)
3. When it breaks, examine the state structure at $a0
4. Look at offset 0x7C - this contains the text base
5. Update TEXT_BASE_PLACEHOLDER with this value

Alternatively, modify the trampoline to read text_base from
the state structure dynamically (state->TextBase at offset 0x7C).
""")

    return 0


if __name__ == "__main__":
    exit(main())
