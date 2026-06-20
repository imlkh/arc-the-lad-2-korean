#!/usr/bin/env python3
"""
Update STG translation files to match newly decoded structure.

Merges existing Korean translations with the new decoded file:
1. Uses decoded file as the structural template (source of truth)
2. Substitutes Korean translations by offset first
3. Falls back to JP→KO text cache (from ALL translation files) for text-based matching
4. Removes invalid entries (per invalid report)
5. Recalculates context lines from actual entry sequence

Usage:
    python update_stg_translation.py SG00          # Single stage
    python update_stg_translation.py SG00 S100     # Multiple stages
    python update_stg_translation.py --all          # All stages
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DECODED_DIR = BASE_DIR / "output" / "decoded" / "stg"
TRANSLATED_DIR = BASE_DIR / "translated" / "ko"

# All known STG stage names
ALL_STAGES = [
    "S100", "S200", "S300", "S400", "S500", "S600", "S700", "S800", "S900",
    "SA00", "SB00", "SC00", "SD00", "SE00", "SF00", "SG00", "SH00", "SI00", "SJ00",
]

# Regex to parse dialogue lines: offset + opcode + [script:XX XX] + text
DIALOGUE_RE = re.compile(
    r"^(\s+)(0x[0-9A-Fa-f]+)\s+"
    r"\[(0x[0-9A-Fa-f]+)\]\s+"
    r"\[script:([0-9A-Fa-f]+ [0-9A-Fa-f]+)\]"
    r"(.*)"
)

CONTEXT_RE = re.compile(r"^\s+--- context: (0x[0-9A-Fa-f]+) -> (0x[0-9A-Fa-f]+) ---")

# Regex to detect Korean text (Hangul syllables + Jamo)
KOREAN_RE = re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]")

# Regex to detect Japanese text (Hiragana + Katakana + CJK)
JP_RE = re.compile(r"[\u3041-\u3096\u30A1-\u30FA\u4E00-\u9FFF]")

# Invalid report: extract offsets from lines like "  Line 1453: 0x003ABC0F [0x8005] ..."
INVALID_LINE_RE = re.compile(r"Line \d+:\s+(0x[0-9A-Fa-f]+)")


def parse_dialogue_line(line: str) -> dict | None:
    """Parse a dialogue line into components."""
    m = DIALOGUE_RE.match(line)
    if not m:
        return None
    return {
        "indent": m.group(1),
        "offset": m.group(2),
        "offset_int": int(m.group(2), 16),
        "opcode": m.group(3),
        "script": m.group(4),
        "text": m.group(5),
    }


def build_dialogue_line(parsed: dict, text: str | None = None) -> str:
    """Reconstruct a dialogue line from parsed components."""
    t = text if text is not None else parsed["text"]
    return f"  {parsed['offset']} [{parsed['opcode']}] [script:{parsed['script']}]{t}"


def load_invalid_offsets(stage: str) -> set[int]:
    """Read invalid_report.txt, extract excluded offsets."""
    report = DECODED_DIR / f"{stage}_STG_invalid_report.txt"
    if not report.exists():
        return set()
    offsets: set[int] = set()
    for line in report.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = INVALID_LINE_RE.search(line)
        if m:
            offsets.add(int(m.group(1), 16))
    return offsets


def load_translations(filepath: Path) -> dict[int, str]:
    """Load offset → text mapping from translated file."""
    translations: dict[int, str] = {}
    if not filepath.exists():
        return translations
    seen: set[int] = set()
    for line_num, line in enumerate(
        filepath.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
    ):
        parsed = parse_dialogue_line(line)
        if not parsed:
            continue
        offset = parsed["offset_int"]
        if offset in seen:
            continue
        seen.add(offset)
        translations[offset] = parsed["text"]
    return translations


def build_text_cache() -> dict[str, str]:
    """Build JP→KO cache from ALL existing translation files.

    For each translated STG file, pairs decoded JP text with translated KO text
    at the same offset. Only includes entries where the translated text contains
    Korean characters and differs from the source JP text.
    """
    cache: dict[str, str] = {}
    for ko_path in sorted(TRANSLATED_DIR.glob("S*_STG.txt")):
        src_path = DECODED_DIR / ko_path.name
        if not src_path.exists():
            continue

        # Load decoded (JP) and translated (KO) by offset
        src_by_offset = load_translations(src_path)
        ko_by_offset = load_translations(ko_path)

        for offset, jp_text in src_by_offset.items():
            ko_text = ko_by_offset.get(offset)
            if not ko_text or ko_text == jp_text:
                continue
            if not KOREAN_RE.search(ko_text):
                continue
            # Only store first occurrence (don't overwrite)
            cache.setdefault(jp_text, ko_text)

    return cache


def load_decoded_entries(stage: str) -> tuple[str | None, list[dict]]:
    """Parse decoded file into header + list of dialogue entries."""
    decoded_path = DECODED_DIR / f"{stage}_STG.txt"
    if not decoded_path.exists():
        print(f"  ERROR: Decoded file not found: {decoded_path}")
        return None, []

    entries: list[dict] = []
    header_line: str | None = None

    for line in decoded_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("#"):
            header_line = line
            continue
        if not line.strip():
            continue
        if CONTEXT_RE.match(line):
            continue  # We'll regenerate context lines
        parsed = parse_dialogue_line(line)
        if parsed:
            entries.append(parsed)

    return header_line, entries


def update_translation(stage: str, text_cache: dict[str, str]) -> bool:
    """Update a single stage's translation file.

    Returns True if successful, False on error.
    """
    print(f"\n{'='*60}")
    print(f"Processing: {stage}")
    print(f"{'='*60}")

    # Load decoded entries (structural template)
    header_line, decoded_entries = load_decoded_entries(stage)
    if not decoded_entries:
        print(f"  No decoded entries for {stage}, skipping.")
        return False

    print(f"  Decoded entries: {len(decoded_entries)}")

    # Load invalid offsets
    invalid_offsets = load_invalid_offsets(stage)
    if invalid_offsets:
        print(f"  Invalid offsets to exclude: {len(invalid_offsets)}")

    # Load existing translations
    translated_path = TRANSLATED_DIR / f"{stage}_STG.txt"
    translations = load_translations(translated_path)
    prev_count = len(translations)
    print(f"  Existing translations loaded: {prev_count}")

    # Filter out invalid entries
    valid_entries = [
        e for e in decoded_entries if e["offset_int"] not in invalid_offsets
    ]
    skipped = len(decoded_entries) - len(valid_entries)
    if skipped:
        print(f"  Skipped invalid entries: {skipped}")
    print(f"  Valid entries: {len(valid_entries)}")

    # Build output with regenerated context lines
    output_lines: list[str] = []
    if header_line:
        output_lines.append(header_line)
        output_lines.append("")

    prev_opcode: str | None = None
    matched_by_offset = 0
    matched_by_cache = 0
    untranslated = 0

    for entry in valid_entries:
        offset = entry["offset_int"]
        opcode = entry["opcode"]

        # Insert context line on speaker/opcode change
        if prev_opcode is not None and opcode != prev_opcode:
            output_lines.append(f"  --- context: {prev_opcode} -> {opcode} ---")

        # Try match by offset first
        if offset in translations and KOREAN_RE.search(translations[offset]):
            output_lines.append(build_dialogue_line(entry, translations[offset]))
            matched_by_offset += 1
        # Try match by JP text cache
        elif entry["text"] in text_cache:
            output_lines.append(build_dialogue_line(entry, text_cache[entry["text"]]))
            matched_by_cache += 1
        else:
            # Keep original (Japanese) text from decoded file
            output_lines.append(build_dialogue_line(entry))
            untranslated += 1

        prev_opcode = opcode

    total_matched = matched_by_offset + matched_by_cache
    print(f"\n  Results:")
    print(f"    Matched by offset:  {matched_by_offset}")
    print(f"    Matched by cache:   {matched_by_cache}")
    print(f"    Total translated:   {total_matched}")
    print(f"    Untranslated (new): {untranslated}")
    print(f"    Total output:       {len(valid_entries)}")

    # Safety check: don't lose existing translations
    if total_matched < prev_count:
        # Count how many previous translations were Korean
        prev_korean = sum(1 for t in translations.values() if KOREAN_RE.search(t))
        if total_matched < prev_korean:
            print(
                f"\n  WARNING: Matched ({total_matched}) < previous Korean "
                f"translations ({prev_korean})!"
            )
            print(f"    Lost translations: {prev_korean - total_matched}")
            print(f"    (This may be expected if entries were reclassified as invalid)")

    # Write output
    print(f"\n  Writing to: {translated_path}")
    translated_path.write_text(
        "\n".join(output_lines) + "\n", encoding="utf-8"
    )
    print(f"  Lines written: {len(output_lines)}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update STG translation files to match decoded structure."
    )
    parser.add_argument(
        "stages",
        nargs="*",
        help="Stage names to process (e.g., SG00 S100 S200)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all stages",
    )
    args = parser.parse_args()

    if args.all:
        stages = ALL_STAGES
    elif args.stages:
        stages = [s.upper() for s in args.stages]
        # Validate stage names
        for s in stages:
            if s not in ALL_STAGES:
                print(f"ERROR: Unknown stage '{s}'. Valid: {', '.join(ALL_STAGES)}")
                return 1
    else:
        parser.print_help()
        return 1

    # Build text cache from all existing translations
    print("Building JP→KO text cache from all translation files...")
    text_cache = build_text_cache()
    print(f"  Cache entries: {len(text_cache)}")

    # Process each stage
    success = 0
    for stage in stages:
        if update_translation(stage, text_cache):
            success += 1

    print(f"\n{'='*60}")
    print(f"Done. Processed {success}/{len(stages)} stages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
