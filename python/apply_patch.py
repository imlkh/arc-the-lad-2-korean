#!/usr/bin/env python3
"""
Apply patched Korean files to the game folder.

This script copies all patched files from output/patched/ to the specified
game folder, replacing the original files.

Usage:
    python apply_patch.py /path/to/game/folder
    python apply_patch.py /path/to/game/folder --dry-run
    python apply_patch.py /path/to/game/folder --backup
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


def get_patched_files():
    """Get list of patched files to apply."""
    if not os.path.exists(PATCHED_DIR):
        return []

    files = []
    for filename in os.listdir(PATCHED_DIR):
        filepath = os.path.join(PATCHED_DIR, filename)
        if os.path.isfile(filepath):
            # Skip non-game files (charmap, preview images, etc.)
            if filename.endswith(('.txt', '.png', '.md')):
                continue
            files.append(filename)

    return sorted(files)


def apply_patch(dest_folder, dry_run=False, backup=False):
    """Apply patched files to destination folder.

    Args:
        dest_folder: Path to the game folder
        dry_run: If True, only show what would be done
        backup: If True, create backups of original files

    Returns:
        Tuple of (applied_count, skipped_count, error_count)
    """
    if not os.path.isdir(dest_folder):
        print(f"ERROR: Destination folder does not exist: {dest_folder}")
        return 0, 0, 1

    patched_files = get_patched_files()

    if not patched_files:
        print("ERROR: No patched files found in output/patched/")
        print(f"       Run 'python patch_korean.py <stage> --system' first.")
        return 0, 0, 1

    print(f"{'[DRY RUN] ' if dry_run else ''}Applying patches to: {dest_folder}")
    print(f"Source: {PATCHED_DIR}")
    print()

    applied = 0
    skipped = 0
    errors = 0

    # Create backup folder if needed
    backup_dir = None
    if backup and not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(dest_folder, f"backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        print(f"Backup folder: {backup_dir}")
        print()

    for filename in patched_files:
        src_path = os.path.join(PATCHED_DIR, filename)
        dst_path = os.path.join(dest_folder, filename)

        src_size = os.path.getsize(src_path)
        dst_exists = os.path.exists(dst_path)
        dst_size = os.path.getsize(dst_path) if dst_exists else 0

        # Check if destination file exists
        if not dst_exists:
            print(f"  SKIP: {filename} (not found in destination)")
            skipped += 1
            continue

        # Check if files are different
        if src_size == dst_size:
            with open(src_path, 'rb') as f1, open(dst_path, 'rb') as f2:
                if f1.read() == f2.read():
                    print(f"  SKIP: {filename} (already patched)")
                    skipped += 1
                    continue

        # Backup original file
        if backup and backup_dir and not dry_run:
            backup_path = os.path.join(backup_dir, filename)
            try:
                shutil.copy2(dst_path, backup_path)
            except Exception as e:
                print(f"  ERROR: {filename} (backup failed: {e})")
                errors += 1
                continue

        # Apply patch
        if dry_run:
            print(f"  APPLY: {filename} ({src_size:,} bytes)")
            applied += 1
        else:
            try:
                shutil.copy2(src_path, dst_path)
                print(f"  APPLY: {filename} ({src_size:,} bytes)")
                applied += 1
            except Exception as e:
                print(f"  ERROR: {filename} ({e})")
                errors += 1

    return applied, skipped, errors


def main():
    parser = argparse.ArgumentParser(
        description="Apply patched Korean files to the game folder"
    )
    parser.add_argument(
        "dest_folder",
        help="Path to the game folder containing original files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup of original files before patching"
    )
    args = parser.parse_args()

    # Normalize path
    dest_folder = os.path.abspath(args.dest_folder)

    print("=== Arc the Lad 2 Patch Applicator ===")
    print()

    applied, skipped, errors = apply_patch(
        dest_folder,
        dry_run=args.dry_run,
        backup=args.backup
    )

    print()
    print(f"=== Summary ===")
    print(f"  Applied: {applied}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")

    if args.dry_run and applied > 0:
        print()
        print("Run without --dry-run to apply changes.")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
