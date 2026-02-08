#!/usr/bin/env python3
"""
POC Step 1: Passthrough Hook Test

This script creates a minimal hook that:
1. Intercepts the text advance handler via jump table entry
2. Simply calls the original handler (passthrough)
3. Returns normally

PURPOSE: Verify our hook mechanism works without breaking the game.
If the game works normally with this patch, our hook point is correct.

Usage:
    python poc_hook_test.py

Then copy output/patched_vl/SCPS_100.26 to your game and test.
The game should work exactly as before (no visible changes).
"""

import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GAME_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "patched_vl")

SCPS_PATH = os.path.join(GAME_DIR, "SCPS_100.26")

# Addresses
JUMP_TABLE_FILE = 0x0C2F60  # Jump table at RAM 0x80183B60
JUMP_TABLE_ENTRY5 = JUMP_TABLE_FILE + 5 * 4  # Entry 5 = text advance handler
ORIGINAL_HANDLER = 0x80101560

# Trampoline location (668 bytes of zeros available)
TRAMPOLINE_FILE = 0x0D8A54
TRAMPOLINE_RAM = 0x80199654


def create_passthrough_trampoline():
    """
    Create a minimal trampoline that just calls the original handler.

    This is a PASSTHROUGH - it doesn't change any behavior.
    If the game works with this, our hook point is correct.

    MIPS code:
        ; Save return address
        addiu $sp, $sp, -8
        sw    $ra, 4($sp)

        ; Call original handler
        jal   ORIGINAL_HANDLER
        nop

        ; Restore and return
        lw    $ra, 4($sp)
        addiu $sp, $sp, 8
        jr    $ra
        nop
    """
    code = []

    # Function prologue
    code.append(0x27BDFFF8)  # addiu $sp, $sp, -8
    code.append(0xAFBF0004)  # sw $ra, 4($sp)

    # Call original handler (JAL instruction)
    # JAL target = (target >> 2) & 0x03FFFFFF
    jal_target = (ORIGINAL_HANDLER >> 2) & 0x03FFFFFF
    code.append(0x0C000000 | jal_target)  # jal ORIGINAL_HANDLER
    code.append(0x00000000)  # nop (delay slot)

    # Function epilogue
    code.append(0x8FBF0004)  # lw $ra, 4($sp)
    code.append(0x27BD0008)  # addiu $sp, $sp, 8
    code.append(0x03E00008)  # jr $ra
    code.append(0x00000000)  # nop (delay slot)

    return code


def patch_executable(scps_data):
    """Patch SCPS_100.26 with the passthrough trampoline."""
    data = bytearray(scps_data)

    # Generate trampoline
    trampoline = create_passthrough_trampoline()

    # Write trampoline to executable
    print(f"Writing trampoline at file offset 0x{TRAMPOLINE_FILE:06X} (RAM 0x{TRAMPOLINE_RAM:08X})")
    for i, instr in enumerate(trampoline):
        offset = TRAMPOLINE_FILE + i * 4
        struct.pack_into('<I', data, offset, instr)
    print(f"  Trampoline size: {len(trampoline) * 4} bytes")

    # Update jump table entry 5 to point to trampoline
    old_entry = struct.unpack_from('<I', data, JUMP_TABLE_ENTRY5)[0]
    print(f"\nUpdating jump table entry 5:")
    print(f"  Old: 0x{old_entry:08X}")
    print(f"  New: 0x{TRAMPOLINE_RAM:08X}")
    struct.pack_into('<I', data, JUMP_TABLE_ENTRY5, TRAMPOLINE_RAM)

    return bytes(data)


def disassemble_trampoline():
    """Print the trampoline code for verification."""
    code = create_passthrough_trampoline()

    print("\n=== Trampoline Disassembly ===\n")

    mnemonics = [
        "addiu $sp, $sp, -8",
        "sw    $ra, 4($sp)",
        f"jal   0x{ORIGINAL_HANDLER:08X}",
        "nop",
        "lw    $ra, 4($sp)",
        "addiu $sp, $sp, 8",
        "jr    $ra",
        "nop"
    ]

    for i, (instr, mnem) in enumerate(zip(code, mnemonics)):
        addr = TRAMPOLINE_RAM + i * 4
        print(f"0x{addr:08X}: {instr:08X}  {mnem}")


def main():
    print("=" * 60)
    print("POC Step 1: Passthrough Hook Test")
    print("=" * 60)
    print()
    print("This creates a minimal hook that calls the original handler.")
    print("If the game works normally with this patch, our hook is correct.")
    print()

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load executable
    print(f"Loading {SCPS_PATH}...")
    with open(SCPS_PATH, "rb") as f:
        scps_data = f.read()
    print(f"  Size: {len(scps_data)} bytes")

    # Show trampoline
    disassemble_trampoline()

    # Patch
    print("\n=== Patching ===\n")
    patched = patch_executable(scps_data)

    # Verify patch
    print("\n=== Verification ===\n")

    # Check trampoline was written
    trampoline = create_passthrough_trampoline()
    for i, expected in enumerate(trampoline):
        offset = TRAMPOLINE_FILE + i * 4
        actual = struct.unpack_from('<I', patched, offset)[0]
        status = "OK" if actual == expected else "MISMATCH"
        print(f"  Trampoline[{i}]: expected 0x{expected:08X}, got 0x{actual:08X} [{status}]")

    # Check jump table entry
    entry = struct.unpack_from('<I', patched, JUMP_TABLE_ENTRY5)[0]
    status = "OK" if entry == TRAMPOLINE_RAM else "MISMATCH"
    print(f"  Jump table entry 5: 0x{entry:08X} [{status}]")

    # Save
    output_path = os.path.join(OUTPUT_DIR, "SCPS_100.26")
    print(f"\n=== Saving ===\n")
    with open(output_path, "wb") as f:
        f.write(patched)
    print(f"Saved: {output_path}")

    print()
    print("=" * 60)
    print("TESTING INSTRUCTIONS")
    print("=" * 60)
    print("""
1. Copy the patched SCPS_100.26 to your game image/directory
2. Load the game in an emulator (DuckStation recommended)
3. Play through some dialogue in S100 (Prodias opening)
4. If dialogue displays normally, the hook works!

The game should behave EXACTLY as before because our trampoline
just calls the original handler without any changes.

Once this works, we can add the lookup table logic.
""")


if __name__ == "__main__":
    main()
