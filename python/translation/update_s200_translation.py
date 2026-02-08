#!/usr/bin/env python3
"""
Update S200_STG.txt translation file to match newly decoded structure.

Merges existing Korean translations with the new decoded file:
1. Uses decoded file as the structural template
2. Substitutes Korean translations by offset
3. Handles shifted offsets (old→new)
4. Removes invalid entries (per invalid report)
5. Fixes duplicate entries
6. Recalculates context lines from actual entry sequence
"""

import re
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECODED_FILE = os.path.join(BASE_DIR, "output/decoded/stg/S200_STG.txt")
TRANSLATED_FILE = os.path.join(BASE_DIR, "translated/ko/S200_STG.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "translated/ko/S200_STG.txt")

# Invalid offsets from S200_STG_invalid_report.txt (to exclude)
INVALID_OFFSETS = {
    # Category 1: Garbage / MIPS Opcodes (34 entries)
    0x003AB5F6, 0x003AB7B4, 0x003AB7D8, 0x003AB7F2,
    0x003AB843, 0x003AB882, 0x003AB892, 0x003AB8AA,
    0x003AB8BC, 0x003ABA2E, 0x003ABA76,
    0x003ABB4A, 0x003ABBDA, 0x003ABE26, 0x003ABE86,
    0x005E05CA, 0x005E0E94, 0x005E106C, 0x005E113E,
    0x005E154A, 0x005E1553, 0x005E1706,
    0x005E24D2, 0x005E2544, 0x005E26A4, 0x005E2792,
    0x005E298A, 0x005E2B5A, 0x005E2BAA,
    0x00C84160, 0x00C84288, 0x00C842B2, 0x00C84298, 0x00C84368,
    # Category 3: Debug / Developer Messages (11 entries)
    0x003ABC02, 0x003ABC0F, 0x003ABC65, 0x003ABC76,
    0x003ABC96, 0x003ABCB8, 0x003ABCD4,
    0x003AC4D8, 0x003AC526, 0x003AC584, 0x003AC604,
}

# Shifted offsets: old_offset → new_offset
OFFSET_SHIFTS = {
    0x0023344A: 0x0023346A,
    0x008151F6: 0x00815206,
    0x00C844B5: 0x00C844B6,
}

# Regex to parse dialogue lines (with [script:XX XX])
DIALOGUE_RE = re.compile(
    r'^(\s+)(0x[0-9A-Fa-f]+)\s+'
    r'\[(0x[0-9A-Fa-f]+)\]\s+'
    r'\[script:([0-9A-Fa-f]+ [0-9A-Fa-f]+)\]'
    r'(.*)'
)

# Regex for dialogue lines WITHOUT [script:XX XX]
DIALOGUE_NOSCRIPT_RE = re.compile(
    r'^(\s+)(0x[0-9A-Fa-f]+)\s+'
    r'\[(0x[0-9A-Fa-f]+)\]\s+'
    r'(?!\[script:)(.*)'
)

CONTEXT_RE = re.compile(r'^\s+--- context: (0x[0-9A-Fa-f]+) -> (0x[0-9A-Fa-f]+) ---')


def parse_dialogue_line(line):
    """Parse a dialogue line into components."""
    m = DIALOGUE_RE.match(line)
    if m:
        return {
            'indent': m.group(1),
            'offset': m.group(2),
            'offset_int': int(m.group(2), 16),
            'opcode': m.group(3),
            'script': m.group(4),
            'text': m.group(5),
        }
    m = DIALOGUE_NOSCRIPT_RE.match(line)
    if m:
        return {
            'indent': m.group(1),
            'offset': m.group(2),
            'offset_int': int(m.group(2), 16),
            'opcode': m.group(3),
            'script': None,
            'text': m.group(4),
        }
    return None


def build_dialogue_line(parsed, text=None):
    """Reconstruct a dialogue line from parsed components."""
    t = text if text is not None else parsed['text']
    if parsed['script']:
        return f"  {parsed['offset']} [{parsed['opcode']}] [script:{parsed['script']}]{t}"
    else:
        return f"  {parsed['offset']} [{parsed['opcode']}] {t}"


def load_translations(filepath):
    """Load offset → korean_text mapping from translated file."""
    translations = {}
    seen_offsets = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\n')
            parsed = parse_dialogue_line(line)
            if parsed:
                offset = parsed['offset_int']
                if offset in seen_offsets:
                    print(f"  WARNING: Duplicate offset {parsed['offset']} at line {line_num} (skipping)")
                    continue
                seen_offsets.add(offset)
                translations[offset] = parsed['text']
    return translations


def main():
    print(f"Loading translations from: {TRANSLATED_FILE}")
    translations = load_translations(TRANSLATED_FILE)
    print(f"  Loaded {len(translations)} unique translations")

    # Add shifted offset mappings
    for old_off, new_off in OFFSET_SHIFTS.items():
        if old_off in translations and new_off not in translations:
            print(f"  Shift: {old_off:#010x} -> {new_off:#010x} (transferring translation)")
            translations[new_off] = translations[old_off]

    print(f"\nProcessing decoded file: {DECODED_FILE}")

    # Parse decoded file into entries (excluding header/blank/context)
    decoded_entries = []  # list of parsed dialogue dicts
    header_line = None

    with open(DECODED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('#'):
                header_line = line
                continue
            if not line.strip():
                continue
            if CONTEXT_RE.match(line):
                continue  # We'll regenerate context lines
            parsed = parse_dialogue_line(line)
            if parsed:
                decoded_entries.append(parsed)

    print(f"  Total decoded entries: {len(decoded_entries)}")

    # Filter out invalid entries
    valid_entries = [e for e in decoded_entries if e['offset_int'] not in INVALID_OFFSETS]
    skipped = len(decoded_entries) - len(valid_entries)
    print(f"  Skipped invalid entries: {skipped}")
    print(f"  Valid entries: {len(valid_entries)}")

    # Build output with regenerated context lines
    output_lines = []
    if header_line:
        # Update header to reflect translation counts
        translated_count = sum(1 for e in valid_entries if e['offset_int'] in translations)
        untranslated_count = len(valid_entries) - translated_count
        output_lines.append(header_line)
        output_lines.append('')

    prev_opcode = None
    matched = 0
    new_entries = 0

    for entry in valid_entries:
        offset = entry['offset_int']
        opcode = entry['opcode']

        # Insert context line on speaker change
        if prev_opcode is not None and opcode != prev_opcode:
            output_lines.append(f"  --- context: {prev_opcode} -> {opcode} ---")

        if offset in translations:
            output_lines.append(build_dialogue_line(entry, translations[offset]))
            matched += 1
        else:
            output_lines.append(build_dialogue_line(entry))
            new_entries += 1

        prev_opcode = opcode

    print(f"\n  Matched translations: {matched}")
    print(f"  New/untranslated entries: {new_entries}")

    # Write output
    print(f"\nWriting to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')

    print(f"  Total lines written: {len(output_lines)}")
    print("\nDone!")

    # Show untranslated entries for review
    if new_entries > 0:
        print(f"\n{'='*60}")
        print(f"NEW/UNTRANSLATED ENTRIES ({new_entries} total):")
        print(f"{'='*60}")
        for entry in valid_entries:
            if entry['offset_int'] not in translations:
                print(f"  {entry['offset']} [{entry['opcode']}] [script:{entry['script']}]{entry['text']}")


if __name__ == '__main__':
    main()
