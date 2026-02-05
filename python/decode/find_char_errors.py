#!/usr/bin/env python3
"""
Find placeholder/debug text patterns in decoded game files.

Identifies text that uses placeholder kanji sequences found in BEAM.DAT's
shared template region. These are NOT character table errors -- the character
table is verified correct. Instead, these patterns indicate debug/placeholder
content that differs from the final game text in STG files.

See docs/COMM_IMG_corrections.md for verification details.

Usage:
    python find_char_errors.py
"""

import os
import re

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "output", "decoded")

# Patterns that identify placeholder/debug text in BEAM.DAT
# These use different charIDs than the equivalent text in STG files
# Format: (pattern_regex, description)
PLACEHOLDER_PATTERNS = [
    # Placeholder verbs (BEAM.DAT uses different chars than STG)
    (r'[切獅告](?:り|る|ます)', 'Placeholder go/climb/descend verbs (切=行, 獅=上, 告=下)'),
    (r'[協狭](?:り|つけ)', 'Placeholder find/take verbs (協=見, 狭=取)'),
    (r'[償簡抱跡](?:に|を|が)', 'Placeholder particles (償=本当, 跡=手, 抱=入)'),
    (r'[温慎鈴堕西](?:があります|がある)', 'Placeholder nouns (温慎=階段, 西鈴=宝箱)'),

    # Code bytes decoded as text (not placeholder, actual garbage)
    (r'[ぁ-んァ-ン][A-Za-z][ぁ-んァ-ン]', 'Latin mixed with Japanese (MIPS code bytes)'),
    (r'ギ{3,}', 'Repeated ギ (common MIPS code pattern)'),

    # Rare kanji sequences (may indicate code bytes or unusual text)
    (r'[哭泣獅殴凪薙慵鏜涎嚙]{2,}', 'Multiple rare kanji in sequence'),
]


def scan_file(filepath):
    """Scan a decoded text file for placeholder patterns."""
    issues = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Extract the text portion (after offset and length)
            match = re.search(r'\[\s*\d+\]\s*(.+)$', line)
            if not match:
                continue
            text = match.group(1)

            for pattern, description in PLACEHOLDER_PATTERNS:
                m = re.search(pattern, text)
                if m:
                    issues.append({
                        'file': os.path.basename(filepath),
                        'line': line_num,
                        'text': text[:80],
                        'match': m.group(0),
                        'issue': description
                    })
    return issues


def main():
    all_issues = []

    # Scan BIN files
    bin_dir = os.path.join(OUTPUT_DIR, "bin")
    if os.path.exists(bin_dir):
        for fname in sorted(os.listdir(bin_dir)):
            if fname.endswith('.txt'):
                filepath = os.path.join(bin_dir, fname)
                issues = scan_file(filepath)
                all_issues.extend(issues)

    # Scan STG files
    stg_dir = os.path.join(OUTPUT_DIR, "stg")
    if os.path.exists(stg_dir):
        for fname in sorted(os.listdir(stg_dir)):
            if fname.endswith('.txt'):
                filepath = os.path.join(stg_dir, fname)
                issues = scan_file(filepath)
                all_issues.extend(issues)

    if not all_issues:
        print("No placeholder/debug patterns found.")
        return

    # Group by issue type
    by_issue = {}
    for item in all_issues:
        key = item['issue']
        if key not in by_issue:
            by_issue[key] = []
        by_issue[key].append(item)

    print(f"Found {len(all_issues)} placeholder/debug text occurrences:\n")

    for issue_type, items in sorted(by_issue.items(), key=lambda x: -len(x[1])):
        print(f"=== {issue_type} ({len(items)} occurrences) ===")
        # Show first 5 examples
        for item in items[:5]:
            print(f"  {item['file']}:{item['line']}")
            print(f"    Match: {item['match']}")
            print(f"    Text: {item['text'][:60]}...")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
        print()

    # Summary
    print("=" * 70)
    print("NOTE: These are NOT character table errors.")
    print("The character table (COMM_IMG_chars.md) is verified correct.")
    print("These patterns identify placeholder/debug text in BEAM.DAT that")
    print("uses different byte sequences than the final game text in STG files.")
    print("See docs/COMM_IMG_corrections.md for details.")


if __name__ == "__main__":
    main()
