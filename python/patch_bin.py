#!/usr/bin/env python3
"""
Patch PS1 BIN disc image with Korean translation files.

This script patches the game files directly within a PS1 BIN image,
recalculating EDC/ECC checksums for each modified sector.

Usage:
    python patch_bin.py /path/to/game.bin
    python patch_bin.py /path/to/game.bin --dry-run
    python patch_bin.py /path/to/game.bin --backup
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

# === Paths ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "..")
PATCHED_DIR = os.path.join(BASE_DIR, "output", "patched")

# === PS1 CD-ROM Constants ===
SECTOR_SIZE = 2352
SYNC_PATTERN = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])
DATA_OFFSET = 24      # Mode 2 Form 1: sync(12) + header(4) + subheader(8)
DATA_SIZE = 2048      # User data per sector
EDC_OFFSET = 2072     # Error Detection Code offset
ECC_OFFSET = 2076     # Error Correction Code offset

# === EDC/ECC Lookup Tables ===
# Pre-computed tables for EDC and ECC calculation
_edc_table = None
_ecc_f_table = None
_ecc_b_table = None


def _init_edc_table():
    """Initialize EDC lookup table."""
    global _edc_table
    if _edc_table is not None:
        return

    _edc_table = []
    for i in range(256):
        edc = i
        for _ in range(8):
            if edc & 1:
                edc = (edc >> 1) ^ 0xD8018001
            else:
                edc = edc >> 1
        _edc_table.append(edc)


def _init_ecc_tables():
    """Initialize ECC lookup tables."""
    global _ecc_f_table, _ecc_b_table
    if _ecc_f_table is not None:
        return

    _ecc_f_table = []
    _ecc_b_table = []

    for i in range(256):
        j = (i << 1) ^ (0x11D if i & 0x80 else 0)
        _ecc_f_table.append(j & 0xFF)
        j = i
        j = ((j >> 1) ^ (0x8E if j & 1 else 0)) & 0xFF
        j = ((j >> 1) ^ (0x8E if j & 1 else 0)) & 0xFF
        _ecc_b_table.append(j)


def compute_edc(data):
    """Compute EDC (Error Detection Code) for sector data."""
    _init_edc_table()
    edc = 0
    for byte in data:
        edc = _edc_table[(edc ^ byte) & 0xFF] ^ (edc >> 8)
    return edc


def compute_ecc(data, major_count, minor_count, major_mult, minor_inc):
    """Compute ECC (Error Correction Code) P or Q parity."""
    _init_ecc_tables()

    ecc = bytearray(major_count * 2)
    size = major_count * minor_count

    for major in range(major_count):
        idx = (major >> 1) * major_mult + (major & 1)
        ecc_a = 0
        ecc_b = 0

        for _ in range(minor_count):
            if idx < len(data):
                val = data[idx]
            else:
                val = 0
            idx += minor_inc
            if idx >= size:
                idx -= size

            ecc_a = _ecc_f_table[ecc_a] ^ val
            ecc_b = _ecc_f_table[ecc_b ^ val]

        ecc_a = _ecc_b_table[_ecc_f_table[ecc_a] ^ ecc_b]
        ecc[major] = ecc_a
        ecc[major + major_count] = ecc_a ^ ecc_b

    return bytes(ecc)


def rebuild_sector(sector_data, user_data):
    """Rebuild a Mode 2 Form 1 sector with new user data, recalculating EDC/ECC.

    Mode 2 Form 1 sector layout (2352 bytes):
    - Bytes 0-11: Sync pattern
    - Bytes 12-15: Header (min, sec, sector, mode)
    - Bytes 16-23: Subheader (file, channel, submode, coding) x2
    - Bytes 24-2071: User data (2048 bytes)
    - Bytes 2072-2075: EDC (4 bytes)
    - Bytes 2076-2351: ECC (276 bytes = P-parity 172 + Q-parity 104)
    """
    new_sector = bytearray(sector_data)

    # Copy new user data
    new_sector[DATA_OFFSET:DATA_OFFSET + DATA_SIZE] = user_data

    # Compute EDC over subheader + user data (bytes 16-2071)
    edc_data = bytes(new_sector[16:2072])
    edc = compute_edc(edc_data)
    new_sector[2072:2076] = edc.to_bytes(4, 'little')

    # Compute ECC P-parity (172 bytes)
    # P-parity covers address + data + EDC (bytes 12-2075)
    ecc_data = bytes(new_sector[12:2076])
    ecc_p = compute_ecc(ecc_data, 86, 24, 2, 86)
    new_sector[2076:2076 + 172] = ecc_p

    # Compute ECC Q-parity (104 bytes)
    # Q-parity covers address + data + EDC + P-parity (bytes 12-2247)
    ecc_data = bytes(new_sector[12:2248])
    ecc_q = compute_ecc(ecc_data, 52, 43, 86, 88)
    new_sector[2248:2352] = ecc_q

    return bytes(new_sector)


def read_sector(f, lba):
    """Read a full sector from BIN file."""
    f.seek(lba * SECTOR_SIZE)
    return f.read(SECTOR_SIZE)


def read_sector_data(f, lba):
    """Read user data from a sector."""
    f.seek(lba * SECTOR_SIZE + DATA_OFFSET)
    return f.read(DATA_SIZE)


def find_file_in_iso(f, filename):
    """Find a file in the ISO 9660 filesystem.

    Returns: dict with 'lba', 'size', 'sectors' or None if not found
    """
    # Read Primary Volume Descriptor (sector 16)
    pvd = read_sector_data(f, 16)

    # Verify PVD
    if pvd[0:1] != b'\x01' or pvd[1:6] != b'CD001':
        return None

    # Get root directory location
    root_lba = int.from_bytes(pvd[158:162], 'little')
    root_size = int.from_bytes(pvd[166:170], 'little')

    # Read root directory
    root_data = bytearray()
    sectors_to_read = (root_size + DATA_SIZE - 1) // DATA_SIZE
    for i in range(sectors_to_read):
        root_data.extend(read_sector_data(f, root_lba + i))

    # Parse directory entries
    offset = 0
    while offset < root_size:
        record_len = root_data[offset]
        if record_len == 0:
            offset = ((offset // DATA_SIZE) + 1) * DATA_SIZE
            if offset >= root_size:
                break
            continue

        file_lba = int.from_bytes(root_data[offset + 2:offset + 6], 'little')
        file_size = int.from_bytes(root_data[offset + 10:offset + 14], 'little')
        name_len = root_data[offset + 32]

        if name_len > 0 and offset + 33 + name_len <= len(root_data):
            try:
                name = root_data[offset + 33:offset + 33 + name_len].decode('ascii')
                if ';' in name:
                    name = name.split(';')[0]

                if name.upper() == filename.upper():
                    return {
                        'lba': file_lba,
                        'size': file_size,
                        'sectors': (file_size + DATA_SIZE - 1) // DATA_SIZE
                    }
            except:
                pass

        offset += record_len

    return None


def patch_file_in_bin(bin_path, filename, patch_data, dry_run=False):
    """Patch a file within the BIN image.

    Returns: (success, message)
    """
    with open(bin_path, 'r+b' if not dry_run else 'rb') as f:
        # Find file in ISO
        file_info = find_file_in_iso(f, filename)
        if not file_info:
            return False, f"File not found in ISO: {filename}"

        # Check size compatibility
        original_size = file_info['size']
        patch_size = len(patch_data)

        if patch_size > original_size:
            return False, f"Patch too large: {patch_size} > {original_size} bytes"

        # Pad patch data if smaller
        if patch_size < original_size:
            patch_data = patch_data + b'\x00' * (original_size - patch_size)

        # Patch sectors
        lba = file_info['lba']
        sectors = file_info['sectors']

        for i in range(sectors):
            sector_lba = lba + i
            data_start = i * DATA_SIZE
            data_end = min(data_start + DATA_SIZE, len(patch_data))
            user_data = patch_data[data_start:data_end]

            # Pad last sector if needed
            if len(user_data) < DATA_SIZE:
                user_data = user_data + b'\x00' * (DATA_SIZE - len(user_data))

            if not dry_run:
                # Read original sector
                original_sector = read_sector(f, sector_lba)

                # Rebuild sector with new data
                new_sector = rebuild_sector(original_sector, user_data)

                # Write patched sector
                f.seek(sector_lba * SECTOR_SIZE)
                f.write(new_sector)

        return True, f"Patched {sectors} sectors at LBA {lba}"


def get_patched_files():
    """Get list of patchable files."""
    if not os.path.exists(PATCHED_DIR):
        return {}

    files = {}
    for filename in os.listdir(PATCHED_DIR):
        filepath = os.path.join(PATCHED_DIR, filename)
        if os.path.isfile(filepath):
            # Skip non-game files
            if filename.endswith(('.txt', '.png', '.md')):
                continue
            # Skip system files
            if filename.startswith('.'):
                continue
            # Skip directories
            if os.path.isdir(filepath):
                continue
            # Skip BIN/CUE disc images and backups
            if filename.endswith(('.bin', '.cue', '.backup', '.bak')):
                continue
            if '.backup_' in filename:
                continue
            files[filename] = filepath

    return files


def find_backup(bin_path):
    """Find existing backup file for the given BIN path.

    Returns the backup path if found, None otherwise.
    """
    import glob
    backup_pattern = f"{bin_path}.backup_*"
    backups = sorted(glob.glob(backup_pattern))
    if backups:
        return backups[0]  # Return the oldest backup (original)
    return None


def ensure_backup_and_restore(bin_path, dry_run=False):
    """Ensure a backup exists and restore the BIN from it.

    If no backup exists, creates one from the current BIN.
    If backup exists, restores the BIN from the backup.

    Returns: (success, message)
    """
    backup_path = find_backup(bin_path)

    if backup_path:
        # Backup exists - restore from it
        if dry_run:
            return True, f"Would restore from: {os.path.basename(backup_path)}"
        print(f"Restoring from backup: {os.path.basename(backup_path)}")
        shutil.copy2(backup_path, bin_path)
        return True, f"Restored from: {os.path.basename(backup_path)}"
    else:
        # No backup - create one
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{bin_path}.backup_{timestamp}"
        if dry_run:
            return True, f"Would create backup: {os.path.basename(backup_path)}"
        print(f"Creating backup: {os.path.basename(backup_path)}")
        shutil.copy2(bin_path, backup_path)
        return True, f"Created backup: {os.path.basename(backup_path)}"


def main():
    parser = argparse.ArgumentParser(
        description="Patch PS1 BIN disc image with Korean translation"
    )
    parser.add_argument(
        "bin_file",
        help="Path to the PS1 BIN disc image"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="Don't restore from backup before patching (patch in place)"
    )
    args = parser.parse_args()

    bin_path = os.path.abspath(args.bin_file)

    print("=== Arc the Lad 2 BIN Patcher ===")
    print()

    # Check BIN file exists
    if not os.path.isfile(bin_path):
        print(f"ERROR: BIN file not found: {bin_path}")
        return 1

    # Get patched files
    patched_files = get_patched_files()
    if not patched_files:
        print("ERROR: No patched files found in output/patched/")
        print("       Run 'python patch_korean.py <stage> --system' first.")
        return 1

    print(f"BIN file: {bin_path}")
    print(f"Patched files: {len(patched_files)}")
    print()

    # Restore from backup (or create backup if none exists)
    if not args.no_restore:
        success, message = ensure_backup_and_restore(bin_path, args.dry_run)
        if success:
            print(f"  {message}")
        else:
            print(f"ERROR: {message}")
            return 1
        print()

    # Verify files exist in ISO
    print("Scanning ISO filesystem...")
    with open(bin_path, 'rb') as f:
        for filename in patched_files:
            info = find_file_in_iso(f, filename)
            if info:
                print(f"  {filename:<15} LBA: {info['lba']:>6}, Size: {info['size']:>10,} bytes")
            else:
                print(f"  {filename:<15} NOT FOUND in ISO")
    print()

    # Apply patches
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Applying patches...")

    applied = 0
    errors = 0

    for filename, filepath in sorted(patched_files.items()):
        with open(filepath, 'rb') as f:
            patch_data = f.read()

        success, message = patch_file_in_bin(bin_path, filename, patch_data, args.dry_run)

        if success:
            print(f"  OK: {filename} - {message}")
            applied += 1
        else:
            print(f"  ERROR: {filename} - {message}")
            errors += 1

    print()
    print("=== Summary ===")
    print(f"  Applied: {applied}")
    print(f"  Errors:  {errors}")

    if args.dry_run and applied > 0:
        print()
        print("Run without --dry-run to apply changes.")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
