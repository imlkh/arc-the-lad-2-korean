#!/usr/bin/env python3
"""
Apply passthrough hook to an existing SCPS_100.26 file.

This applies the hook to the already-patched SCPS_100.26 (with Korean text)
so we can test the hook mechanism without losing the Korean patches.

Usage:
    python apply_hook.py [--lookup]

    Default: Apply passthrough hook (just calls original handler)
    --lookup: Apply full lookup table trampoline
"""

import os
import struct
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)  # python/
BASE_DIR = os.path.dirname(PYTHON_DIR)    # atl2_korean_translation/
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "patched")

# Target file
SCPS_PATH = os.path.join(OUTPUT_DIR, "SCPS_100.26")

# Addresses
JUMP_TABLE_FILE = 0x0C2F60
JUMP_TABLE_ENTRY5 = JUMP_TABLE_FILE + 5 * 4
ORIGINAL_HANDLER = 0x80101560
TRAMPOLINE_FILE = 0x0D8A54
TRAMPOLINE_RAM = 0x80199654


def create_passthrough_trampoline():
    """Minimal trampoline that just calls the original handler."""
    code = []
    code.append(0x27BDFFF8)  # addiu $sp, $sp, -8
    code.append(0xAFBF0004)  # sw $ra, 4($sp)
    jal_target = (ORIGINAL_HANDLER >> 2) & 0x03FFFFFF
    code.append(0x0C000000 | jal_target)  # jal ORIGINAL_HANDLER
    code.append(0x00000000)  # nop
    code.append(0x8FBF0004)  # lw $ra, 4($sp)
    code.append(0x27BD0008)  # addiu $sp, $sp, 8
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop
    return code


def create_lookup_trampoline(variable_length=False, multi_chunk=False):
    """
    Full lookup table trampoline.

    Args:
        variable_length: If True, offsets are relative to chunk start.
                        If False, offsets are relative to text region start.
        multi_chunk: If True, read VLUT offset from master pointer at 0xAFF00.
                    This allows each chunk to have VLUT at different offset.
    """
    LOOKUP_TABLE_OFFSET = 0xA0800
    MASTER_PTR_OFFSET = 0xAFF00
    TEXT_REGION_OFFSET = 0xB4000

    code = []

    # Function prologue
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

    if multi_chunk:
        # Multi-chunk mode: read VLUT offset from master pointer at 0xAFF00
        # $t0 = chunk_base + 0xAFF00
        code.append(0x3C08000A)  # lui $t0, 0x000A
        code.append(0x3508FF00)  # ori $t0, $t0, 0xFF00
        code.append(0x00484021)  # addu $t0, $v0, $t0
        # Load VLUT offset from master pointer
        code.append(0x8D080000)  # lw $t0, 0($t0)  -> $t0 = VLUT offset
        # Calculate table address: chunk_base + VLUT offset
        code.append(0x01484021)  # addu $t0, $t2, $t0
    else:
        # Single-chunk mode: fixed VLUT offset 0xA0800
        # Calculate table address: chunk_base + 0xA0800
        code.append(0x3C08000A)  # lui $t0, 0x000A
        code.append(0x35080800)  # ori $t0, $t0, 0x0800
        code.append(0x00484021)  # addu $t0, $v0, $t0

    # Check magic "VLUT" = 0x54554C56
    code.append(0x8D020000)  # lw $v0, 0($t0)
    code.append(0x3C035455)  # lui $v1, 0x5455
    code.append(0x34634C56)  # ori $v1, $v1, 0x4C56

    # Branch offsets calculated from instruction index to fallback:
    # Fixed-length: fallback at index 40
    #   Branch 1 at index 14: offset = 40 - 15 = 25 (0x19)
    #   Branch 2 at index 20: offset = 40 - 21 = 19 (0x13)
    #   Branch 3 at index 25: offset = 40 - 26 = 14 (0x0E)
    # Variable-length: fallback at index 36 (4 fewer instructions)
    #   Branch 1 at index 14: offset = 36 - 15 = 21 (0x15)
    #   Branch 2 at index 20: offset = 36 - 21 = 15 (0x0F)
    #   Branch 3 at index 25: offset = 36 - 26 = 10 (0x0A)

    if variable_length:
        code.append(0x14430015)  # bne $v0, $v1, fallback (21 instructions)
    else:
        code.append(0x14430019)  # bne $v0, $v1, fallback (25 instructions)
    code.append(0x00000000)  # nop

    # Load entry count
    code.append(0x8D020004)  # lw $v0, 4($t0)

    # Load SeqIndex
    code.append(0x8FA40010)  # lw $a0, 16($sp)
    code.append(0x9483009A)  # lhu $v1, 0x9A($a0)

    # Check bounds
    code.append(0x0062082A)  # slt $at, $v1, $v0

    if variable_length:
        code.append(0x1020000F)  # beq $at, $zero, fallback (15 instructions)
    else:
        code.append(0x10200013)  # beq $at, $zero, fallback (19 instructions)
    code.append(0x00000000)  # nop

    # Calculate entry address
    code.append(0x00031880)  # sll $v1, $v1, 2
    code.append(0x01034021)  # addu $t0, $t0, $v1
    code.append(0x8D090008)  # lw $t1, 8($t0)

    # Check if offset valid
    if variable_length:
        code.append(0x1120000A)  # beq $t1, $zero, fallback (10 instructions)
    else:
        code.append(0x1120000E)  # beq $t1, $zero, fallback (14 instructions)
    code.append(0x00000000)  # nop

    if variable_length:
        # Variable-length: offset is relative to chunk start
        # new_ptr = chunk_base + offset
        code.append(0x01494821)  # addu $t1, $t2, $t1
    else:
        # Fixed-length: offset is relative to text region start
        # new_ptr = chunk_base + TEXT_REGION_OFFSET + offset
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

    # Fallback: call original handler
    code.append(0x8FA40010)  # lw $a0, 16($sp)
    jal_target = (ORIGINAL_HANDLER >> 2) & 0x03FFFFFF
    code.append(0x0C000000 | jal_target)
    code.append(0x00000000)  # nop

    code.append(0x8FAA000C)  # lw $t2, 12($sp)
    code.append(0x8FBF0014)  # lw $ra, 20($sp)
    code.append(0x27BD0018)  # addiu $sp, $sp, 24
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop

    return code


def main():
    parser = argparse.ArgumentParser(description="Apply hook to SCPS_100.26")
    parser.add_argument("--lookup", action="store_true",
                        help="Apply lookup table trampoline (fixed-length offsets)")
    parser.add_argument("--variable-length", action="store_true",
                        help="Apply variable-length trampoline (offsets from chunk start, single chunk)")
    parser.add_argument("--variable-length-multi", action="store_true",
                        help="Apply variable-length trampoline with per-chunk VLUT offsets")
    args = parser.parse_args()

    print("=== Apply Hook to Patched SCPS_100.26 ===")
    print()

    if not os.path.exists(SCPS_PATH):
        print(f"ERROR: {SCPS_PATH} not found!")
        print("       Run 'python patch_all.py' first.")
        return 1

    # Read file
    print(f"Loading {SCPS_PATH}...")
    with open(SCPS_PATH, "rb") as f:
        data = bytearray(f.read())

    # Generate trampoline
    if args.variable_length_multi:
        print("Generating VARIABLE-LENGTH MULTI-CHUNK trampoline...")
        trampoline = create_lookup_trampoline(variable_length=True, multi_chunk=True)
    elif args.variable_length:
        print("Generating VARIABLE-LENGTH trampoline...")
        trampoline = create_lookup_trampoline(variable_length=True, multi_chunk=False)
    elif args.lookup:
        print("Generating LOOKUP TABLE trampoline (fixed-length)...")
        trampoline = create_lookup_trampoline(variable_length=False, multi_chunk=False)
    else:
        print("Generating PASSTHROUGH trampoline...")
        trampoline = create_passthrough_trampoline()

    print(f"  Trampoline size: {len(trampoline) * 4} bytes")

    # Write trampoline
    print(f"\nWriting trampoline at 0x{TRAMPOLINE_FILE:06X}...")
    for i, instr in enumerate(trampoline):
        offset = TRAMPOLINE_FILE + i * 4
        struct.pack_into('<I', data, offset, instr)

    # Update jump table entry
    old_entry = struct.unpack_from('<I', data, JUMP_TABLE_ENTRY5)[0]
    print(f"Updating jump table entry 5:")
    print(f"  Old: 0x{old_entry:08X}")
    print(f"  New: 0x{TRAMPOLINE_RAM:08X}")
    struct.pack_into('<I', data, JUMP_TABLE_ENTRY5, TRAMPOLINE_RAM)

    # Save
    with open(SCPS_PATH, "wb") as f:
        f.write(data)

    print(f"\nSaved: {SCPS_PATH}")
    print()

    if args.variable_length_multi:
        print("Hook type: VARIABLE-LENGTH MULTI-CHUNK LOOKUP TABLE")
        print("  - Reads VLUT offset from master pointer at 0xAFF00")
        print("  - Each chunk can have VLUT at different offset")
        print("  - Offsets are relative to CHUNK START")
        print("  - Korean text in padding region after each chunk's VLUT")
        print("  - Falls back to original handler if master pointer is 0")
    elif args.variable_length:
        print("Hook type: VARIABLE-LENGTH LOOKUP TABLE (single chunk)")
        print("  - Reads dialogue offsets from VLUT table in STG chunks")
        print("  - Offsets are relative to CHUNK START (not text region)")
        print("  - Korean text relocated to padding region (0xA2000+)")
        print("  - Falls back to original handler if table not found")
    elif args.lookup:
        print("Hook type: FIXED-LENGTH LOOKUP TABLE")
        print("  - Reads dialogue offsets from VLUT table in STG chunks")
        print("  - Offsets are relative to text region start")
        print("  - Falls back to original handler if table not found")
    else:
        print("Hook type: PASSTHROUGH")
        print("  - Just calls original handler (no behavior change)")
        print("  - Use this to verify hook mechanism works")

    print()
    print("Next step: Run patch_bin.py to apply to disc image")

    return 0


if __name__ == "__main__":
    exit(main())
