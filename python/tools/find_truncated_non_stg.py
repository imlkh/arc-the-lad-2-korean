#!/usr/bin/env python3
"""Find truncated entries in non-STG translation files (SCPS_100.26, BEAM.DAT).

Reports every entry where the Korean translation exceeds the original Japanese
byte count, with per-character byte cost annotation to help identify which
characters to shorten.

Usage:
    python python/tools/find_truncated_non_stg.py              # Both files
    python python/tools/find_truncated_non_stg.py --scps       # SCPS only
    python python/tools/find_truncated_non_stg.py --beam       # BEAM only
    python python/tools/find_truncated_non_stg.py -o report.txt  # Save to file
"""

import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)  # python/
PATCH_DIR = os.path.join(PYTHON_DIR, "patch")
sys.path.insert(0, PATCH_DIR)

from patch_korean import (
    load_decode_table, encode_korean_text, parse_bin_translation_file,
    build_encode_table, char_id_to_bytes, BASE_DIR, OUTPUT_DIR,
)

TRANSLATED_DIR = os.path.join(BASE_DIR, "translated", "ko")


def load_unified_charmap():
    """Load the unified Korean character mapping from unified_charmap.txt."""
    charmap_path = os.path.join(OUTPUT_DIR, "unified_charmap.txt")
    if not os.path.exists(charmap_path):
        print(f"ERROR: unified_charmap.txt not found at {charmap_path}")
        print("       Run patch_all.py first to create the unified character mapping.")
        sys.exit(1)

    korean_mapping = {}
    with open(charmap_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                try:
                    korean_mapping[parts[0]] = int(parts[1])
                except (ValueError, IndexError):
                    continue
    return korean_mapping


def char_byte_cost(ch, korean_mapping, encode_table):
    """Return the encoded byte cost for a single visible character.

    Returns (cost, is_two_byte) where is_two_byte indicates the char
    uses a 2-byte charID (kanji-range slot).
    """
    # Korean character
    if ch in korean_mapping:
        char_id = korean_mapping[ch]
        encoded = char_id_to_bytes(char_id)
        cost = len(encoded) if encoded else 0
        return cost, cost == 2

    # Preserved character (Latin, digit, symbol)
    if ch in encode_table:
        char_id = encode_table[ch]
        encoded = char_id_to_bytes(char_id)
        cost = len(encoded) if encoded else 0
        return cost, cost == 2

    # Punctuation (same map as encode_korean_text)
    punct_map = {
        "、": 0xE4, "。": 0xEC, "！": 0xED, "？": 0xEE,
        "…": 0xE5, "・": 250, "ー": 0xE3, "～": 0xEA,
        "(": 245, ")": 246, "「": 251, "」": 252,
        ",": 247, ".": 248, ":": 249,
        "?": 0xEE, "!": 0xED, "~": 0xEA, "-": 0xE7,
        "/": 232, "／": 232, '"': 235,
    }
    if ch in punct_map:
        char_id = punct_map[ch]
        if char_id is not None:
            encoded = char_id_to_bytes(char_id)
            cost = len(encoded) if encoded else 0
            return cost, cost == 2
        return 0, False  # space mapped to None

    # Space -> skipped (0 bytes)
    if ch == " ":
        return 0, False

    return 0, False


def analyze_text_bytes(text, korean_mapping, decode_table, encode_table):
    """Analyze a translation text and return per-character byte costs.

    Returns list of (char_or_tag, byte_cost, is_two_byte, is_control).
    Control codes are returned as their full tag string.
    """
    # Normalize like encode_korean_text does
    text = text.replace("...", "…")
    text = text.replace("..", "…")

    result = []
    i = 0
    while i < len(text):
        ch = text[i]

        # Newline
        if ch == "\n":
            result.append(("\\n", 4, False, True))
            i += 1
            continue

        # Literal \n
        if ch == "\\" and i + 1 < len(text) and text[i + 1] == "n":
            result.append(("\\n", 4, False, True))
            i += 2
            continue

        # Control code tags
        if ch == "[":
            end = text.find("]", i)
            if end != -1:
                tag = text[i : end + 1]
                tag_inner = text[i + 1 : end]

                # Calculate tag byte cost (same logic as encode_korean_text)
                cost = 0
                if tag_inner.startswith("delay:"):
                    cost = 4
                elif tag_inner.startswith("box:"):
                    cost = 4
                    if tag_inner == "box:speech":
                        cost = 5  # includes 0xA0 space byte at string start
                elif tag_inner == "cursor":
                    cost = 4
                elif tag_inner == "br":
                    cost = 4
                elif tag_inner == "opt":
                    cost = 1
                elif tag_inner.startswith("FF:"):
                    parts = tag_inner[3:].split()
                    cost = 1 + len(parts)  # 0xFF + each byte
                elif tag_inner.startswith("num:"):
                    cost = 4
                elif tag_inner.startswith("item:"):
                    cost = 4
                elif tag_inner.startswith("name:"):
                    cost = 4

                result.append((tag, cost, False, True))
                i = end + 1
                continue

        # Regular character
        cost, is_two = char_byte_cost(ch, korean_mapping, encode_table)
        result.append((ch, cost, is_two, False))
        i += 1

    return result


def format_entry_report(entry, char_analysis, encoded_len, overflow):
    """Format a single truncated entry report."""
    lines = []
    offset = entry["offset"]
    orig_len = entry["orig_length"]
    text = entry["text"]

    lines.append(f"  0x{offset:08X} [orig: {orig_len}B, korean: {encoded_len}B, overflow: {overflow}B]")
    lines.append(f"  Korean: {text}")

    # Build byte cost annotation (only visible chars, skip controls)
    visible_chars = [(ch, cost, is_two) for ch, cost, is_two, is_ctrl in char_analysis if not is_ctrl]
    two_byte_chars = [(ch, cost) for ch, cost, is_two in visible_chars if is_two]

    if visible_chars:
        cost_str = " ".join(str(cost) for _, cost, _ in visible_chars)
        total_visible = sum(cost for _, cost, _ in visible_chars)
        total_control = sum(cost for _, cost, _, is_ctrl in char_analysis if is_ctrl)

        two_byte_list = ", ".join(ch for ch, _ in two_byte_chars) if two_byte_chars else "none"
        lines.append(f"  Bytes:  {cost_str}  = {total_visible} visible + {total_control} control (2-byte: {two_byte_list})")

    # Actionable suggestion
    if overflow <= 2 and len(two_byte_chars) >= 1:
        lines.append(f"  → Shorten by {overflow}B: replace {len(two_byte_chars)} available 2-byte char(s) with shorter synonyms")
    elif overflow <= 5:
        lines.append(f"  → Shorten by {overflow}B: abbreviate or use shorter wording")
    else:
        lines.append(f"  → Shorten by {overflow}B: significant rewrite needed")

    return "\n".join(lines)


def analyze_file(file_label, translation_path, korean_mapping, decode_table):
    """Analyze a translation file and return (report_text, stats_dict)."""
    if not os.path.exists(translation_path):
        return f"  File not found: {translation_path}\n", None

    entries = parse_bin_translation_file(translation_path)
    encode_table = build_encode_table(decode_table)

    truncated = []
    overflow_buckets = {"1-2": 0, "3-5": 0, "6-10": 0, "11+": 0}
    total_overflow = 0
    total_with_orig = 0

    for entry in entries:
        if entry.get("orig_length") is None:
            continue
        total_with_orig += 1

        encoded = encode_korean_text(entry["text"], korean_mapping, decode_table)
        encoded_len = len(encoded)
        orig_len = entry["orig_length"]

        if encoded_len > orig_len:
            overflow = encoded_len - orig_len
            total_overflow += overflow
            char_analysis = analyze_text_bytes(entry["text"], korean_mapping, decode_table, encode_table)

            truncated.append({
                "entry": entry,
                "encoded_len": encoded_len,
                "overflow": overflow,
                "char_analysis": char_analysis,
            })

            if overflow <= 2:
                overflow_buckets["1-2"] += 1
            elif overflow <= 5:
                overflow_buckets["3-5"] += 1
            elif overflow <= 10:
                overflow_buckets["6-10"] += 1
            else:
                overflow_buckets["11+"] += 1

    # Sort by overflow descending for prioritization
    truncated.sort(key=lambda x: x["overflow"], reverse=True)

    lines = []
    pct = (len(truncated) / total_with_orig * 100) if total_with_orig else 0
    avg = (total_overflow / len(truncated)) if truncated else 0

    lines.append(f"=== {file_label}: {len(truncated)} truncated entries (of {total_with_orig}) ===")
    lines.append(f"    Overflow: {pct:.1f}% | Avg: {avg:.1f}B | Total: {total_overflow}B")
    lines.append(f"    Buckets: 1-2B: {overflow_buckets['1-2']} | 3-5B: {overflow_buckets['3-5']} | 6-10B: {overflow_buckets['6-10']} | 11+B: {overflow_buckets['11+']}")
    lines.append("")

    for item in truncated:
        lines.append(format_entry_report(
            item["entry"], item["char_analysis"],
            item["encoded_len"], item["overflow"],
        ))
        lines.append("")

    stats = {
        "total": total_with_orig,
        "truncated": len(truncated),
        "pct": pct,
        "avg_overflow": avg,
        "total_overflow": total_overflow,
        "buckets": overflow_buckets,
    }

    return "\n".join(lines), stats


def main():
    parser = argparse.ArgumentParser(description="Find truncated non-STG translations")
    parser.add_argument("--scps", action="store_true", help="Only analyze SCPS_100.26")
    parser.add_argument("--beam", action="store_true", help="Only analyze BEAM.DAT")
    parser.add_argument("-o", "--output", help="Save report to file")
    args = parser.parse_args()

    # Default: both files
    if not args.scps and not args.beam:
        args.scps = True
        args.beam = True

    print("Loading character tables...")
    decode_table = load_decode_table()
    korean_mapping = load_unified_charmap()
    print(f"  Loaded {len(korean_mapping)} Korean character mappings")
    print()

    reports = []

    if args.scps:
        scps_path = os.path.join(TRANSLATED_DIR, "SCPS_100_26.txt")
        report, stats = analyze_file("SCPS_100.26", scps_path, korean_mapping, decode_table)
        reports.append(report)

    if args.beam:
        beam_path = os.path.join(TRANSLATED_DIR, "BEAM_DAT.txt")
        report, stats = analyze_file("BEAM.DAT", beam_path, korean_mapping, decode_table)
        reports.append(report)

    full_report = "\n".join(reports)
    print(full_report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(full_report)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
