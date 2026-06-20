#!/usr/bin/env python3
"""
Search decoded STG text files for any lowercase ASCII letters.
These files contain the actual game dialogue text that passed all garbage filters.
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DECODED_DIR = str(BASE_DIR / "output" / "decoded" / "stg")

def scan_file(filepath):
    """Scan a decoded STG text file for lowercase ASCII letters in dialogue text."""
    filename = os.path.basename(filepath)
    hits = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\n')

            # Skip comment/header lines
            if line.startswith('#') or line.startswith('---') or not line.strip():
                continue

            # Dialogue lines have format: "  0xOFFSET [OPCODE] text..."
            # or "  0xOFFSET [OPCODE] [script:XX YY]text..."
            if not line.startswith('  0x'):
                continue

            # Extract the text portion (after all the leading metadata)
            # Format: "  0x000B36F6 [0x00B0] [script:AE 01][box:system]text..."
            # We need to strip control tags and look at the actual rendered text

            # Get everything after the opcode bracket
            m = re.match(r'  0x[0-9A-F]+ \[0x[0-9A-F]+\] (.*)', line)
            if not m:
                continue

            text_part = m.group(1)

            # Strip all [...] tags to get raw text
            stripped = re.sub(r'\[.*?\]', '', text_part)

            # Check for lowercase ASCII letters
            for i, ch in enumerate(stripped):
                if ch.islower() and ch.isascii():
                    # Get surrounding context
                    ctx_start = max(0, i - 10)
                    ctx_end = min(len(stripped), i + 11)
                    context = stripped[ctx_start:ctx_end]

                    hits.append({
                        "line_num": line_num,
                        "char": ch,
                        "position": i,
                        "context": context,
                        "full_text": text_part[:100],
                        "stripped": stripped[:100],
                    })

    return filename, hits


def main():
    print("Scanning decoded STG text files for lowercase ASCII letters")
    print("=" * 100)

    stg_files = sorted([
        os.path.join(DECODED_DIR, f)
        for f in os.listdir(DECODED_DIR)
        if f.endswith('_STG.txt') and 'invalid' not in f and 'menus' not in f
    ])

    total_hits = 0
    total_dialogues = 0

    for filepath in stg_files:
        filename, hits = scan_file(filepath)

        # Count total dialogues
        with open(filepath, 'r', encoding='utf-8') as f:
            dialogue_count = sum(1 for line in f if line.startswith('  0x'))

        total_dialogues += dialogue_count

        if hits:
            print(f"\n{filename}: {len(hits)} lowercase letters in {dialogue_count} dialogues")
            # Group by unique dialogue line
            seen_lines = {}
            for h in hits:
                key = h["line_num"]
                if key not in seen_lines:
                    seen_lines[key] = {
                        "line_num": h["line_num"],
                        "chars": [],
                        "full_text": h["full_text"],
                        "stripped": h["stripped"],
                    }
                seen_lines[key]["chars"].append(h["char"])

            for key in sorted(seen_lines.keys()):
                info = seen_lines[key]
                chars = ''.join(info["chars"])
                print(f"  Line {info['line_num']:5d}: [{chars}] {info['stripped'][:80]}")

            total_hits += len(hits)
        else:
            print(f"{filename}: 0 lowercase letters in {dialogue_count} dialogues")

    print("\n" + "=" * 100)
    print(f"TOTAL: {total_hits} lowercase letters across {total_dialogues} dialogues in {len(stg_files)} files")

    if total_hits == 0:
        print("\nCONCLUSION: No lowercase ASCII letters found in any decoded game dialogue.")
        print("The charID range 187-212 (bytes 0xBB-0xD4) is safe to repurpose for Korean Hangul.")
    else:
        print(f"\nWARNING: {total_hits} lowercase letters found in game dialogue!")
        print("These charIDs cannot be safely repurposed without handling conflicts.")


if __name__ == "__main__":
    main()
