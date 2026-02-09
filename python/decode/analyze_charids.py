#!/usr/bin/env python3
"""
Analyze charID usage across different game files.

Compares which charIDs (and their byte sequences) are used in BEAM.DAT,
SCPS_100.26, and STG files to identify differences in text encoding.

Usage:
    python analyze_charids.py                    # Full analysis
    python analyze_charids.py --char 行          # Find specific character
    python analyze_charids.py --word 行きます    # Find specific word
    python analyze_charids.py --compare          # Compare BEAM vs STG usage
    python analyze_charids.py --korean 702       # Find Korean charID usage in translations
    python analyze_charids.py --korean 쏟        # Find Korean character usage in translations
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(_SCRIPT_DIR, "..", "..")
CHARS_MD_PATH = os.path.join(BASE_DIR, "docs", "COMM_IMG_chars.md")
GAME_DIR = os.path.join(BASE_DIR, "..")
CHARMAP_PATH = os.path.join(BASE_DIR, "output", "patched", "unified_charmap.txt")
TRANS_DIR = os.path.join(BASE_DIR, "output", "patched", "translation")


def build_tables():
    """Build charID <-> character mapping tables."""
    id_to_char = {}
    char_to_id = {}

    text = open(CHARS_MD_PATH, "r", encoding="utf-8").read()
    pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        r"\s*\(\d+,\d+\)\s*\|\s*\d+\s*\|"
        r"\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    )
    # Pattern to strip charID suffix like " (123)" from new format
    charid_suffix = re.compile(r'\s*\(\d+\)\s*$')
    for m in pattern.finditer(text):
        row = int(m.group(2))
        col = int(m.group(3))
        bits = [m.group(i).strip() for i in range(4, 8)]
        for bitplane, label in enumerate(bits):
            # Strip charID suffix first
            label_clean = charid_suffix.sub('', label).strip()
            if not label_clean or label_clean.lower() in ('(blank)', 'blank', ''):
                continue
            char_id = 1 + (row * 21 + col) * 4 + bitplane
            clean = label_clean.rstrip("?").strip()
            if clean:
                id_to_char[char_id] = clean
                if clean not in char_to_id:
                    char_to_id[clean] = char_id
    return id_to_char, char_to_id


def load_korean_charmap():
    """Load unified_charmap.txt -> (charID_to_korean, korean_to_charID)."""
    id_to_kr = {}
    kr_to_id = {}
    if not os.path.exists(CHARMAP_PATH):
        return id_to_kr, kr_to_id
    with open(CHARMAP_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                kr_char = parts[0]
                char_id = int(parts[1])
                id_to_kr[char_id] = kr_char
                kr_to_id[kr_char] = char_id
    return id_to_kr, kr_to_id


def find_korean_in_translations(target_char):
    """Search all translation files for a Korean character. Returns per-file results."""
    results = {}
    if not os.path.exists(TRANS_DIR):
        return results
    for fname in sorted(os.listdir(TRANS_DIR)):
        if not fname.endswith('.txt'):
            continue
        fpath = os.path.join(TRANS_DIR, fname)
        matches = []
        with open(fpath, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                if target_char in line:
                    matches.append((lineno, line.rstrip()))
        if matches:
            results[fname] = matches
    return results


def char_id_to_bytes(char_id):
    """Convert charID to byte sequence."""
    if 1 <= char_id <= 0xEE:
        return bytes([char_id])
    elif char_id >= 239:
        first = 0xF0 + (char_id - 239) // 255
        second = (char_id - 239) % 255
        return bytes([first, second])
    return None


def bytes_to_char_id(data, pos):
    """Extract charID from bytes at position. Returns (charID, bytes_consumed)."""
    if pos >= len(data):
        return None, 0
    b = data[pos]
    if b == 0x00 or b == 0xFF:
        return None, 0
    if 0x01 <= b <= 0xEE:
        return b, 1
    if 0xF0 <= b <= 0xFE and pos + 1 < len(data):
        second = data[pos + 1]
        char_id = (b - 0xF0) * 255 + second + 239
        return char_id, 2
    return None, 0


def extract_charids_from_file(filepath, use_ff08=False):
    """Extract all charIDs used in a file.

    Returns dict of {charID: count}
    """
    data = open(filepath, "rb").read()
    counts = Counter()

    if use_ff08:
        # Only scan after FF 08 markers (dialogue regions)
        pos = 0
        while True:
            idx = data.find(b'\xFF\x08', pos)
            if idx == -1:
                break
            # Scan the dialogue after the marker
            scan_pos = idx + 4  # Skip FF 08 XX XX
            while scan_pos < len(data) and scan_pos < idx + 500:  # Limit scan range
                b = data[scan_pos]
                if b == 0x00:
                    break
                if b == 0xFF:
                    scan_pos += 4
                    continue
                char_id, consumed = bytes_to_char_id(data, scan_pos)
                if char_id:
                    counts[char_id] += 1
                    scan_pos += consumed
                else:
                    scan_pos += 1
            pos = idx + 1
    else:
        # Full scan
        pos = 0
        while pos < len(data):
            char_id, consumed = bytes_to_char_id(data, pos)
            if char_id and consumed > 0:
                counts[char_id] += 1
                pos += consumed
            else:
                pos += 1

    return counts


def find_char_in_file(filepath, target_char, char_to_id, id_to_char):
    """Find all occurrences of a character in a file with context."""
    target_id = char_to_id.get(target_char)
    if not target_id:
        return []

    target_bytes = char_id_to_bytes(target_id)
    data = open(filepath, "rb").read()

    occurrences = []
    pos = 0
    while True:
        idx = data.find(target_bytes, pos)
        if idx == -1:
            break

        # Get context (decode surrounding bytes)
        start = max(0, idx - 10)
        end = min(len(data), idx + 20)
        context_bytes = data[start:end]

        # Decode context
        context_chars = []
        cpos = 0
        while cpos < len(context_bytes):
            char_id, consumed = bytes_to_char_id(context_bytes, cpos)
            if char_id and char_id in id_to_char:
                context_chars.append(id_to_char[char_id])
                cpos += consumed
            else:
                context_chars.append('·')
                cpos += 1

        occurrences.append({
            'offset': idx,
            'context': ''.join(context_chars),
            'hex': context_bytes.hex()
        })
        pos = idx + 1

    return occurrences


def find_word_in_file(filepath, word, char_to_id, id_to_char):
    """Find a word by its byte sequence in a file."""
    # Convert word to expected byte sequence
    word_bytes = b''
    for char in word:
        char_id = char_to_id.get(char)
        if char_id:
            word_bytes += char_id_to_bytes(char_id)
        else:
            return []  # Character not in table

    data = open(filepath, "rb").read()
    occurrences = []
    pos = 0
    while True:
        idx = data.find(word_bytes, pos)
        if idx == -1:
            break
        occurrences.append({
            'offset': idx,
            'bytes': word_bytes.hex()
        })
        pos = idx + 1

    return occurrences


def main():
    parser = argparse.ArgumentParser(description="Analyze charID usage across game files")
    parser.add_argument("--char", help="Find specific character across files")
    parser.add_argument("--word", help="Find specific word across files")
    parser.add_argument("--compare", action="store_true", help="Compare BEAM.DAT vs STG charID usage")
    parser.add_argument("--korean", help="Find Korean charID usage in translation files (charID number or Korean character)")
    parser.add_argument("--top", type=int, default=20, help="Show top N charIDs (default: 20)")
    args = parser.parse_args()

    # Handle --korean early (doesn't need Japanese tables)
    if args.korean:
        id_to_kr, kr_to_id = load_korean_charmap()
        if not id_to_kr:
            print(f"ERROR: Korean charmap not found: {CHARMAP_PATH}")
            print("  Run patch_all.py first to generate it.")
            return

        # Determine target: charID number or Korean character
        target_char = None
        target_id = None
        try:
            target_id = int(args.korean)
            target_char = id_to_kr.get(target_id)
            if not target_char:
                print(f"CharID {target_id} is not mapped to any Korean character.")
                return
        except ValueError:
            target_char = args.korean
            target_id = kr_to_id.get(target_char)
            if not target_id:
                print(f"Character '{target_char}' not found in Korean charmap.")
                return

        target_bytes = char_id_to_bytes(target_id)
        byte_str = ' '.join(f'{b:02X}' for b in target_bytes) if target_bytes else '??'
        encoding_type = "single-byte" if target_id <= 0xEE else "two-byte"

        print(f"Character: {target_char} (U+{ord(target_char):04X})")
        print(f"CharID:    {target_id}")
        print(f"Encoding:  {byte_str} ({encoding_type})")
        print()

        # Search translation files
        results = find_korean_in_translations(target_char)
        if not results:
            print("Not found in any translation file.")
            return

        total = sum(len(matches) for matches in results.values())
        print(f"Found in {len(results)} file(s), {total} line(s):\n")

        for fname, matches in results.items():
            print(f"  {fname} ({len(matches)} lines):")
            for lineno, line in matches[:10]:
                print(f"    L{lineno}: {line.strip()[:80]}")
            if len(matches) > 10:
                print(f"    ... and {len(matches) - 10} more")
            print()
        return

    id_to_char, char_to_id = build_tables()
    print(f"Loaded {len(id_to_char)} character mappings\n")

    # File paths
    beam_path = os.path.join(GAME_DIR, "BEAM.DAT")
    scps_path = os.path.join(GAME_DIR, "SCPS_100.26")
    stg_dir = GAME_DIR

    if args.char:
        # Find specific character
        target = args.char
        target_id = char_to_id.get(target)
        if not target_id:
            print(f"Character '{target}' not found in table")
            return

        target_bytes = char_id_to_bytes(target_id)
        print(f"Character: {target}")
        print(f"CharID: {target_id}")
        print(f"Bytes: {target_bytes.hex().upper()}")
        print()

        for filepath, name in [(beam_path, "BEAM.DAT"), (scps_path, "SCPS_100.26")]:
            if os.path.exists(filepath):
                occs = find_char_in_file(filepath, target, char_to_id, id_to_char)
                print(f"{name}: {len(occs)} occurrences")
                for occ in occs[:5]:
                    print(f"  0x{occ['offset']:08X}: {occ['context']}")
                if len(occs) > 5:
                    print(f"  ... and {len(occs) - 5} more")
                print()

        # Check STG files
        stg_count = 0
        for fname in sorted(os.listdir(stg_dir)):
            if fname.endswith('.STG'):
                fpath = os.path.join(stg_dir, fname)
                occs = find_char_in_file(fpath, target, char_to_id, id_to_char)
                stg_count += len(occs)
        print(f"STG files (total): {stg_count} occurrences")

    elif args.word:
        # Find specific word
        word = args.word
        print(f"Searching for word: {word}")

        # Show expected byte sequence
        word_bytes = b''
        for char in word:
            char_id = char_to_id.get(char)
            if char_id:
                word_bytes += char_id_to_bytes(char_id)
                print(f"  {char} -> charID {char_id} -> {char_id_to_bytes(char_id).hex().upper()}")
            else:
                print(f"  {char} -> NOT FOUND")
        print(f"Expected bytes: {word_bytes.hex().upper()}")
        print()

        for filepath, name in [(beam_path, "BEAM.DAT"), (scps_path, "SCPS_100.26")]:
            if os.path.exists(filepath):
                occs = find_word_in_file(filepath, word, char_to_id, id_to_char)
                print(f"{name}: {len(occs)} occurrences")
                for occ in occs[:5]:
                    print(f"  0x{occ['offset']:08X}")

        # Check STG files
        stg_total = 0
        for fname in sorted(os.listdir(stg_dir)):
            if fname.endswith('.STG'):
                fpath = os.path.join(stg_dir, fname)
                occs = find_word_in_file(fpath, word, char_to_id, id_to_char)
                if occs:
                    print(f"{fname}: {len(occs)} occurrences")
                    stg_total += len(occs)
        print(f"\nSTG total: {stg_total} occurrences")

    elif args.compare:
        # Compare charID usage between BEAM.DAT and STG files
        print("Extracting charIDs from BEAM.DAT (FF08 regions)...")
        beam_counts = extract_charids_from_file(beam_path, use_ff08=True)

        print("Extracting charIDs from STG files...")
        stg_counts = Counter()
        for fname in sorted(os.listdir(stg_dir)):
            if fname.endswith('.STG'):
                fpath = os.path.join(stg_dir, fname)
                stg_counts.update(extract_charids_from_file(fpath, use_ff08=True))

        # Find charIDs unique to each
        beam_only = set(beam_counts.keys()) - set(stg_counts.keys())
        stg_only = set(stg_counts.keys()) - set(beam_counts.keys())
        common = set(beam_counts.keys()) & set(stg_counts.keys())

        print(f"\nCharID comparison:")
        print(f"  BEAM.DAT unique: {len(beam_only)}")
        print(f"  STG unique: {len(stg_only)}")
        print(f"  Common: {len(common)}")

        print(f"\nTop {args.top} charIDs in BEAM.DAT (by frequency):")
        for char_id, count in beam_counts.most_common(args.top):
            char = id_to_char.get(char_id, '?')
            in_stg = "✓" if char_id in stg_counts else "✗"
            print(f"  {char_id:5d} ({char}) x{count:5d}  STG:{in_stg}")

        print(f"\nCharIDs in BEAM.DAT but rare/absent in STG (potential placeholders):")
        for char_id in sorted(beam_only):
            char = id_to_char.get(char_id, '?')
            count = beam_counts[char_id]
            if count >= 10:  # Only show if used frequently
                print(f"  {char_id:5d} ({char}) x{count}")

    else:
        # Default: show charID stats for each file
        print("CharID usage statistics:\n")

        for filepath, name, use_ff08 in [
            (beam_path, "BEAM.DAT", True),
            (scps_path, "SCPS_100.26", False),
        ]:
            if os.path.exists(filepath):
                counts = extract_charids_from_file(filepath, use_ff08=use_ff08)
                print(f"{name}:")
                print(f"  Unique charIDs: {len(counts)}")
                print(f"  Total chars: {sum(counts.values())}")
                print(f"  Top {args.top}:")
                for char_id, count in counts.most_common(args.top):
                    char = id_to_char.get(char_id, '?')
                    byte_repr = char_id_to_bytes(char_id).hex().upper()
                    print(f"    {char_id:5d} {byte_repr:8s} {char:4s} x{count}")
                print()


if __name__ == "__main__":
    main()
