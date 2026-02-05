#!/usr/bin/env python3
"""
Extract unique Korean (Hangul syllable) characters from translated text files.

Usage:
    python extract_unique_korean.py

Output: translated/ko/unique_korean_chars.txt
"""

import glob
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KO_DIR = os.path.join(_SCRIPT_DIR, "..", "..", "translated", "ko")
OUTPUT_PATH = os.path.join(KO_DIR, "unique_korean_chars.txt")


def main():
    files = sorted(glob.glob(os.path.join(KO_DIR, "*.txt")))
    # Exclude our own output file
    files = [f for f in files if os.path.basename(f) != "unique_korean_chars.txt"]
    print(f"Found {len(files)} Korean translation files")

    korean_chars = set()
    for f in files:
        text = open(f, "r", encoding="utf-8").read()
        for ch in text:
            # Korean Hangul Syllables: U+AC00-U+D7A3
            if "\uAC00" <= ch <= "\uD7A3":
                korean_chars.add(ch)

    sorted_chars = sorted(korean_chars)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("".join(sorted_chars))
        f.write("\n")

    print(f"Unique Korean characters: {len(sorted_chars)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
