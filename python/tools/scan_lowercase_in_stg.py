#!/usr/bin/env python3
"""
Scan decoded game text files for standalone lowercase ASCII letters (charIDs 187-212).

These charIDs (bytes 0xBB-0xD4) are being repurposed for Korean Hangul in the translation.
This script checks whether any actual game dialogue uses lowercase a-z, which would conflict.

Approach: Use the already-decoded text files (output of decode_text.py with all 20+ garbage
filter rules applied) as the authoritative source of what the game actually displays.
"""

import os
import re
from pathlib import Path

BASE_DIR = str(Path(__file__).resolve().parents[2] / "output" / "decoded")


def scan_decoded_file(filepath):
    """Scan a decoded text file for lowercase ASCII letters in dialogue text."""
    hits = []
    dialogue_count = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if not line.startswith('  0x'):
                continue

            dialogue_count += 1

            # Extract text after metadata brackets
            m = re.match(r'  0x([0-9A-Fa-f]+) \[.*?\] (.*)', line)
            if not m:
                continue

            offset_str = m.group(1)
            text_part = m.group(2)
            stripped = re.sub(r'\[.*?\]', '', text_part)

            lowercase_chars = [(i, ch) for i, ch in enumerate(stripped) if ch.islower() and ch.isascii()]
            if lowercase_chars:
                hits.append({
                    "line_num": line_num,
                    "offset": offset_str,
                    "chars": [ch for _, ch in lowercase_chars],
                    "stripped": stripped,
                    "full_line": line.rstrip(),
                })

    return dialogue_count, hits


def main():
    print("Lowercase ASCII Letter Scan in Decoded Game Text")
    print("CharIDs 187-212 (bytes 0xBB-0xD4) = a-z")
    print("=" * 100)

    results = {}

    # STG files
    stg_dir = os.path.join(BASE_DIR, "stg")
    for fname in sorted(os.listdir(stg_dir)):
        if fname.endswith('_STG.txt') and 'invalid' not in fname and 'menus' not in fname and not fname.endswith('.md'):
            filepath = os.path.join(stg_dir, fname)
            count, hits = scan_decoded_file(filepath)
            results[fname] = (count, hits)

    # BIN files
    bin_dir = os.path.join(BASE_DIR, "bin")
    for fname in sorted(os.listdir(bin_dir)):
        if fname.endswith('.txt'):
            filepath = os.path.join(bin_dir, fname)
            count, hits = scan_decoded_file(filepath)
            results[fname] = (count, hits)

    # Report
    total_dialogues = sum(c for c, _ in results.values())
    total_hits = sum(len(h["chars"]) for _, hits in results.values() for h in hits)

    for fname in sorted(results.keys()):
        count, hits = results[fname]
        hit_count = sum(len(h["chars"]) for h in hits)
        if hits:
            print(f"\n{fname}: {hit_count} lowercase letters / {count} dialogues")
            for h in hits:
                print(f"  0x{h['offset']} [{','.join(h['chars'])}] {h['stripped'][:100]}")
        else:
            print(f"{fname}: 0 / {count}")

    print(f"\n{'='*100}")
    print(f"TOTAL: {total_hits} lowercase letters across {total_dialogues} dialogues")

    if total_hits > 0:
        letter_freq = {}
        for _, hits in results.values():
            for h in hits:
                for ch in h["chars"]:
                    letter_freq[ch] = letter_freq.get(ch, 0) + 1
        print(f"\nLetter frequency: {dict(sorted(letter_freq.items()))}")


if __name__ == "__main__":
    main()
