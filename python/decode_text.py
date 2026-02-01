#!/usr/bin/env python3
"""
Decode Arc the Lad 2 dialogue text from binary game files.

Usage:
    python decode_text.py <file> <offset>          # decode one string at offset
    python decode_text.py <file> --scan            # find and decode all text strings
    python decode_text.py <file> --find "ますか"    # find strings containing a pattern
"""

import argparse
import os
import re
import sys

# === Constants ===
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARS_MD_PATH = os.path.join(_SCRIPT_DIR, "..", "COMM_IMG_chars.md")

# Minimum consecutive valid characters to consider a run as text
MIN_TEXT_RUN = 3


def build_decode_table():
    """Parse COMM_IMG_chars.md and build charID -> character mapping.

    Uses the same regex approach as view_char.py.
    Formula: charID = 1 + (row * 21 + col) * 4 + bitplane
    """
    table = {}
    if not os.path.exists(CHARS_MD_PATH):
        print(f"Error: character table not found: {CHARS_MD_PATH}", file=sys.stderr)
        sys.exit(1)

    text = open(CHARS_MD_PATH, "r", encoding="utf-8").read()
    pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        r"\s*\(\d+,\d+\)\s*\|\s*\d+\s*\|"
        r"\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    )
    for m in pattern.finditer(text):
        cell = int(m.group(1))
        row = int(m.group(2))
        col = int(m.group(3))
        bits = [m.group(i).strip() for i in range(4, 8)]
        for bitplane, label in enumerate(bits):
            if not label or label == "(blank)" or label == "(Blank)":
                continue
            char_id = 1 + (row * 21 + col) * 4 + bitplane
            # Strip trailing ? from uncertain characters
            clean = label.rstrip("?").strip()
            if clean:
                table[char_id] = clean
    return table


def build_encode_table(decode_table):
    """Build reverse mapping: character -> charID (first occurrence wins)."""
    encode = {}
    for char_id, char in sorted(decode_table.items()):
        if char not in encode:
            encode[char] = char_id
    return encode


def char_id_to_bytes(char_id):
    """Encode a charID to its byte representation."""
    if 1 <= char_id <= 0xEE:
        return bytes([char_id])
    elif char_id >= 239:
        first = 0xF0 + (char_id - 239) // 255
        second = (char_id - 239) % 255
        return bytes([first, second])
    return None


def decode_string(data, offset, decode_table):
    """Decode a null-terminated text string starting at offset.

    Returns (decoded_text, bytes_consumed).
    """
    parts = []
    pos = offset
    length = len(data)

    while pos < length:
        b = data[pos]

        # Null terminator
        if b == 0x00:
            pos += 1
            break

        # FF control code (4 bytes)
        if b == 0xFF:
            if pos + 3 >= length:
                parts.append(f"[FF:incomplete]")
                pos += 1
                break
            sub = data[pos + 1]
            p1 = data[pos + 2]
            p2 = data[pos + 3]

            if sub == 0x05:
                parts.append("\n")
            elif sub == 0x08:
                if p1 == 0x01:
                    parts.append("[box:system]")
                elif p1 == 0x02:
                    parts.append("[box:close]")
                elif p1 == 0x03:
                    parts.append("[box:speech]")
                elif p1 == 0x05:
                    parts.append("[box:narration]")
                elif p1 == 0x07:
                    parts.append("[cursor]")
                else:
                    parts.append(f"[FF:08 {p1:02X} {p2:02X}]")
            elif sub == 0x03:
                parts.append(f"[delay:{p1:02X}]")
            elif sub == 0x07:
                parts.append(f"[num:{p1:02X}]")
            elif sub == 0x0B:
                parts.append(f"[item:{p1:02X}]")
            elif sub == 0x0D:
                parts.append(f"[name:{p1:02X}]")
            else:
                parts.append(f"[FF:{sub:02X} {p1:02X} {p2:02X}]")
            pos += 4
            continue

        # EF: choice option prefix
        if b == 0xEF:
            parts.append("[opt]")
            pos += 1
            continue

        # Two-byte charID (F0-FE prefix)
        if 0xF0 <= b <= 0xFE:
            if pos + 1 >= length:
                parts.append(f"[{b:02X}:incomplete]")
                pos += 1
                break
            second = data[pos + 1]
            char_id = (b - 0xF0) * 255 + second + 239
            char = decode_table.get(char_id)
            if char:
                parts.append(char)
            else:
                parts.append(f"[?{char_id}]")
            pos += 2
            continue

        # Single-byte charID (01-EE)
        if 0x01 <= b <= 0xEE:
            char = decode_table.get(b)
            if char:
                parts.append(char)
            else:
                parts.append(f"[?{b}]")
            pos += 1
            continue

        # Unknown byte
        parts.append(f"[{b:02X}]")
        pos += 1

    return "".join(parts), pos - offset


def is_valid_char_byte(b, decode_table):
    """Check if a byte could be a valid single-byte character."""
    return 0x01 <= b <= 0xEE and b in decode_table


def hex_dump(data, offset, length, cols=16):
    """Format a hex dump of data[offset:offset+length]."""
    lines = []
    for i in range(0, length, cols):
        addr = offset + i
        chunk = data[offset + i:offset + i + cols]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        lines.append(f"  {addr:08X}  {hex_part}")
    return "\n".join(lines)


def scan_file(data, decode_table):
    """Find all text strings in a binary file.

    Strategy:
    1. Look for FF 08 XX 01 dialogue box markers and decode from there
    2. Find standalone null-terminated runs of valid charIDs
    """
    results = []
    seen_offsets = set()
    length = len(data)

    # Pass 1: Find FF 08 XX 01 dialogue markers
    pos = 0
    while pos < length - 3:
        if data[pos] == 0xFF and data[pos + 1] == 0x08 and data[pos + 3] == 0x01:
            sub = data[pos + 2]
            if sub in (0x01, 0x02, 0x03, 0x05, 0x07):
                start = pos
                text, consumed = decode_string(data, start, decode_table)
                # Only include if there's actual text content
                stripped = text
                for tag in ("[box:system]", "[box:close]", "[box:speech]",
                            "[box:narration]", "[cursor]", "\n", "[opt]"):
                    stripped = stripped.replace(tag, "")
                # Remove control code tags
                stripped = re.sub(r"\[.*?\]", "", stripped)
                if len(stripped) >= MIN_TEXT_RUN:
                    if start not in seen_offsets:
                        results.append((start, consumed, text))
                        seen_offsets.add(start)
                        pos = start + consumed
                        continue
        pos += 1

    # Build interval set of already-found ranges for fast overlap check
    found_ranges = sorted((off, off + sz) for off, sz, _ in results)

    def in_found_range(p):
        for s, e in found_ranges:
            if s <= p < e:
                return e
            if s > p:
                break
        return 0

    # Pass 2: Find null-terminated text runs not overlapping Pass 1 results.
    # Walk through null bytes and check what follows as a potential string.
    pos = 0
    while pos < length:
        # Skip over already-found ranges
        skip_to = in_found_range(pos)
        if skip_to:
            pos = skip_to
            continue

        # We look for strings that start after a null byte (or at position 0)
        if pos > 0 and data[pos - 1] != 0x00:
            pos += 1
            continue

        # Validate this looks like a real text string by counting
        # consecutive valid character bytes before any null or invalid byte.
        # Reject any run that hits an unknown charID — real text should only
        # contain characters present in the font table.
        scan_pos = pos
        valid_chars = 0
        total_bytes = 0
        clean = True
        while scan_pos < length:
            b = data[scan_pos]
            if b == 0x00:
                break
            elif b == 0xFF:
                # FF control code - skip 4 bytes
                if scan_pos + 3 < length:
                    scan_pos += 4
                    total_bytes += 4
                    continue
                else:
                    break
            elif b == 0xEF:
                scan_pos += 1
                total_bytes += 1
                continue
            elif 0xF0 <= b <= 0xFE:
                if scan_pos + 1 < length:
                    second = data[scan_pos + 1]
                    char_id = (b - 0xF0) * 255 + second + 239
                    if char_id in decode_table:
                        valid_chars += 1
                    else:
                        clean = False
                        break
                    scan_pos += 2
                    total_bytes += 2
                    continue
                else:
                    break
            elif 0x01 <= b <= 0xEE:
                if b in decode_table:
                    valid_chars += 1
                else:
                    clean = False
                    break
                scan_pos += 1
                total_bytes += 1
                continue
            else:
                break

        # Require null termination, all known charIDs, and a higher minimum
        # character count (6) for standalone strings to reduce false positives
        min_standalone = 6
        if (clean and scan_pos < length and data[scan_pos] == 0x00
                and valid_chars >= min_standalone):
            if pos not in seen_offsets:
                text, consumed = decode_string(data, pos, decode_table)
                results.append((pos, consumed, text))
                seen_offsets.add(pos)
                pos = pos + consumed
                continue

        pos += 1

    results.sort(key=lambda r: r[0])
    return results


def find_text(data, search_str, decode_table, encode_table):
    """Find all occurrences of a text pattern in binary data."""
    # Encode the search string to byte pattern
    byte_pattern = bytearray()
    for ch in search_str:
        char_id = encode_table.get(ch)
        if char_id is None:
            print(f"Warning: character '{ch}' not in encoding table, skipping",
                  file=sys.stderr)
            return []
        encoded = char_id_to_bytes(char_id)
        if encoded:
            byte_pattern.extend(encoded)

    if not byte_pattern:
        return []

    results = []
    pattern_bytes = bytes(byte_pattern)
    pos = 0

    while pos < len(data):
        idx = data.find(pattern_bytes, pos)
        if idx == -1:
            break

        # Walk backwards to find the string start (look for null or FF 08)
        start = idx
        while start > 0 and data[start - 1] != 0x00:
            start -= 1
            # Don't walk back more than 4KB
            if idx - start > 4096:
                start = idx
                break

        text, consumed = decode_string(data, start, decode_table)
        results.append((start, consumed, text))
        pos = idx + len(pattern_bytes)

    return results


def parse_offset(s):
    """Parse an offset string (supports 0x hex prefix and decimal)."""
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    return int(s)


def main():
    parser = argparse.ArgumentParser(
        description="Decode Arc the Lad 2 text from binary game files."
    )
    parser.add_argument("file", help="Binary file to decode")
    parser.add_argument("offset", nargs="?", default=None,
                        help="Byte offset to decode (hex with 0x prefix or decimal)")
    parser.add_argument("--scan", action="store_true",
                        help="Scan file for all text strings")
    parser.add_argument("--find", metavar="TEXT",
                        help="Find strings containing the given text")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    if not args.scan and not args.find and args.offset is None:
        parser.error("Provide an offset, --scan, or --find")

    # Load character table
    decode_table = build_decode_table()
    data = open(args.file, "rb").read()

    # Mode 1: Single offset
    if args.offset is not None:
        offset = parse_offset(args.offset)
        if offset >= len(data):
            print(f"Error: offset 0x{offset:X} beyond file size ({len(data)} bytes)",
                  file=sys.stderr)
            sys.exit(1)

        text, consumed = decode_string(data, offset, decode_table)
        print(f"Offset: 0x{offset:08X} ({consumed} bytes)")
        print(hex_dump(data, offset, consumed))
        print(f"Text: {text}")
        return

    # Mode 2: Scan
    if args.scan:
        results = scan_file(data, decode_table)
        print(f"Found {len(results)} text strings in {args.file}")
        print()
        for offset, consumed, text in results:
            # Show compact single-line form for short strings
            display = text.replace("\n", "\\n")
            print(f"  0x{offset:08X} [{consumed:4d}] {display}")
        return

    # Mode 3: Find
    if args.find:
        encode_table = build_encode_table(decode_table)
        results = find_text(data, args.find, decode_table, encode_table)
        print(f"Found {len(results)} matches for \"{args.find}\" in {args.file}")
        print()
        for offset, consumed, text in results:
            display = text.replace("\n", "\\n")
            print(f"  0x{offset:08X} [{consumed:4d}] {display}")
        return


if __name__ == "__main__":
    main()
