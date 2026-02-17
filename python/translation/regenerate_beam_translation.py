#!/usr/bin/env python3
"""Regenerate BEAM_DAT.txt Korean translation file.

Merges translations from multiple sources with priority ordering:
  1. Backup file (existing complete translations by offset)
  2. Pattern matching (BEAM_DAT_patterns.txt - full-text exact match)
  3. Word-level corrections (BEAM_corrections.txt - garbled→Korean)
  4. Hardcoded character name tables
  5. Original text (kept as-is for untranslated entries)

Usage:
    python python/translation/regenerate_beam_translation.py
    python python/translation/regenerate_beam_translation.py --no-backup  # Skip backup, use patterns only
"""

import os
import re
import sys

# Base directory (project root = atl2_korean_translation/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Input files
DECODED_PATH = os.path.join(BASE_DIR, "output", "decoded", "bin", "BEAM_DAT.txt")
BACKUP_PATH = os.path.join(BASE_DIR, "translated", "ko", "backup_new", "BEAM_DAT.txt")
PATTERNS_PATH = os.path.join(BASE_DIR, "translated", "ko", "BEAM_DAT_patterns.txt")
CORRECTIONS_PATH = os.path.join(BASE_DIR, "translated", "ko", "BEAM_corrections.txt")

# Output file
OUTPUT_PATH = os.path.join(BASE_DIR, "translated", "ko", "BEAM_DAT.txt")

# Entry regex: 2-space indent + 0xOFFSET [LENGTH] text
ENTRY_RE = re.compile(r'^\s*(0x[0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$')

# Box tag stripping regex: removes [box:system], [box:speech], [box:narration], [box:close]
BOX_RE = re.compile(r'\[box:(?:system|speech|narration|close)\]')

# ── Character name tables ────────────────────────────────────────────
# These appear at two locations in BEAM.DAT (Table 1 and Table 2)
CHARACTER_NAMES = {
    'アーク': '아크',
    'ポコ': '포코',
    'トッシュ': '토슈',
    'イーガ': '이가',
    'ゴーゲン': '고겐',
    'エルク': '엘크',
    'リーザ': '리자',
    'シャンテ': '샨테',
    'シュウ': '슈우',
    'ヂークベック': '지크벡',
    'ヂーク': '지크',
    'サニア': '사니아',
    'グルガ': '그루가',
    'ケラック': '케락',
    'モフリー': '모프리',
    'ヘモジー': '헤모지',
    'フウジン': '풍신',
    'ライジン': '뇌신',
    'オドン': '오돈',
    'ククル': '쿠쿠루',
    'ちょこ': '초코',
}

# Character name regions (offsets where name tables appear)
CHAR_NAME_REGIONS = [
    (0x0216C720, 0x0216C780),  # Table 1
    (0x0216ECC0, 0x0216ED20),  # Table 2
]


def read_decoded_entries(path):
    """Read decoded BEAM_DAT.txt, return list of (offset_str, length_str, text)."""
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = ENTRY_RE.match(line)
            if m:
                offset_str = m.group(1)
                length_str = m.group(2)
                text = m.group(3)
                entries.append((offset_str, length_str, text))
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
                offset_str = m.group(1)
                text = m.group(3)
                translations[offset_str] = text
    return translations


def read_patterns(path):
    """Read BEAM_DAT_patterns.txt, return dict of original_text → korean_text."""
    patterns = {}
    if not os.path.exists(path):
        return patterns
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            original, korean = line.split('=', 1)
            patterns[original] = korean
    return patterns


def read_corrections(path):
    """Read BEAM_corrections.txt, return list of (garbled, correct_jp, korean)."""
    corrections = []
    if not os.path.exists(path):
        return corrections
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) == 3:
                garbled, correct_jp, korean = parts
                corrections.append((garbled, correct_jp, korean))
    return corrections


def strip_box_tags(text):
    """Remove [box:system], [box:speech], [box:narration], [box:close] tags."""
    return BOX_RE.sub('', text)


def is_in_char_name_region(offset_str):
    """Check if offset falls within a character name region."""
    offset = int(offset_str, 16)
    for start, end in CHAR_NAME_REGIONS:
        if start <= offset < end:
            return True
    return False


def apply_corrections(text, corrections):
    """Apply word-level garbled→Korean corrections to text.

    Returns corrected text or None if no corrections applied.
    """
    result = text
    applied = False
    for garbled, _correct_jp, korean in corrections:
        if garbled in result:
            result = result.replace(garbled, korean)
            applied = True
    return result if applied else None


def translate_entry(offset_str, length_str, original_text,
                    backup_translations, patterns, corrections):
    """Translate a single entry using the priority cascade.

    Priority:
      1. Backup translation (by offset)
      2. Pattern matching (full-text exact match)
      3. Character name lookup
      4. Word-level corrections
      5. Original text (stripped of box tags)
    """
    # Priority 1: Backup translation
    if offset_str in backup_translations:
        return backup_translations[offset_str], 'backup'

    # Priority 2: Pattern matching (exact full-text match)
    if original_text in patterns:
        translated = patterns[original_text]
        return strip_box_tags(translated), 'pattern'

    # Priority 3: Character names
    stripped = strip_box_tags(original_text)
    if is_in_char_name_region(offset_str) and stripped in CHARACTER_NAMES:
        return CHARACTER_NAMES[stripped], 'charname'

    # Priority 4: Word-level corrections
    corrected = apply_corrections(stripped, corrections)
    if corrected is not None:
        return corrected, 'correction'

    # Priority 5: Keep original (stripped of box tags)
    return stripped, 'original'


def main():
    use_backup = '--no-backup' not in sys.argv

    # Read all sources
    print(f"Reading decoded entries from {DECODED_PATH}...")
    entries = read_decoded_entries(DECODED_PATH)
    print(f"  Found {len(entries)} entries")

    backup_translations = {}
    if use_backup:
        print(f"Reading backup translations from {BACKUP_PATH}...")
        backup_translations = read_backup_translations(BACKUP_PATH)
        print(f"  Found {len(backup_translations)} backup translations")

    print(f"Reading patterns from {PATTERNS_PATH}...")
    patterns = read_patterns(PATTERNS_PATH)
    print(f"  Found {len(patterns)} patterns")

    print(f"Reading corrections from {CORRECTIONS_PATH}...")
    corrections = read_corrections(CORRECTIONS_PATH)
    print(f"  Found {len(corrections)} corrections")

    # Translate all entries
    stats = {'backup': 0, 'pattern': 0, 'charname': 0, 'correction': 0, 'original': 0}
    output_lines = []

    for offset_str, length_str, original_text in entries:
        translated, source = translate_entry(
            offset_str, length_str, original_text,
            backup_translations, patterns, corrections
        )
        stats[source] += 1
        # Format: 2-space indent + offset + [length] + text
        output_lines.append(f"  {offset_str} [{length_str:>4}] {translated}")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# BEAM.DAT — {len(entries)} strings (Korean translations, fully translated)\n")
        f.write("\n")
        for line in output_lines:
            f.write(line + "\n")

    # Print stats
    print(f"\nOutput written to {OUTPUT_PATH}")
    print(f"  Total entries: {len(entries)}")
    print(f"  From backup:     {stats['backup']:>5}")
    print(f"  From patterns:   {stats['pattern']:>5}")
    print(f"  From char names: {stats['charname']:>5}")
    print(f"  From corrections:{stats['correction']:>5}")
    print(f"  Original kept:   {stats['original']:>5}")

    translated_count = stats['backup'] + stats['pattern'] + stats['charname'] + stats['correction']
    print(f"  Translation coverage: {translated_count}/{len(entries)} "
          f"({100*translated_count/len(entries):.1f}%)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
