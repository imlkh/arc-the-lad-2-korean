#!/usr/bin/env python3
"""
Arc the Lad 2 Korean Translation - Patch Workflow Orchestrator

Runs the complete patch workflow:
0. Validation - Check for potential issues before patching
1. patch_all.py - Font + fixed-length patching
2. patch_variable_length_multi.py - Variable-length VLUTs for each STG
3. apply_hook.py - Apply variable-length hook
4. patch_bin.py - Apply patches to disc image

Usage:
    python patch_workflow.py                    # Patch S100 and SG00
    python patch_workflow.py S100               # Patch only S100
    python patch_workflow.py S100 SG00 S200     # Patch specific stages
    python patch_workflow.py --all              # Patch all available stages
    python patch_workflow.py --validate-only    # Only run validation, no patching
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

# Constants
CHUNK_SIZE = 0xBC800  # 772,096 bytes per chunk

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_step(step_num, text):
    print(f"{Colors.BOLD}[{step_num}] {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}! {text}{Colors.END}")

def run_command(cmd, description):
    """Run a command and return success status."""
    print_step("→", description)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            # Print abbreviated output
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if any(x in line.lower() for x in ['patched', 'saved', 'total', 'error', 'ok:', 'summary']):
                    print(f"    {line}")
            print_success(description)
            return True
        else:
            print_error(f"{description} failed")
            print(result.stderr)
            return False
    except Exception as e:
        print_error(f"{description} failed: {e}")
        return False

def find_available_stages():
    """Find all STG files that have translation files."""
    translated_dir = Path(__file__).parent.parent.parent / "translated" / "ko"
    stages = []
    for f in translated_dir.glob("*_STG.txt"):
        stage_name = f.stem.replace("_STG", "")
        stages.append(stage_name)
    return sorted(stages)

def find_bin_image():
    """Find the BIN disc image (the patched output is the Korean-named disc)."""
    patched_dir = Path(__file__).parent.parent.parent / "output" / "patched"

    # Explicit names, in preference order (Korean-patched output first).
    patterns = [
        "Arc the Lad II (Korean Patch)/Arc the Lad II (Korean Patch).bin",
        "Arc the Lad II (Japan)/Arc the Lad II (Japan).bin",
        "Arc the Lad 2 (Japan)/Arc the Lad 2 (Japan).bin",
    ]
    for pattern in patterns:
        matches = list(patched_dir.glob(pattern))
        if matches:
            return matches[0]

    # Fallback: any *.bin in a disc subfolder or top level, excluding backups.
    def _not_backup(p):
        return ".backup_" not in p.name
    for pattern in ("*/*.bin", "*.bin"):
        matches = [p for p in patched_dir.glob(pattern) if _not_backup(p)]
        if matches:
            return matches[0]

    return None


def copy_translation_files(stages):
    """Copy translation files to output/patched/translation/ directory.

    This preserves the translated text files alongside the patched game files.
    """
    base_dir = Path(__file__).parent.parent.parent
    translated_dir = base_dir / "translated" / "ko"
    output_dir = base_dir / "output" / "patched" / "translation"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    # Remove previously staged STG files so excluded stages are not
    # accidentally picked up by patch_all.py on later runs.
    for old_stg in output_dir.glob("*_STG.txt"):
        old_stg.unlink()

    # Copy STG translation files for specified stages
    for stage in stages:
        src = translated_dir / f"{stage}_STG.txt"
        if src.exists():
            dst = output_dir / f"{stage}_STG.txt"
            shutil.copy2(src, dst)
            copied.append(f"{stage}_STG.txt")

    # Also copy other translation files (BIN files, etc.)
    other_files = [
        "SCPS_100_26.txt",
        "SDIC_BIN.txt",
        "YGUILD_BIN.txt",
        "SMITH_BIN.txt",
        "BEAM_DAT.txt",
    ]

    for filename in other_files:
        src = translated_dir / filename
        if src.exists():
            dst = output_dir / filename
            shutil.copy2(src, dst)
            copied.append(filename)

    return copied


def validate_translations(stages):
    """Validate translation files for potential issues before patching.

    Checks:
    1. [box:speech][delay:00] in padding/event regions (should be [box:speech] only)
    2. Dialogues that will be truncated (Korean text too long)

    Returns:
        tuple: (errors, warnings) - lists of issue descriptions
    """
    base_dir = Path(__file__).parent.parent.parent
    translated_dir = base_dir / "translated" / "ko"
    game_dir = base_dir.parent

    errors = []
    warnings = []

    # Try to load encoding functions for size calculation
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from patch_korean import load_decode_table, encode_korean_text, build_encode_table
        from patch_variable_length_multi import get_vlut_config
        can_check_size = True
        decode_table = load_decode_table()

        # Try to load charmap if it exists
        charmap_path = base_dir / "output" / "patched" / "unified_charmap.txt"
        charmap = {}
        if charmap_path.exists():
            with open(charmap_path) as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        charmap[parts[0]] = int(parts[1])
    except Exception as e:
        can_check_size = False
        warnings.append(f"Cannot load encoding modules for size validation: {e}")

    for stage in stages:
        trans_file = translated_dir / f"{stage}_STG.txt"
        if not trans_file.exists():
            warnings.append(f"{stage}: Translation file not found")
            continue

        # Try to load original STG for size comparison
        orig_stg = game_dir / f"{stage}.STG"
        orig_data = None
        if orig_stg.exists():
            try:
                with open(orig_stg, 'rb') as f:
                    orig_data = f.read()
            except:
                pass

        # Load VLUT config to know which chunks use variable-length relocation
        vlut_offsets = {}
        if orig_data and can_check_size:
            try:
                vlut_offsets, _ = get_vlut_config(stage, orig_data)
            except Exception:
                pass

        with open(trans_file) as f:
            lines = f.readlines()

        delay_in_padding = []
        truncated = []
        vlut_skipped = 0

        for line_num, line in enumerate(lines, 1):
            if not line.strip().startswith('0x'):
                continue

            parts = line.strip().split()
            if not parts:
                continue

            try:
                offset = int(parts[0], 16)
            except:
                continue

            within_chunk = offset % CHUNK_SIZE
            is_padding_region = 0xA0000 <= within_chunk < 0xB4000

            # Note: [box:speech] display bug fix is now handled automatically
            # by encode_korean_text() inserting a space (0xA0, 1 byte) after
            # [box:speech] at string start. The old [delay:00] workaround
            # (4 bytes) is no longer needed in translation files.

            # Check 2: Truncation in padding region (only if we can calculate size)
            # Skip VLUT-enabled chunks — the variable-length patcher handles overflows
            if is_padding_region and vlut_offsets:
                chunk_idx = offset // CHUNK_SIZE
                if vlut_offsets.get(chunk_idx, 0) != 0:
                    vlut_skipped += 1
                    continue

            if is_padding_region and can_check_size and orig_data and charmap:
                # Extract content after [script:XX XX]
                script_idx = line.find('[script:')
                if script_idx == -1:
                    continue
                script_end = line.find(']', script_idx) + 1
                content = line[script_end:].strip()

                # Parse script prefix bytes (e.g., "A9 00" -> 2 bytes)
                script_text = line[script_idx+8:script_end-1]  # "XX XX" part
                script_bytes = bytes.fromhex(script_text.replace(' ', ''))
                prefix_len = len(script_bytes)

                try:
                    # Get original slot size - skip script prefix when finding null
                    # (Script prefix like "00 24" or "A9 00" contains 0x00 bytes)
                    slot_data = orig_data[offset + prefix_len:offset + 200]
                    null_pos = slot_data.find(b'\x00')
                    if null_pos == -1 or null_pos > 150:
                        continue
                    orig_size = prefix_len + null_pos + 1  # prefix + text + null

                    # Encode Korean text
                    encoded = encode_korean_text(content, charmap, decode_table)
                    korean_size = len(encoded) + 1  # +1 for null

                    # Available space (minus 2-byte script prefix)
                    available = orig_size - 2

                    if korean_size > available:
                        overflow = korean_size - available
                        truncated.append({
                            'line': line_num,
                            'offset': offset,
                            'orig_size': orig_size,
                            'korean_size': korean_size,
                            'overflow': overflow,
                            'text': content[:50]
                        })
                except:
                    pass

        # Report issues for this stage
        # delay_in_padding check removed — [box:speech] display bug is now
        # handled automatically by the encoder (1-byte space insertion)

        if vlut_skipped:
            warnings.append(
                f"{stage}: {vlut_skipped} padding-region entries skipped (VLUT-enabled chunks handle overflow)"
            )

        if truncated:
            # Separate critical (>3 bytes) from minor (1-3 bytes) truncation
            critical = [t for t in truncated if t['overflow'] > 3]
            minor = [t for t in truncated if t['overflow'] <= 3]

            for item in critical:
                errors.append(
                    f"{stage} line {item['line']}: CRITICAL truncation at 0x{item['offset']:08X} "
                    f"(overflow {item['overflow']}b) - must shorten text"
                )

            if minor:
                # Summarize minor truncations
                warnings.append(
                    f"{stage}: {len(minor)} minor truncations (1-3 bytes) in padding/event regions - may cause display issues"
                )

    return errors, warnings


def main():
    print_header("Arc the Lad 2 Korean Translation - Patch Workflow")

    # Check for validate-only mode
    validate_only = "--validate-only" in sys.argv
    if validate_only:
        sys.argv.remove("--validate-only")

    # Determine which stages to patch
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            stages = find_available_stages()
            print(f"Found {len(stages)} stages with translations: {', '.join(stages)}")
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
            return 0
        else:
            stages = [s.upper() for s in sys.argv[1:]]
    else:
        # Default stage selection (edit here).
        # - include_stages: explicit list to patch by default
        # - exclude_stages: remove stages from include list
        # If include_stages is empty, all available stages are included first.
        # include_stages = ["S100", "SG00", "S200"]   # e.g. ["S100", "SG00", "S200", "S300"]
        include_stages = [
            "S100",
            "S200",
            "S300",
            "S400",
            "S500",
            "S600",
            "S700",
            "S800",
            "S900",
            "SA00",
            "SB00",
            "SC00",
            "SD00",
            "SE00",
            "SF00",
            "SG00",
            "SH00",
            "SI00",
            "SJ00",
        ]
        exclude_stages = []                  # e.g. ["S200"]

        if include_stages:
            stages = [s.upper() for s in include_stages]
        else:
            stages = [s.upper() for s in find_available_stages()]

        exclude_set = {s.upper() for s in exclude_stages}
        stages = [s for s in stages if s not in exclude_set]

    print(f"Stages to patch: {', '.join(stages)}")

    # Step 0: Validation
    print_header("Step 0: Validation")
    print_step("→", "Checking translation files for issues...")

    errors, warnings = validate_translations(stages)

    # Print errors (critical issues)
    for error in errors:
        print_error(error)

    if errors:
        print(f"\n{Colors.RED}{Colors.BOLD}Found {len(errors)} critical error(s) that will cause display issues.{Colors.END}")
        print(f"{Colors.YELLOW}Fix these issues before patching:{Colors.END}")
        print(f"  - [box:speech] display bug → now auto-fixed by encoder")
        print(f"  - CRITICAL truncation (>3 bytes) → shorten Korean text")

        if validate_only:
            return 1

        # Ask user if they want to continue anyway
        print(f"\n{Colors.YELLOW}Continue with patching anyway? (y/N): {Colors.END}", end="")
        try:
            response = input().strip().lower()
            if response != 'y':
                print("Aborted.")
                return 1
        except:
            print("\nAborted.")
            return 1
    elif warnings:
        print_success(f"Validation passed with {len(warnings)} warning(s)")
        for warning in warnings:
            print(f"    {Colors.YELLOW}⚠ {warning}{Colors.END}")
    else:
        print_success("Validation passed - no issues found")

    if validate_only:
        print(f"\n{Colors.GREEN}Validation complete. Use without --validate-only to patch.{Colors.END}")
        return 0

    # Track results
    results = {
        "validation": len(errors) == 0,
        "font": None,
        "stages": {},
        "hook": None,
        "bin": None
    }

    # Copy translation files to output directory
    print_step("→", "Copying translation files to output/patched/translation/")
    copied_files = copy_translation_files(stages)
    print_success(f"Copied {len(copied_files)} translation files")

    # Step 1: Font + fixed-length patching
    print_header("Step 1: Font + Fixed-Length Patching")
    results["font"] = run_command(
        [sys.executable, "patch_all.py"],
        "patch_all.py - Font and fixed-length patching"
    )

    if not results["font"]:
        print_error("Font patching failed. Aborting.")
        return 1

    # Ensure stage STGs were refreshed by patch_all.py.
    # If this fails, step 2 may re-patch stale VLUT data from a previous run.
    base_dir = Path(__file__).parent.parent.parent
    output_dir = base_dir / "output" / "patched"
    missing_stage_outputs = [s for s in stages if not (output_dir / f"{s}.STG").exists()]
    if missing_stage_outputs:
        print_error(
            "Missing staged STG outputs after patch_all.py: "
            + ", ".join(missing_stage_outputs)
        )
        print("  Expected files in output/patched/<STAGE>.STG before variable-length step.")
        return 1

    # Step 2: Variable-length patching for each stage
    print_header("Step 2: Variable-Length Patching")
    for stage in stages:
        results["stages"][stage] = run_command(
            [sys.executable, "patch_variable_length_multi.py", stage],
            f"patch_variable_length_multi.py {stage}"
        )
        if not results["stages"][stage]:
            print_warning(f"Variable-length patching for {stage} failed, continuing...")

    # Step 3: Apply hook
    print_header("Step 3: Apply Variable-Length Hook")
    results["hook"] = run_command(
        [sys.executable, "apply_hook.py", "--variable-length-multi"],
        "apply_hook.py --variable-length-multi"
    )

    if not results["hook"]:
        print_error("Hook application failed. Aborting.")
        return 1

    # Step 4: Apply to disc image
    print_header("Step 4: Apply to Disc Image")
    bin_path = find_bin_image()

    if bin_path:
        patch_bin_cmd = [sys.executable, "patch_bin.py", str(bin_path), "--stages", *stages]
        results["bin"] = run_command(
            patch_bin_cmd,
            f"patch_bin.py {bin_path.name}"
        )
    else:
        print_warning("No BIN disc image found in output/patched/")
        print("  Run manually: python patch_bin.py <path_to_bin>")
        results["bin"] = None

    # Summary
    print_header("Summary")

    print(f"Validation:        {'✓' if results['validation'] else '⚠ (continued with errors)'}")
    print(f"Font patching:     {'✓' if results['font'] else '✗'}")
    for stage, success in results["stages"].items():
        print(f"  {stage} variable:   {'✓' if success else '✗'}")
    print(f"Hook applied:      {'✓' if results['hook'] else '✗'}")
    print(f"BIN patched:       {'✓' if results['bin'] else '—' if results['bin'] is None else '✗'}")

    # Check if all succeeded
    all_stages_ok = all(results["stages"].values())
    all_ok = results["validation"] and results["font"] and all_stages_ok and results["hook"] and results["bin"]

    if all_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All steps completed successfully!{Colors.END}")
        print(f"\nDisc image ready at:")
        if bin_path:
            print(f"  {bin_path}")
    else:
        print(f"\n{Colors.YELLOW}Workflow completed with some issues.{Colors.END}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
