#!/usr/bin/env python3
"""
Test script to isolate freeze issues by selectively patching.

Modes:
  stg-only   - STG patches + VLUT + hook only (original non-STG files)
  stg-fixed  - STG fixed-length only, no VLUT/hook (original non-STG files)
  bin-only   - Non-STG patches only (original STG files, no hook)
  full       - Full workflow (same as patch_workflow.py)

Usage:
    python test_isolate.py stg-only              # S100+SG00 with VLUT+hook
    python test_isolate.py stg-only S100         # S100 only with VLUT+hook
    python test_isolate.py stg-fixed             # S100+SG00 fixed-length only
    python test_isolate.py stg-fixed S100        # S100 only fixed-length
    python test_isolate.py bin-only
    python test_isolate.py full
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent.parent          # atl2_korean_translation/
GAME_DIR = BASE_DIR.parent                   # Arc_The_Lad2/
OUTPUT_DIR = BASE_DIR / "output" / "patched"
TRANS_SRC = BASE_DIR / "translated" / "ko"
TRANS_DST = OUTPUT_DIR / "translation"

# STG translation files
STG_FILES = ["S100_STG.txt", "SG00_STG.txt"]

# Non-STG translation files
BIN_FILES = [
    "SCPS_100_26.txt",
    "SDIC_BIN.txt",
    "YGUILD_BIN.txt",
    "SMITH_BIN.txt",
    "BEAM_DAT.txt",
]

# Original game files that correspond to non-STG translations
ORIGINAL_BIN_MAP = {
    "SCPS_100.26": "SCPS_100.26",
    "SDIC.BIN": "SDIC.BIN",
    "YGUILD.BIN": "YGUILD.BIN",
    "SMITH.BIN": "SMITH.BIN",
    "BEAM.DAT": "BEAM.DAT",
}

ORIGINAL_STG_MAP = {
    "S100.STG": "S100.STG",
    "SG00.STG": "SG00.STG",
}

STAGES = ["S100", "SG00"]
CHUNK_SIZE = 0xBC800


def filter_translation_by_chunks(src_path, dst_path, include_chunks,
                                  exclude_offsets=None):
    """Copy translation file but only include entries from specified chunks.

    Args:
        exclude_offsets: set of offset ranges (start, end) to exclude
    """
    import re
    kept = 0
    excluded = 0
    total = 0
    with open(src_path, 'r', encoding='utf-8') as fin, \
         open(dst_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            if line.strip().startswith('0x'):
                total += 1
                match = re.match(r'0x([0-9A-Fa-f]+)', line.strip())
                if match:
                    offset = int(match.group(1), 16)
                    chunk_idx = offset // CHUNK_SIZE

                    # Check exclude ranges
                    if exclude_offsets:
                        skip = False
                        for rng_start, rng_end in exclude_offsets:
                            if rng_start <= offset < rng_end:
                                skip = True
                                excluded += 1
                                break
                        if skip:
                            continue

                    if chunk_idx in include_chunks:
                        fout.write(line)
                        kept += 1
                    continue
            # Keep context/header lines
            fout.write(line)
    msg = f"  Filtered: {kept}/{total} entries (chunks {sorted(include_chunks)})"
    if excluded:
        msg += f", excluded {excluded} entries by offset range"
    print(msg)
    return kept


def run(cmd, desc):
    """Run a command and print output."""
    print(f"\n>>> {desc}")
    print(f"    {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
    # Print key output lines
    for line in result.stdout.strip().split('\n'):
        if any(x in line.lower() for x in ['patched', 'saved', 'total', 'error',
                                             'ok', 'summary', 'copied', 'skip',
                                             'chunk', 'vlut', 'hook', 'entries']):
            print(f"    {line}")
    if result.returncode != 0:
        print(f"    FAILED (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.strip().split('\n')[:5]:
                print(f"    ERR: {line}")
        return False
    print(f"    OK")
    return True


def copy_translations(include_stg=True, include_bin=True, stages=None):
    """Copy selected translation files to staging directory.

    Args:
        include_stg: Include STG translation files
        include_bin: Include non-STG translation files
        stages: List of stage names to include (e.g., ["S100"]). None = all.
    """
    TRANS_DST.mkdir(parents=True, exist_ok=True)

    # Clean existing translation staging
    for f in TRANS_DST.glob("*.txt"):
        f.unlink()

    copied = []

    if include_stg:
        stg_files = STG_FILES
        if stages:
            stg_files = [f"{s}_STG.txt" for s in stages]
        for name in stg_files:
            src = TRANS_SRC / name
            if src.exists():
                shutil.copy2(src, TRANS_DST / name)
                copied.append(name)

    if include_bin:
        for name in BIN_FILES:
            src = TRANS_SRC / name
            if src.exists():
                shutil.copy2(src, TRANS_DST / name)
                copied.append(name)

    print(f"Copied {len(copied)} translation files: {', '.join(copied)}")
    return copied


def replace_with_originals(file_map):
    """Replace patched output files with un-patched originals."""
    for game_name, out_name in file_map.items():
        src = GAME_DIR / game_name
        dst = OUTPUT_DIR / out_name
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Replaced with original: {out_name}")
        else:
            print(f"  WARNING: Original not found: {src}")


def ensure_scps_for_hook():
    """Ensure SCPS_100.26 exists in output for hook application."""
    dst = OUTPUT_DIR / "SCPS_100.26"
    if not dst.exists():
        src = GAME_DIR / "SCPS_100.26"
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied original SCPS_100.26 for hook")


def mode_stg_only(stages=None):
    """Test with STG patches + VLUT + hook only."""
    stages = stages or STAGES
    print("=" * 60)
    print(f"MODE: stg-only ({', '.join(stages)})")
    print("  STG: fixed-length + variable-length VLUT + hook")
    print("  BIN: original (no Korean patches)")
    print("=" * 60)

    # 1. Copy only STG translations
    copy_translations(include_stg=True, include_bin=False, stages=stages)

    # 2. Run patch_all.py (font + STG fixed-length only)
    if not run([sys.executable, "patch_all.py"], "Font + STG fixed-length patching"):
        return False

    # 3. Run variable-length patcher for each stage
    for stage in stages:
        run([sys.executable, "patch_variable_length_multi.py", stage],
            f"Variable-length VLUT for {stage}")

    # 4. Ensure SCPS exists for hook, then apply hook
    ensure_scps_for_hook()
    if not run([sys.executable, "apply_hook.py", "--variable-length-multi"],
               "Apply variable-length hook"):
        return False

    # 5. Replace non-STG files with originals (except SCPS which has hook)
    print("\nReplacing non-STG files with originals...")
    replace_with_originals({
        "SDIC.BIN": "SDIC.BIN",
        "YGUILD.BIN": "YGUILD.BIN",
        "SMITH.BIN": "SMITH.BIN",
        "BEAM.DAT": "BEAM.DAT",
    })
    # Replace STGs that are NOT in our test set with originals
    for stg_name, out_name in ORIGINAL_STG_MAP.items():
        stage = stg_name.replace(".STG", "")
        if stage not in stages:
            replace_with_originals({stg_name: out_name})

    # 6. Build disc image
    return build_disc_image()


def mode_stg_fixed(stages=None):
    """Test with STG fixed-length only (no VLUT/hook)."""
    stages = stages or STAGES
    print("=" * 60)
    print(f"MODE: stg-fixed ({', '.join(stages)})")
    print("  STG: fixed-length only (NO VLUT, NO hook)")
    print("  BIN: original (no Korean patches)")
    print("=" * 60)

    # 1. Copy only STG translations
    copy_translations(include_stg=True, include_bin=False, stages=stages)

    # 2. Run patch_all.py (font + STG fixed-length only)
    if not run([sys.executable, "patch_all.py"], "Font + STG fixed-length patching"):
        return False

    # 3. NO variable-length, NO hook

    # 4. Ensure SCPS/BIN files exist as originals
    print("\nReplacing non-STG files with originals...")
    replace_with_originals(ORIGINAL_BIN_MAP)
    # Replace STGs not in our test set
    for stg_name, out_name in ORIGINAL_STG_MAP.items():
        stage = stg_name.replace(".STG", "")
        if stage not in stages:
            replace_with_originals({stg_name: out_name})

    # 5. Build disc image
    return build_disc_image()


def mode_bin_only():
    """Test with non-STG patches only."""
    print("=" * 60)
    print("MODE: bin-only")
    print("  STG: original (no Korean patches)")
    print("  BIN: Korean patches (SCPS, SDIC, YGUILD, SMITH, BEAM)")
    print("  Hook: NO")
    print("=" * 60)

    # 1. Copy only non-STG translations
    copy_translations(include_stg=False, include_bin=True)

    # 2. Run patch_all.py (font + non-STG patching only)
    if not run([sys.executable, "patch_all.py"], "Font + non-STG patching"):
        return False

    # 3. NO variable-length, NO hook

    # 4. Replace STG files with originals
    print("\nReplacing STG files with originals...")
    replace_with_originals(ORIGINAL_STG_MAP)

    # 5. Ensure SCPS has no hook (re-patch from original + translations)
    # patch_all.py already patched SCPS without hook, so it's fine

    # 6. Build disc image
    return build_disc_image()


def mode_full():
    """Full workflow (same as patch_workflow.py)."""
    print("=" * 60)
    print("MODE: full")
    print("  STG: fixed-length + variable-length VLUT + hook")
    print("  BIN: Korean patches (SCPS, SDIC, YGUILD, SMITH, BEAM)")
    print("=" * 60)

    # 1. Copy all translations
    copy_translations(include_stg=True, include_bin=True)

    # 2. Run patch_all.py
    if not run([sys.executable, "patch_all.py"], "Font + all patching"):
        return False

    # 3. Run variable-length patcher
    for stage in STAGES:
        run([sys.executable, "patch_variable_length_multi.py", stage],
            f"Variable-length VLUT for {stage}")

    # 4. Apply hook
    if not run([sys.executable, "apply_hook.py", "--variable-length-multi"],
               "Apply variable-length hook"):
        return False

    # 5. Build disc image
    return build_disc_image()


def build_disc_image():
    """Find and patch the disc image (rename-proof; excludes backups)."""
    # Disc bins live in a subfolder; exclude *.backup_*.bin and prefer the
    # Korean-named disc.
    matches = [p for p in OUTPUT_DIR.glob("**/*.bin")
               if ".backup_" not in p.name]
    matches.sort(key=lambda p: (0 if "Korean" in p.name else 1, p.name))
    if matches:
        return run([sys.executable, "patch_bin.py", str(matches[0])],
                   f"Build disc image: {matches[0].name}")

    print("ERROR: No BIN disc image found")
    return False


def mode_stg_chunk(stages=None, chunks=None, exclude_region=None):
    """Test with only specific chunks patched in S100 (fixed-length, no VLUT/hook).

    Args:
        exclude_region: "event" to exclude event_script region (0xB0000-0xB4000),
                       "text" to exclude text region (0xB4000+),
                       "first-half"/"second-half" to split text region entries
    """
    stage = (stages or ["S100"])[0]
    if not chunks:
        print("ERROR: Specify chunks, e.g.: python test_isolate.py stg-chunk S100 0,1,2")
        return False

    label = f"{stage} chunks {sorted(chunks)}"
    if exclude_region:
        label += f" exclude={exclude_region}"

    print("=" * 60)
    print(f"MODE: stg-chunk ({label})")
    print("  STG: fixed-length, selected chunks only")
    print("  BIN: original (no Korean patches)")
    print("  Hook: NO")
    print("=" * 60)

    # Build exclude offset ranges based on region filter
    exclude_offsets = None
    if exclude_region:
        exclude_offsets = set()
        for c in chunks:
            cs = c * CHUNK_SIZE
            if exclude_region == "event":
                # Exclude event_script region (0xB0000-0xB4000)
                exclude_offsets.add((cs + 0xB0000, cs + 0xB4000))
            elif exclude_region == "text":
                # Exclude text region (0xB4000+)
                exclude_offsets.add((cs + 0xB4000, cs + CHUNK_SIZE))
            elif exclude_region == "padding":
                # Exclude padding region (0xA0000-0xB0000)
                exclude_offsets.add((cs + 0xA0000, cs + 0xB0000))
            elif exclude_region == "first-half":
                # Exclude first half of text region
                mid = cs + 0xB4000 + (CHUNK_SIZE - 0xB4000) // 2
                exclude_offsets.add((cs + 0xB4000, mid))
            elif exclude_region == "second-half":
                mid = cs + 0xB4000 + (CHUNK_SIZE - 0xB4000) // 2
                exclude_offsets.add((mid, cs + CHUNK_SIZE))
            elif exclude_region == "q3":
                # Exclude 3rd quarter (first half of second half)
                mid = cs + 0xB4000 + (CHUNK_SIZE - 0xB4000) // 2
                q3_end = mid + (cs + CHUNK_SIZE - mid) // 2
                exclude_offsets.add((mid, q3_end))
            elif exclude_region == "q4":
                # Exclude 4th quarter (second half of second half)
                mid = cs + 0xB4000 + (CHUNK_SIZE - 0xB4000) // 2
                q3_end = mid + (cs + CHUNK_SIZE - mid) // 2
                exclude_offsets.add((q3_end, cs + CHUNK_SIZE))

    # Extra filtering modes (works alongside offset-based)
    if exclude_region:
        import re as _re
        src = TRANS_SRC / f"{stage}_STG.txt"

        if exclude_region.startswith("opcode="):
            # e.g., --exclude=opcode=00B4
            exclude_opcode = int(exclude_region.split("=", 1)[1], 16)
            with open(src) as f:
                for line in f:
                    m = _re.match(r'\s*0x([0-9A-Fa-f]+)\s+\[0x([0-9A-Fa-f]+)\]', line.strip())
                    if m:
                        off = int(m.group(1), 16)
                        opc = int(m.group(2), 16)
                        if opc == exclude_opcode:
                            if exclude_offsets is None:
                                exclude_offsets = set()
                            exclude_offsets.add((off, off + 1))

        elif exclude_region.startswith("only=opcode="):
            # KEEP only entries with this opcode, exclude everything else
            keep_opcode = int(exclude_region.split("=")[2], 16)
            if exclude_offsets is None:
                exclude_offsets = set()
            with open(src) as f:
                for line in f:
                    m = _re.match(r'\s*0x([0-9A-Fa-f]+)\s+\[0x([0-9A-Fa-f]+)\]', line.strip())
                    if m:
                        off = int(m.group(1), 16)
                        opc = int(m.group(2), 16)
                        if opc != keep_opcode:
                            exclude_offsets.add((off, off + 1))

        elif exclude_region.startswith("range="):
            # e.g., --exclude=range=178000-178400
            rng = exclude_region.split("=", 1)[1]
            parts = rng.split("-")
            rng_start = int(parts[0], 16)
            rng_end = int(parts[1], 16)
            if exclude_offsets is None:
                exclude_offsets = set()
            exclude_offsets.add((rng_start, rng_end))

        elif exclude_region.startswith("only=range="):
            # KEEP only entries in this range, exclude everything else
            rng = exclude_region.split("=", 2)[2]
            parts = rng.split("-")
            rng_start = int(parts[0], 16)
            rng_end = int(parts[1], 16)
            if exclude_offsets is None:
                exclude_offsets = set()
            # Exclude everything outside the range
            exclude_offsets.add((0, rng_start))
            exclude_offsets.add((rng_end, 0xFFFFFFFF))

    # 1. Copy STG translation, filtered by chunks
    TRANS_DST.mkdir(parents=True, exist_ok=True)
    for f in TRANS_DST.glob("*.txt"):
        f.unlink()

    src = TRANS_SRC / f"{stage}_STG.txt"
    dst = TRANS_DST / f"{stage}_STG.txt"
    if not src.exists():
        print(f"ERROR: {src} not found")
        return False
    filter_translation_by_chunks(src, dst, chunks, exclude_offsets=exclude_offsets)

    # 2. Run patch_all.py
    if not run([sys.executable, "patch_all.py"], f"Font + {stage} chunks {sorted(chunks)}"):
        return False

    # 3. Replace everything else with originals
    print("\nReplacing other files with originals...")
    replace_with_originals(ORIGINAL_BIN_MAP)
    for stg_name, out_name in ORIGINAL_STG_MAP.items():
        s = stg_name.replace(".STG", "")
        if s != stage:
            replace_with_originals({stg_name: out_name})

    # 4. Build disc image
    return build_disc_image()


MODES = {
    "stg-only": mode_stg_only,
    "stg-fixed": mode_stg_fixed,
    "stg-chunk": mode_stg_chunk,
    "bin-only": mode_bin_only,
    "full": mode_full,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODES:
        print(__doc__)
        print(f"\nAvailable modes: {', '.join(MODES.keys())}")
        print(f"\nExamples:")
        print(f"  python test_isolate.py stg-fixed S100")
        print(f"  python test_isolate.py stg-chunk S100 0,1,2,3,4")
        print(f"  python test_isolate.py stg-chunk S100 5,6,7,8,9,10")
        return 1

    mode = sys.argv[1]
    extra_args = sys.argv[2:]

    # Parse stage, chunk, and exclude arguments
    extra_stages = None
    chunk_set = None
    exclude_region = None

    for arg in extra_args:
        if arg.startswith("--exclude="):
            exclude_region = arg.split("=", 1)[1]
        elif ',' in arg or arg.isdigit():
            chunk_set = set(int(x) for x in arg.split(','))
        else:
            if extra_stages is None:
                extra_stages = []
            extra_stages.append(arg.upper())

    label = mode
    if extra_stages:
        label += f" ({', '.join(extra_stages)})"
    if chunk_set:
        label += f" chunks={sorted(chunk_set)}"
    if exclude_region:
        label += f" exclude={exclude_region}"
    print(f"\n=== Test Isolate: {label} ===\n")

    mode_func = MODES[mode]
    if mode == "stg-chunk":
        success = mode_func(stages=extra_stages, chunks=chunk_set,
                           exclude_region=exclude_region)
    elif mode in ("stg-only", "stg-fixed"):
        success = mode_func(stages=extra_stages)
    else:
        success = mode_func()

    if success:
        print(f"\n{'='*60}")
        print(f"BUILD COMPLETE: {label}")
        print(f"{'='*60}")
    else:
        print(f"\nBUILD FAILED: {label}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
