#!/usr/bin/env python3
"""
Build a verified xdelta release package for the Korean translation.

Verifies the original BIN is the pristine redump "Arc the Lad II (Japan)
(Rev 1)" dump, builds an xdelta3 patch to the Korean BIN, round-trip
verifies it byte-for-byte, and packages patch + cue + README + checksums
into output/release/<version>/.

Usage:
    python make_release_patch.py
    python make_release_patch.py --original PATH --patched PATH --out DIR

Requires xdelta3 on PATH (brew install xdelta / apt install xdelta3).
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

# === Paths (same convention as patch_bin.py) ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)   # python/
BASE_DIR = os.path.dirname(PYTHON_DIR)     # atl2_korean_translation/
PATCHED_DIR = os.path.join(BASE_DIR, "output", "patched")

DEFAULT_ORIGINAL = os.path.join(
    PATCHED_DIR, "Arc the Lad II (Japan).bin.backup_20260206_001549.bin")
DEFAULT_PATCHED = os.path.join(
    PATCHED_DIR, "Arc the Lad II (Korean Patch)",
    "Arc the Lad II (Korean Patch).bin")
DEFAULT_CUE = os.path.join(
    PATCHED_DIR, "Arc the Lad II (Korean Patch)",
    "Arc the Lad II (Korean Patch).cue")
DEFAULT_OUT_DIR = os.path.join(BASE_DIR, "output", "release")

# === redump.org reference: the only supported source dump ===
REDUMP_TITLE = "Arc the Lad II (Japan) (Rev 1)"          # SCPS-91071/91310
REDUMP_MD5 = "012b023097777cb6ce6a5de5e0457022"
REDUMP_SIZE = 739144224

_CHUNK = 8 * 1024 * 1024


def _hash_file(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while True:
            block = f.read(_CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def md5_file(path):
    return _hash_file(path, "md5")


def sha256_file(path):
    return _hash_file(path, "sha256")


def verify_source(path, expected_md5=REDUMP_MD5, expected_size=REDUMP_SIZE):
    """Hard-fail unless `path` is the pristine source dump."""
    size = os.path.getsize(path)
    if size != expected_size:
        sys.exit(
            f"ERROR: source size mismatch: {size:,} bytes "
            f"(expected {expected_size:,}).\n"
            f'The source must be a pristine redump dump of "{REDUMP_TITLE}".')
    actual = md5_file(path)
    if actual != expected_md5.lower():
        sys.exit(
            f"ERROR: source MD5 mismatch:\n"
            f"  expected {expected_md5} ({REDUMP_TITLE})\n"
            f"  actual   {actual}\n"
            f"A release patch is never built from a modified source.")


def check_xdelta3():
    """Return the xdelta3 executable path, or exit with an install hint."""
    path = shutil.which("xdelta3")
    if not path:
        sys.exit("ERROR: xdelta3 not found on PATH.\n"
                 "Install it with: brew install xdelta   (macOS)\n"
                 "             or: apt install xdelta3   (Debian/Ubuntu)")
    return path


def build_patch(original, patched, patch_path):
    """Encode original -> patched as an xdelta (VCDIFF) patch."""
    subprocess.run(
        ["xdelta3", "-e", "-9", "-S", "lzma", "-f",
         "-s", original, patched, patch_path],
        check=True)


def verify_patch(original, patch_path, expected_md5):
    """Apply the patch to the original and require a byte-exact result.

    On any failure the patch file is deleted: an unverified patch is
    never shipped. The temp output is always deleted.
    """
    fd, tmp = tempfile.mkstemp(suffix=".bin",
                               dir=os.path.dirname(patch_path) or ".")
    os.close(fd)
    try:
        try:
            subprocess.run(
                ["xdelta3", "-d", "-f", "-s", original, patch_path, tmp],
                check=True)
        except subprocess.CalledProcessError:
            os.remove(patch_path)
            sys.exit("ERROR: round-trip failed: xdelta3 could not apply "
                     "the patch it just built. Patch deleted.")
        actual = md5_file(tmp)
        if actual != expected_md5.lower():
            os.remove(patch_path)
            sys.exit(
                f"ERROR: round-trip MD5 mismatch:\n"
                f"  expected {expected_md5}\n"
                f"  actual   {actual}\n"
                f"Patch deleted; never ship an unverified patch.")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == "__main__":
    sys.exit("Not runnable yet: CLI arrives in Task 3.")
