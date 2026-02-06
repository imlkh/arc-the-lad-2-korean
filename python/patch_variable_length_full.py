#!/usr/bin/env python3
"""
Full Variable-Length Korean Translation Patcher

This script runs the complete workflow for variable-length Korean translations:
1. Run patch_all.py (Korean font + fixed-length text)
2. Run patch_variable_length_multi.py (per-chunk VLUTs + Korean text)
3. Run apply_hook.py --variable-length-multi (trampoline with master pointer)
4. Run patch_bin.py (apply to disc image)

Usage:
    python patch_variable_length_full.py [DISC_IMAGE]

Example:
    python patch_variable_length_full.py "output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin"
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)


def run_script(script_name, args=None):
    """Run a Python script and check for errors."""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"\nERROR: {script_name} failed with return code {result.returncode}")
        return False
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Full variable-length Korean translation patcher"
    )
    parser.add_argument("disc_image", nargs="?",
                        default="output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin",
                        help="Path to disc image (default: output/patched/...)")
    parser.add_argument("--stg", default="S100",
                        help="STG file to patch (default: S100)")
    parser.add_argument("--skip-patch-all", action="store_true",
                        help="Skip patch_all.py (if already run)")
    args = parser.parse_args()

    print("="*60)
    print("Variable-Length Korean Translation - Full Workflow")
    print("="*60)
    print(f"STG file: {args.stg}")
    print(f"Disc image: {args.disc_image}")

    # Step 1: patch_all.py
    if not args.skip_patch_all:
        if not run_script("patch_all.py"):
            return 1
    else:
        print("\n[Skipping patch_all.py]")

    # Step 2: patch_variable_length_multi.py
    if not run_script("patch_variable_length_multi.py", [args.stg]):
        return 1

    # Step 3: apply_hook.py --variable-length-multi
    if not run_script("apply_hook.py", ["--variable-length-multi"]):
        return 1

    # Step 4: patch_bin.py
    if not run_script("patch_bin.py", [args.disc_image]):
        return 1

    print("\n" + "="*60)
    print("SUCCESS: Variable-length patching complete!")
    print("="*60)
    print(f"\nPatched disc image: {args.disc_image}")
    print("\nThe game is ready to test.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
