#!/usr/bin/env python3
"""Regenerate SCPS_100_26.txt Korean translation file.

Merges translations from backup with hardcoded entries for missing character names.

Priority cascade:
  1. Hardcoded translations (3 character names missing from backup)
  2. Backup file (existing translations by offset)
  3. Original text (kept as-is for font test chars, symbols, etc.)

Usage:
    python python/translation/regenerate_scps_translation.py
"""

import os
import re
import sys

# Base directory (project root = atl2_korean_translation/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Input files
DECODED_PATH = os.path.join(BASE_DIR, "output", "decoded", "bin", "SCPS_100_26.txt")
BACKUP_PATH = os.path.join(BASE_DIR, "translated", "ko", "backup_new", "SCPS_100_26.txt")

# Output file
OUTPUT_PATH = os.path.join(BASE_DIR, "translated", "ko", "SCPS_100_26.txt")

# Entry regex: 2-space indent + 0xOFFSET [LENGTH] text
ENTRY_RE = re.compile(r'^\s*(0x[0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$')

# ── Hardcoded translations for entries missing from backup ──────────
# These 3 character names exist in the decoded file but not in backup_new
HARDCODED_TRANSLATIONS = {
    '0x000D2690': '(에러)',       # ゥテ(エラー) — error placeholder
    '0x000D26E6': '풍신',         # フウジン — Wind God
    '0x000D26EC': '뇌신',         # ライジン — Thunder God
}


def read_decoded_entries(path):
    """Read decoded SCPS_100_26.txt, return list of (offset_str, length_str, text)."""
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = ENTRY_RE.match(line)
            if m:
                entries.append((m.group(1), m.group(2), m.group(3)))
    return entries


def read_backup_translations(path):
    """Read backup translation file, return dict of offset_str → translated_text."""
    translations = {}
    if not os.path.exists(path):
        return translations
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = ENTRY_RE.match(line)
            if m:
                translations[m.group(1)] = m.group(3)
    return translations


def translate_entry(offset_str, original_text, backup_translations):
    """Translate a single entry using the priority cascade.

    Priority:
      1. Hardcoded translation (missing character names)
      2. Backup translation (by offset)
      3. Original text (kept as-is)
    """
    # Priority 1: Hardcoded translations
    if offset_str in HARDCODED_TRANSLATIONS:
        return HARDCODED_TRANSLATIONS[offset_str], 'hardcoded'

    # Priority 2: Backup translation
    if offset_str in backup_translations:
        return backup_translations[offset_str], 'backup'

    # Priority 3: Keep original
    return original_text, 'original'


def main():
    # Read all sources
    print(f"Reading decoded entries from {DECODED_PATH}...")
    entries = read_decoded_entries(DECODED_PATH)
    print(f"  Found {len(entries)} entries")

    print(f"Reading backup translations from {BACKUP_PATH}...")
    backup_translations = read_backup_translations(BACKUP_PATH)
    print(f"  Found {len(backup_translations)} backup translations")

    # Translate all entries
    stats = {'hardcoded': 0, 'backup': 0, 'original': 0}
    output_lines = []

    for offset_str, length_str, original_text in entries:
        translated, source = translate_entry(offset_str, original_text, backup_translations)
        stats[source] += 1
        output_lines.append(f"  {offset_str} [{length_str:>4}] {translated}")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# SCPS_100.26 — {len(entries)} strings (Korean translations)\n")
        f.write("\n")
        for line in output_lines:
            f.write(line + "\n")

    # Print stats
    print(f"\nOutput written to {OUTPUT_PATH}")
    print(f"  Total entries: {len(entries)}")
    print(f"  From hardcoded:  {stats['hardcoded']:>5}")
    print(f"  From backup:     {stats['backup']:>5}")
    print(f"  Original kept:   {stats['original']:>5}")

    translated_count = stats['hardcoded'] + stats['backup']
    # Count how many of the translated entries actually contain Korean
    korean_count = 0
    for offset_str, _, original_text in entries:
        translated, source = translate_entry(offset_str, original_text, backup_translations)
        if any('\uAC00' <= ch <= '\uD7A3' for ch in translated):
            korean_count += 1

    print(f"  Korean translations: {korean_count}/{len(entries)} "
          f"({100*korean_count/len(entries):.1f}%)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
