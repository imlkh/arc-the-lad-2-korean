#!/usr/bin/env python3
"""
POC Step 3: Chunk-Based Lookup Table

This script stores the lookup table in the STG chunk padding region,
not in SCPS_100.26. The trampoline calculates the table address
dynamically from the current TextPtr.

APPROACH:
1. Trampoline in SCPS_100.26 (fits in 668 bytes)
2. Lookup table in STG chunk at offset 0xA0800 (64KB available)
3. Trampoline calculates table address from TextPtr:
   - TextPtr points to: chunk_base + 0xB4xxx
   - Table at: chunk_base + 0xA0800
   - Offset from text region to table: 0xB4000 - 0xA0800 = 0x13800

Usage:
    python poc_chunk_table.py [--test-only]
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

# Trampoline location (in unused area of SCPS_100.26)
TRAMPOLINE_FILE = 0x0D8A54
TRAMPOLINE_RAM = 0x80199654

# Chunk constants
CHUNK_SIZE = 0xBC800
TEXT_REGION_OFFSET = 0xB4000
LOOKUP_TABLE_OFFSET = 0xA0800

# Offset from text region start to lookup table
# table_addr = (TextPtr & 0xFFFF0000) - 0x13800
# Actually: text_region_start = chunk_base + 0xB4000
#           table = chunk_base + 0xA0800
#           table = text_region_start - 0x13800
TEXT_TO_TABLE_OFFSET = TEXT_REGION_OFFSET - LOOKUP_TABLE_OFFSET  # 0x13800


def create_chunk_trampoline(original_handler):
    """
    Create trampoline that:
    1. Gets TextPtr from state structure
    2. Calculates chunk base: chunk_base = (TextPtr & 0xFFF00000)
    3. Calculates table address: table = chunk_base + 0xA0800
    4. Loads SeqIndex, looks up offset from table
    5. Converts offset to absolute address: chunk_base + 0xB4000 + offset
    6. Updates TextPtr with absolute address
    7. Increments SeqIndex
    8. Returns

    Register usage:
    - $a0: State structure pointer (passed in, preserved)
    - $v0, $v1: Temporaries
    - $t0: Table base / temp
    - $t1: Entry value (offset), then absolute address
    - $t2: Chunk base (saved for address calculation)

    State structure offsets:
    - 0x78: TextPtr (4 bytes)
    - 0x9A: SeqIndex (2 bytes)

    Lookup table format (at chunk + 0xA0800):
    - [0:4] Magic "VLUT" (0x54554C56 LE)
    - [4:8] Entry count (N)
    - [8:...] Offsets (relative to text region start, 4 bytes each)
    """
    code = []

    # Function prologue (save $ra, $a0, $t2)
    code.append(0x27BDFFE8)  # addiu $sp, $sp, -24
    code.append(0xAFBF0014)  # sw $ra, 20($sp)
    code.append(0xAFA40010)  # sw $a0, 16($sp)
    code.append(0xAFAA000C)  # sw $t2, 12($sp)

    # Load TextPtr
    code.append(0x8C820078)  # lw $v0, 0x78($a0)

    # Calculate chunk base: mask to 1MB alignment
    code.append(0x3C03FFF0)  # lui $v1, 0xFFF0
    code.append(0x00431024)  # and $v0, $v0, $v1

    # Save chunk base in $t2
    code.append(0x00405021)  # addu $t2, $v0, $zero

    # Calculate table address: chunk_base + 0xA0800
    code.append(0x3C08000A)  # lui $t0, 0x000A
    code.append(0x35080800)  # ori $t0, $t0, 0x0800
    code.append(0x00484021)  # addu $t0, $v0, $t0

    # Check magic "VLUT" = 0x54554C56
    code.append(0x8D020000)  # lw $v0, 0($t0)
    code.append(0x3C035455)  # lui $v1, 0x5455
    code.append(0x34634C56)  # ori $v1, $v1, 0x4C56
    # Branch to fallback if magic doesn't match (22 instructions ahead)
    code.append(0x14430016)  # bne $v0, $v1, fallback
    code.append(0x00000000)  # nop

    # Load entry count
    code.append(0x8D020004)  # lw $v0, 4($t0)

    # Load SeqIndex
    code.append(0x8FA40010)  # lw $a0, 16($sp)
    code.append(0x9483009A)  # lhu $v1, 0x9A($a0)

    # Check bounds: SeqIndex < entry_count
    code.append(0x0062082A)  # slt $at, $v1, $v0
    # Branch to fallback if out of bounds (16 instructions ahead)
    code.append(0x10200010)  # beq $at, $zero, fallback
    code.append(0x00000000)  # nop

    # Calculate entry address: table + 8 + (SeqIndex * 4)
    code.append(0x00031880)  # sll $v1, $v1, 2
    code.append(0x01034021)  # addu $t0, $t0, $v1
    code.append(0x8D090008)  # lw $t1, 8($t0)

    # Check if offset is valid (non-zero)
    # Branch to fallback if zero (10 instructions ahead)
    code.append(0x1120000A)  # beq $t1, $zero, fallback
    code.append(0x00000000)  # nop

    # Convert relative offset to absolute address
    # new_ptr = chunk_base ($t2) + TEXT_REGION_OFFSET + offset ($t1)
    code.append(0x3C03000B)  # lui $v1, 0x000B
    code.append(0x34634000)  # ori $v1, $v1, 0x4000
    code.append(0x01431021)  # addu $v0, $t2, $v1
    code.append(0x00494821)  # addu $t1, $v0, $t1

    # Update TextPtr
    code.append(0xAC890078)  # sw $t1, 0x78($a0)

    # Increment SeqIndex
    code.append(0x9482009A)  # lhu $v0, 0x9A($a0)
    code.append(0x24420001)  # addiu $v0, $v0, 1
    code.append(0xA482009A)  # sh $v0, 0x9A($a0)

    # Success epilogue
    code.append(0x8FAA000C)  # lw $t2, 12($sp)
    code.append(0x8FBF0014)  # lw $ra, 20($sp)
    code.append(0x27BD0018)  # addiu $sp, $sp, 24
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop

    # fallback: call original handler
    code.append(0x8FA40010)  # lw $a0, 16($sp)
    jal_target = (original_handler >> 2) & 0x03FFFFFF
    code.append(0x0C000000 | jal_target)  # jal original_handler
    code.append(0x00000000)  # nop

    # Fallback epilogue
    code.append(0x8FAA000C)  # lw $t2, 12($sp)
    code.append(0x8FBF0014)  # lw $ra, 20($sp)
    code.append(0x27BD0018)  # addiu $sp, $sp, 24
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop

    return code


def parse_stg_dialogues(stg_data, chunk_idx=0):
    """
    Parse dialogue positions from an STG chunk.
    Returns list of (offset_from_text_region_start, text_length) tuples.
    """
    chunk_start = chunk_idx * CHUNK_SIZE
    text_start = chunk_start + TEXT_REGION_OFFSET
    text_end = chunk_start + CHUNK_SIZE

    dialogues = []

    # Scan for A9 00 markers (dialogue stream)
    i = text_start
    while i < text_end - 4:
        if stg_data[i] == 0xA9 and stg_data[i + 1] == 0x00:
            # Found dialogue marker
            # Offset from text region start
            offset = i - text_start

            # Find null terminator
            j = i + 4  # Skip marker (2) + prefix (2)
            while j < text_end and stg_data[j] != 0x00:
                j += 1

            length = j - (i + 4)
            dialogues.append((offset, length))
            i = j + 1
        else:
            i += 1

    return dialogues


def create_lookup_table_relative(dialogues):
    """
    Create lookup table with offsets relative to text region start.

    Format:
    - [0:4] Magic "VLUT" (0x54554C56 LE)
    - [4:8] Entry count
    - [8:...] Offsets (relative to text region, 4 bytes each)
    """
    table = bytearray()

    # Magic
    table.extend(b'VLUT')

    # Entry count
    table.extend(struct.pack('<I', len(dialogues)))

    # Offsets (relative to text region start)
    # Add 2 to skip the A9 00 marker and point to prefix+text
    for offset, _ in dialogues:
        table.extend(struct.pack('<I', offset + 2))

    return bytes(table)


def disassemble_trampoline(code, base_addr):
    """Print disassembly for verification."""
    print(f"\n=== Trampoline Disassembly ({len(code) * 4} bytes) ===\n")

    for i, instr in enumerate(code):
        addr = base_addr + i * 4
        # Basic opcode decode
        op = (instr >> 26) & 0x3F
        if op == 0:  # R-type
            funct = instr & 0x3F
            if funct == 0x21:
                mnem = "addu"
            elif funct == 0x24:
                mnem = "and"
            elif funct == 0x00:
                rd = (instr >> 11) & 0x1F
                sa = (instr >> 6) & 0x1F
                if rd == 0 and sa == 0:
                    mnem = "nop"
                else:
                    mnem = "sll"
            elif funct == 0x08:
                mnem = "jr"
            elif funct == 0x2A:
                mnem = "slt"
            else:
                mnem = f"R-type funct=0x{funct:02X}"
        elif op == 0x09:
            mnem = "addiu"
        elif op == 0x23:
            mnem = "lw"
        elif op == 0x2B:
            mnem = "sw"
        elif op == 0x25:
            mnem = "lhu"
        elif op == 0x29:
            mnem = "sh"
        elif op == 0x0F:
            mnem = "lui"
        elif op == 0x0D:
            mnem = "ori"
        elif op == 0x05:
            mnem = "bne"
        elif op == 0x04:
            mnem = "beq"
        elif op == 0x03:
            target = (instr & 0x03FFFFFF) << 2
            mnem = f"jal 0x{target:08X}"
        else:
            mnem = f"op=0x{op:02X}"

        print(f"0x{addr:08X}: {instr:08X}  {mnem}")


def main():
    parser = argparse.ArgumentParser(description="POC Step 3: Chunk-Based Lookup")
    parser.add_argument("--test-only", action="store_true", help="Analyze only, don't write")
    args = parser.parse_args()

    print("=" * 60)
    print("POC Step 3: Chunk-Based Lookup Table")
    print("=" * 60)
    print()
    print("This stores the lookup table in the STG chunk, not SCPS_100.26.")
    print("The trampoline calculates table address from TextPtr dynamically.")
    print()

    # Load files
    print(f"Loading {SCPS_PATH}...")
    with open(SCPS_PATH, "rb") as f:
        scps_data = f.read()

    print(f"Loading {STG_PATH}...")
    with open(STG_PATH, "rb") as f:
        stg_data = f.read()

    # Parse dialogues
    print("\nParsing S100.STG chunk 0 dialogues...")
    dialogues = parse_stg_dialogues(stg_data, 0)
    print(f"  Found {len(dialogues)} dialogues")

    if dialogues:
        print(f"  First 5 offsets: {[hex(d[0]) for d in dialogues[:5]]}")
        print(f"  Last 5 offsets: {[hex(d[0]) for d in dialogues[-5:]]}")

    # Create lookup table
    print("\nCreating lookup table (relative offsets)...")
    lookup_table = create_lookup_table_relative(dialogues)
    print(f"  Table size: {len(lookup_table)} bytes")
    print(f"  Will be stored at chunk offset 0x{LOOKUP_TABLE_OFFSET:05X}")

    # Generate trampoline
    print("\nGenerating trampoline code...")
    trampoline = create_chunk_trampoline(ORIGINAL_HANDLER)
    print(f"  Trampoline size: {len(trampoline) * 4} bytes")
    print(f"  Location: RAM 0x{TRAMPOLINE_RAM:08X}")

    # Space check
    trampoline_size = len(trampoline) * 4
    available_scps = 668  # bytes available in SCPS_100.26
    available_chunk = 0x10000 - 0x800  # ~62KB in padding region

    print("\nSpace check:")
    print(f"  Trampoline: {trampoline_size} bytes (SCPS_100.26)")
    print(f"    Available: {available_scps} bytes")
    print(f"    Status: {'OK' if trampoline_size <= available_scps else 'OVERFLOW!'}")
    print(f"  Lookup table: {len(lookup_table)} bytes (STG chunk)")
    print(f"    Available: {available_chunk} bytes")
    print(f"    Status: {'OK' if len(lookup_table) <= available_chunk else 'OVERFLOW!'}")

    if trampoline_size > available_scps:
        print("\nERROR: Trampoline too large for SCPS_100.26!")
        return 1

    if len(lookup_table) > available_chunk:
        print("\nERROR: Lookup table too large for chunk padding!")
        return 1

    # Show disassembly
    disassemble_trampoline(trampoline, TRAMPOLINE_RAM)

    if args.test_only:
        print("\n[Test mode - not writing files]")
        return 0

    # Patch SCPS_100.26
    print("\n" + "=" * 60)
    print("Patching SCPS_100.26...")
    scps_patched = bytearray(scps_data)

    # Write trampoline
    for i, instr in enumerate(trampoline):
        offset = TRAMPOLINE_FILE + i * 4
        struct.pack_into('<I', scps_patched, offset, instr)
    print(f"  Wrote trampoline at 0x{TRAMPOLINE_FILE:06X}")

    # Update jump table entry 5
    struct.pack_into('<I', scps_patched, JUMP_TABLE_ENTRY5, TRAMPOLINE_RAM)
    print(f"  Updated jump table entry 5 -> 0x{TRAMPOLINE_RAM:08X}")

    # Patch STG chunk
    print("\nPatching S100.STG chunk 0...")
    stg_patched = bytearray(stg_data)

    # Write lookup table to chunk 0
    table_offset = LOOKUP_TABLE_OFFSET
    stg_patched[table_offset:table_offset + len(lookup_table)] = lookup_table
    print(f"  Wrote lookup table at chunk offset 0x{table_offset:05X}")

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    scps_out = os.path.join(OUTPUT_DIR, "SCPS_100.26")
    with open(scps_out, "wb") as f:
        f.write(scps_patched)
    print(f"\nSaved: {scps_out}")

    stg_out = os.path.join(OUTPUT_DIR, "S100.STG")
    with open(stg_out, "wb") as f:
        f.write(stg_patched)
    print(f"Saved: {stg_out}")

    print()
    print("=" * 60)
    print("IMPORTANT NOTES")
    print("=" * 60)
    print("""
The lookup table contains RELATIVE offsets from text region start.
The trampoline calculates the actual TextPtr by:
1. Masking current TextPtr to get approximate chunk base
2. Adding table offset to find the table
3. Looking up the relative offset
4. Converting to absolute address

KNOWN ISSUE: The chunk base calculation assumes 1MB alignment.
This may not work if chunks load at arbitrary addresses.

To fix this, we need to either:
1. Find where the game stores chunk base address
2. Use a different calculation based on actual memory layout
3. Store absolute addresses and determine chunk load address

TESTING:
1. Copy patched files to your game image
2. Load in emulator (DuckStation with debugging)
3. Set breakpoint at 0x80199654 (trampoline start)
4. Check if it correctly calculates table address
5. Watch dialogue behavior
""")

    return 0


if __name__ == "__main__":
    exit(main())
