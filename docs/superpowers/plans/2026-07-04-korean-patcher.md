# Korean Patch Release Builder (make_release_patch.py) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A script that builds a verified 16 MB xdelta release package so users patch their own original BIN instead of the project distributing the 739 MB Korean disc image.

**Architecture:** One standalone script `python/patch/make_release_patch.py` (same style as `patch_bin.py`: argparse, module-level path constants, stdlib only). It verifies the source BIN against the redump Rev 1 hash, shells out to `xdelta3` to build the patch, round-trip-verifies the patch byte-for-byte, and packages `.xdelta` + `.cue` + `README.txt` + `SHA256SUMS.txt` into `output/release/<version>/`.

**Tech Stack:** Python 3 stdlib (`hashlib`, `subprocess`, `tempfile`, `argparse`), external `xdelta3` CLI (installed: `/opt/homebrew/bin/xdelta3`).

**Spec:** `docs/superpowers/specs/2026-07-04-korean-patcher-design.md`

## Global Constraints

- Python 3, **stdlib only** — no pip dependencies.
- Use `os.path` (not `pathlib`) and module-level `SCRIPT_DIR`/`BASE_DIR` constants, matching `python/patch/patch_bin.py`.
- Tests are standalone scripts run with `python3` (no pytest): test functions + `if __name__ == "__main__":` runner that prints `PASS: ...` — matching `python/validation/test_scan_residual_japanese.py`.
- Tests must NOT touch the real 739 MB BINs — use small synthetic files in `tempfile.TemporaryDirectory()`.
- Redump reference values (copy verbatim):
  - Title: `Arc the Lad II (Japan) (Rev 1)`
  - MD5: `012b023097777cb6ce6a5de5e0457022`
  - Size: `739144224`
- v1.0 (SCPS-10026) dumps are out of scope; the README must say they are unsupported.
- Never ship an unverified patch: on any verification failure, delete outputs and exit non-zero.
- Commit messages: plain conventional style, no AI/assistant attribution or Co-Authored-By lines.

---

### Task 1: Hashing helpers and source verification

**Files:**
- Create: `python/patch/make_release_patch.py`
- Test: `python/patch/test_make_release_patch.py`

**Interfaces:**
- Produces (used by Tasks 2–3):
  - `md5_file(path: str) -> str` — lowercase hex digest, streaming (8 MB chunks)
  - `sha256_file(path: str) -> str` — lowercase hex digest
  - `verify_source(path: str, expected_md5: str = REDUMP_MD5, expected_size: int = REDUMP_SIZE) -> None` — raises `SystemExit` (non-zero) on mismatch
  - Constants `REDUMP_TITLE`, `REDUMP_MD5`, `REDUMP_SIZE`, `DEFAULT_ORIGINAL`, `DEFAULT_PATCHED`, `DEFAULT_CUE`, `DEFAULT_OUT_DIR`
  - Test helper `make_pair(tmp: str) -> tuple[str, str]` in the test file (reused by later tasks' tests)

- [ ] **Step 1: Write the failing tests**

Create `python/patch/test_make_release_patch.py`:

```python
"""Tests for make_release_patch.py.

Uses small synthetic files only -- never the real 739 MB BINs.
Run: python3 python/patch/test_make_release_patch.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_release_patch import md5_file, sha256_file, verify_source  # noqa: E402


def make_pair(tmp):
    """Create a small fake original/patched BIN pair (100 KB each)."""
    orig = os.path.join(tmp, "orig.bin")
    patched = os.path.join(tmp, "patched.bin")
    data = bytes(range(256)) * 400  # 102,400 bytes
    with open(orig, "wb") as f:
        f.write(data)
    mod = bytearray(data)
    mod[5000:5010] = b"KOREANTEXT"
    with open(patched, "wb") as f:
        f.write(bytes(mod))
    return orig, patched


def test_md5_and_sha256():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "x.bin")
        with open(p, "wb") as f:
            f.write(b"hello")
        assert md5_file(p) == "5d41402abc4b2a76b9719d911017c592", md5_file(p)
        assert sha256_file(p) == ("2cf24dba5fb0a30e26e83b2ac5b9e29e"
                                  "1b161e5c1fa7425e73043362938b9824"), sha256_file(p)


def test_verify_source_accepts_matching_file():
    with tempfile.TemporaryDirectory() as tmp:
        orig, _ = make_pair(tmp)
        # Must return without raising.
        verify_source(orig, md5_file(orig), os.path.getsize(orig))


def test_verify_source_rejects_wrong_size():
    with tempfile.TemporaryDirectory() as tmp:
        orig, _ = make_pair(tmp)
        try:
            verify_source(orig, md5_file(orig), os.path.getsize(orig) + 1)
        except SystemExit as e:
            assert "size mismatch" in str(e), e
        else:
            raise AssertionError("expected SystemExit for wrong size")


def test_verify_source_rejects_wrong_md5():
    with tempfile.TemporaryDirectory() as tmp:
        orig, _ = make_pair(tmp)
        try:
            verify_source(orig, "0" * 32, os.path.getsize(orig))
        except SystemExit as e:
            assert "MD5 mismatch" in str(e), e
        else:
            raise AssertionError("expected SystemExit for wrong md5")


if __name__ == "__main__":
    test_md5_and_sha256()
    test_verify_source_accepts_matching_file()
    test_verify_source_rejects_wrong_size()
    test_verify_source_rejects_wrong_md5()
    print("PASS: all make_release_patch tests")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd atl2_korean_translation && python3 python/patch/test_make_release_patch.py`
Expected: `ModuleNotFoundError: No module named 'make_release_patch'`

- [ ] **Step 3: Write the implementation**

Create `python/patch/make_release_patch.py`:

```python
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


if __name__ == "__main__":
    sys.exit("Not runnable yet: CLI arrives in Task 3.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd atl2_korean_translation && python3 python/patch/test_make_release_patch.py`
Expected: `PASS: all make_release_patch tests`

- [ ] **Step 5: Commit**

```bash
git add python/patch/make_release_patch.py python/patch/test_make_release_patch.py
git commit -m "Add hashing and redump source verification for release patch builder"
```

---

### Task 2: xdelta build and round-trip verification

**Files:**
- Modify: `python/patch/make_release_patch.py` (insert functions after `verify_source`, before the `if __name__` block)
- Test: `python/patch/test_make_release_patch.py` (append tests, extend runner)

**Interfaces:**
- Consumes: `md5_file`, `verify_source`, `make_pair` from Task 1
- Produces (used by Task 3):
  - `check_xdelta3() -> str` — absolute path to xdelta3; `SystemExit` with install hint if missing
  - `build_patch(original: str, patched: str, patch_path: str) -> None` — runs `xdelta3 -e -9 -S lzma -f -s`
  - `verify_patch(original: str, patch_path: str, expected_md5: str) -> None` — applies patch to a temp file, requires MD5 match; on ANY failure deletes `patch_path` and raises `SystemExit`; always deletes the temp file

- [ ] **Step 1: Write the failing tests**

Append to `python/patch/test_make_release_patch.py` (and extend the import):

```python
from make_release_patch import (  # noqa: E402
    md5_file, sha256_file, verify_source,
    check_xdelta3, build_patch, verify_patch)
```

(Replace the Task 1 import line with the block above — one import statement total.)

```python
def test_check_xdelta3_found():
    path = check_xdelta3()
    assert os.path.basename(path) == "xdelta3", path


def test_build_and_verify_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        patch = os.path.join(tmp, "test.xdelta")
        build_patch(orig, patched, patch)
        assert os.path.getsize(patch) > 0
        # Must not raise, and must keep the patch file.
        verify_patch(orig, patch, md5_file(patched))
        assert os.path.exists(patch)


def test_verify_patch_rejects_wrong_md5_and_deletes_patch():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        patch = os.path.join(tmp, "test.xdelta")
        build_patch(orig, patched, patch)
        try:
            verify_patch(orig, patch, "0" * 32)
        except SystemExit as e:
            assert "round-trip" in str(e), e
            assert not os.path.exists(patch), "bad patch must be deleted"
        else:
            raise AssertionError("expected SystemExit for wrong md5")
        # No temp .bin files may be left behind.
        leftovers = [f for f in os.listdir(tmp)
                     if f.endswith(".bin") and f not in ("orig.bin", "patched.bin")]
        assert leftovers == [], leftovers
```

Extend the `__main__` runner:

```python
    test_check_xdelta3_found()
    test_build_and_verify_roundtrip()
    test_verify_patch_rejects_wrong_md5_and_deletes_patch()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd atl2_korean_translation && python3 python/patch/test_make_release_patch.py`
Expected: `ImportError: cannot import name 'check_xdelta3'`

- [ ] **Step 3: Write the implementation**

Insert into `python/patch/make_release_patch.py` after `verify_source`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd atl2_korean_translation && python3 python/patch/test_make_release_patch.py`
Expected: `PASS: all make_release_patch tests`

- [ ] **Step 5: Commit**

```bash
git add python/patch/make_release_patch.py python/patch/test_make_release_patch.py
git commit -m "Add xdelta build and round-trip verification"
```

---

### Task 3: Release packaging and CLI

**Files:**
- Modify: `python/patch/make_release_patch.py` (add functions + replace the `if __name__` block)
- Test: `python/patch/test_make_release_patch.py` (append tests, extend runner)

**Interfaces:**
- Consumes: everything from Tasks 1–2
- Produces:
  - `get_version() -> str` — `git describe --tags --always` in `BASE_DIR`, `"unversioned"` on failure
  - `write_readme(out_dir: str, version: str, patch_name: str) -> None` — writes `README.txt` (Korean then English)
  - `write_sha256sums(out_dir: str, filenames: list[str]) -> None` — writes `SHA256SUMS.txt` (`<sha256>  <name>` per line)
  - `main(argv: list[str] | None = None) -> None` — full CLI; flags `--original --patched --cue --out --expected-md5 --expected-size`

- [ ] **Step 1: Write the failing test**

Append to `python/patch/test_make_release_patch.py` (extend the import with `main`):

```python
from make_release_patch import (  # noqa: E402
    md5_file, sha256_file, verify_source,
    check_xdelta3, build_patch, verify_patch, main)
```

```python
def test_main_builds_release_package():
    with tempfile.TemporaryDirectory() as tmp:
        orig, patched = make_pair(tmp)
        cue = os.path.join(tmp, "test.cue")
        with open(cue, "w") as f:
            f.write('FILE "Arc the Lad II (Korean Patch).bin" BINARY\n'
                    '  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
        out = os.path.join(tmp, "release")
        main(["--original", orig, "--patched", patched, "--cue", cue,
              "--out", out,
              "--expected-md5", md5_file(orig),
              "--expected-size", str(os.path.getsize(orig))])
        [vdir] = os.listdir(out)  # one version directory
        vpath = os.path.join(out, vdir)
        files = sorted(os.listdir(vpath))
        patch_names = [f for f in files if f.endswith(".xdelta")]
        assert len(patch_names) == 1, files
        assert patch_names[0].startswith("arc-the-lad-2-korean-"), patch_names
        assert "Arc the Lad II (Korean Patch).cue" in files, files
        assert "README.txt" in files, files
        assert "SHA256SUMS.txt" in files, files
        readme = open(os.path.join(vpath, "README.txt"), encoding="utf-8").read()
        assert "012B023097777CB6CE6A5DE5E0457022" in readme
        assert "Rev 1" in readme
        assert patch_names[0] in readme
        sums = open(os.path.join(vpath, "SHA256SUMS.txt")).read().splitlines()
        assert len(sums) == 2, sums  # patch + cue
        for line in sums:
            digest, name = line.split("  ", 1)
            assert digest == sha256_file(os.path.join(vpath, name)), line
```

Extend the `__main__` runner:

```python
    test_main_builds_release_package()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd atl2_korean_translation && python3 python/patch/test_make_release_patch.py`
Expected: `ImportError: cannot import name 'main'`

- [ ] **Step 3: Write the implementation**

Add to `python/patch/make_release_patch.py` after `verify_patch` (and REPLACE the Task 1 placeholder `if __name__` block with the one below):

```python
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
    os.makedirs(out_dir, exist_ok=True)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd atl2_korean_translation && python3 python/patch/test_make_release_patch.py`
Expected: `PASS: all make_release_patch tests`

- [ ] **Step 5: Commit**

```bash
git add python/patch/make_release_patch.py python/patch/test_make_release_patch.py
git commit -m "Add release packaging and CLI for xdelta patch builder"
```

---

### Task 4: Real end-to-end run and documentation

**Files:**
- Modify: `docs/PATCHING.md` (append a "Release patch" section at the end)

**Interfaces:**
- Consumes: the finished CLI from Task 3.
- Produces: `output/release/<version>/` on disk (NOT committed — `output/` is build artifacts) and release documentation.

- [ ] **Step 1: Run the builder against the real BINs**

Run: `cd atl2_korean_translation && python3 python/patch/make_release_patch.py`
Expected output (~1–2 min: three 739 MB hash passes + encode + decode):

```
Verifying source: .../output/patched/Arc the Lad II (Japan).bin.backup_20260206_001549.bin
Building patch: .../output/release/<version>/arc-the-lad-2-korean-<version>.xdelta
Verifying round-trip (patch original -> must equal Korean BIN)
OK: release package at .../output/release/<version>
```

- [ ] **Step 2: Inspect the package**

Run: `ls -lh "output/release/"*/ && cat "output/release/"*/SHA256SUMS.txt`
Expected: `.xdelta` ~16 MB, `.cue`, `README.txt`, `SHA256SUMS.txt` with 2 lines.

- [ ] **Step 3: Negative test — wrong source must be refused**

Run: `python3 python/patch/make_release_patch.py --original "output/patched/Arc the Lad II (Korean Patch)/Arc the Lad II (Korean Patch).bin"`
Expected: exits non-zero with `ERROR: source MD5 mismatch` naming `Arc the Lad II (Japan) (Rev 1)` (size check passes — same size — so this exercises the MD5 gate).

- [ ] **Step 4: Document the release process**

Append to `docs/PATCHING.md`:

```markdown
## Release patch (xdelta)

Releases ship a ~16 MB xdelta patch instead of the 739 MB BIN:

    python python/patch/make_release_patch.py

The script hard-fails unless the source BIN is the pristine redump dump
of "Arc the Lad II (Japan) (Rev 1)" (SCPS-91071/91310,
MD5 012B023097777CB6CE6A5DE5E0457022, 739,144,224 bytes), then builds
`output/release/<git-describe>/` containing the `.xdelta`, the `.cue`,
a bilingual `README.txt`, and `SHA256SUMS.txt`. The patch is round-trip
verified (applied back to the original and MD5-compared against the
Korean BIN) before packaging; a failed verification deletes the patch.

The v1.0 release (SCPS-10026) is a different image and is not supported.
Requires `xdelta3` (`brew install xdelta` / `apt install xdelta3`).
Attach the folder contents to the GitHub release. Users apply the patch
with Delta Patcher or https://www.marcrobledo.com/RomPatcher.js/ (per
the bundled README.txt).
```

- [ ] **Step 5: Commit**

```bash
git add docs/PATCHING.md
git commit -m "Document xdelta release patch build process"
```
