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


README_TEMPLATE = """\
================================================================
 아크 더 래드 II 한국어 패치 {version}
 Arc the Lad II Korean Translation Patch {version}
================================================================

■ 필요한 원본 (직접 덤프한 이미지를 사용하세요)
   게임    : Arc the Lad II (Japan) (Rev 1)
             (PlayStation the Best판, SCPS-91071 / SCPS-91310)
   크기    : 739,144,224 바이트
   MD5     : 012B023097777CB6CE6A5DE5E0457022
   ※ 초판(v1.0, SCPS-10026)은 지원하지 않습니다.
      MD5가 다르면 패치가 적용되지 않습니다.

■ 패치 방법 1 — 웹 브라우저 (설치 불필요)
   1. https://www.marcrobledo.com/RomPatcher.js/ 접속
   2. "ROM file"에 원본 BIN 파일 선택
   3. "Patch file"에 {patch_name} 선택
   4. "Apply patch"를 누르고 결과 파일 다운로드
   5. 파일 이름을 "Arc the Lad II (Korean Patch).bin"으로 변경
   6. 동봉된 .cue 파일과 같은 폴더에 두고,
      에뮬레이터에서 .cue 파일을 실행

■ 패치 방법 2 — Delta Patcher (Windows / macOS / Linux)
   1. https://github.com/marco-calautti/DeltaPatcher/releases
      에서 다운로드
   2. 원본 BIN을 미리 복사해 두세요 (원본이 직접 수정됩니다)
   3. "Original file"에 복사본 BIN, "XDelta patch"에
      {patch_name} 선택 후 "Apply patch"
   4. 복사본 이름을 "Arc the Lad II (Korean Patch).bin"으로
      변경하고, 동봉된 .cue와 같은 폴더에서 사용

----------------------------------------------------------------

* Required source (use your own dump)
   Game : Arc the Lad II (Japan) (Rev 1)
          (PlayStation the Best, SCPS-91071 / SCPS-91310)
   Size : 739,144,224 bytes
   MD5  : 012B023097777CB6CE6A5DE5E0457022
   The original v1.0 release (SCPS-10026) is NOT supported;
   the patch will refuse to apply if the MD5 differs.

* How to apply
   Browser (no install): open
   https://www.marcrobledo.com/RomPatcher.js/ , choose your BIN as
   "ROM file" and {patch_name} as "Patch file", apply, then rename
   the result to "Arc the Lad II (Korean Patch).bin" and keep it
   next to the bundled .cue file.

   Delta Patcher (Windows/macOS/Linux):
   https://github.com/marco-calautti/DeltaPatcher/releases
   Patch a COPY of your BIN (it is modified in place), rename it to
   "Arc the Lad II (Korean Patch).bin", and use the bundled .cue.

* Project: https://github.com/imlkh/arc-the-lad-2-korean
"""


def get_version():
    """Release version from git tags, e.g. v0.1.0-beta or v0.1.0-beta-5-gabc123."""
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=BASE_DIR, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unversioned"


def write_readme(out_dir, version, patch_name):
    with open(os.path.join(out_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README_TEMPLATE.format(version=version, patch_name=patch_name))


def write_sha256sums(out_dir, filenames):
    lines = [f"{sha256_file(os.path.join(out_dir, name))}  {name}"
             for name in filenames]
    with open(os.path.join(out_dir, "SHA256SUMS.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a verified xdelta release package "
                    "for the Korean translation.")
    parser.add_argument("--original", default=DEFAULT_ORIGINAL,
                        help="pristine Japanese BIN (redump Rev 1)")
    parser.add_argument("--patched", default=DEFAULT_PATCHED,
                        help="Korean-patched BIN")
    parser.add_argument("--cue", default=DEFAULT_CUE,
                        help="cue sheet to bundle")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR,
                        help="release output root")
    parser.add_argument("--expected-md5", default=REDUMP_MD5,
                        help="required MD5 of --original")
    parser.add_argument("--expected-size", type=int, default=REDUMP_SIZE,
                        help="required size of --original in bytes")
    args = parser.parse_args(argv)

    check_xdelta3()
    print(f"Verifying source: {args.original}")
    verify_source(args.original, args.expected_md5, args.expected_size)

    version = get_version()
    out_dir = os.path.join(args.out, version)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)  # rebuilds must not inherit stale artifacts
    os.makedirs(out_dir)
    patch_name = f"arc-the-lad-2-korean-{version}.xdelta"
    patch_path = os.path.join(out_dir, patch_name)

    print(f"Building patch: {patch_path}")
    build_patch(args.original, args.patched, patch_path)

    print("Verifying round-trip (patch original -> must equal Korean BIN)")
    verify_patch(args.original, patch_path, md5_file(args.patched))

    cue_name = "Arc the Lad II (Korean Patch).cue"
    shutil.copyfile(args.cue, os.path.join(out_dir, cue_name))
    write_readme(out_dir, version, patch_name)
    write_sha256sums(out_dir, [patch_name, cue_name])

    print(f"OK: release package at {out_dir}")


if __name__ == "__main__":
    main()
