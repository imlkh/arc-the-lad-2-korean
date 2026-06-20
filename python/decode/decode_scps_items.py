#!/usr/bin/env python3
"""Decode SCPS_100.26 equipment/item list entries resolving FF control codes.

Parses the decoded SCPS_100_26.txt output and resolves:
- [FF:XX YY ZZ] prefix codes (insert 1-2 characters at start of item)
- [FF:1A 00 XX] item separators (split compound entries into individual items)

FF Prefix Code Rules ([FF:sub YY ZZ]):
- If YY >= 0xF0: single extended character from 2-byte charID (YY, ZZ)
- If YY < 0xF0: two single-byte characters from charIDs YY and ZZ

Item Separator Rules ([FF:1A 00 XX]):
- XX = 0x00: no inline char, next item text follows directly
- XX = 0x01-0xEE: XX is a charID, prepend its character to following text
- XX = 0xF0-0xFE: extended char high byte; first decoded char after separator
                   provides the low byte charID to form extended character
- XX = 0xFF: drop first decoded char after separator (FF subcommand byte),
             remainder is the item name
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode_text import build_decode_table


def build_reverse_table(decode_table):
    """Build character -> charID reverse lookup (first occurrence wins)."""
    reverse = {}
    for cid, ch in sorted(decode_table.items()):
        if ch not in reverse:
            reverse[ch] = cid
    return reverse


def extended_char_id(high_byte, low_byte):
    """Compute extended charID from 2-byte encoding.

    Formula: charID = (high_byte - 0xF0) * 255 + low_byte + 239
    """
    return (high_byte - 0xF0) * 255 + low_byte + 239


def resolve_prefix(text, decode_table):
    """Resolve [FF:XX YY ZZ] prefix codes in text to actual characters.

    For prefix codes that are NOT [FF:1A ...] separators:
    - If YY >= 0xF0: produces one extended character from (YY, ZZ)
    - If YY < 0xF0: produces two single-byte characters from charIDs YY and ZZ
    """
    def replace_prefix(m):
        sub = int(m.group(1), 16)
        yy = int(m.group(2), 16)
        zz = int(m.group(3), 16)

        # Skip separator codes (handled separately)
        if sub == 0x1A:
            return m.group(0)

        if yy >= 0xF0:
            # Extended char from 2-byte charID
            ext_id = extended_char_id(yy, zz)
            ch = decode_table.get(ext_id, f'[?ext:{ext_id}]')
            return ch
        else:
            # Two single-byte chars
            ch1 = decode_table.get(yy, f'[?{yy:02X}]')
            ch2 = decode_table.get(zz, f'[?{zz:02X}]')
            return ch1 + ch2

    return re.sub(r'\[FF:([0-9A-Fa-f]{2}) ([0-9A-Fa-f]{2}) ([0-9A-Fa-f]{2})\]',
                  replace_prefix, text)


def resolve_items(line_text, decode_table, reverse_table):
    """Resolve a single entry with [FF:1A 00 XX] separators into individual item names.

    Steps:
    1. Split on [FF:1A 00 XX] separators
    2. Resolve [FF:XX YY ZZ] prefix codes in each segment
    3. Apply separator XX rules to reconstruct item names
    """
    items = []

    # Split on [FF:1A 00 XX] separators, capturing the XX byte
    parts = re.split(r'\[FF:1A 00 ([0-9A-Fa-f]{2})\]', line_text)

    # First part is the first item (may contain [FF:XX YY ZZ] prefix codes)
    first = resolve_prefix(parts[0], decode_table)
    items.append(first)

    # Remaining parts alternate: XX_hex, segment_text
    for i in range(1, len(parts), 2):
        xx_hex = parts[i]
        xx = int(xx_hex, 16)
        segment = parts[i + 1] if i + 1 < len(parts) else ""

        # Resolve any [FF:XX YY ZZ] prefix codes in the segment text
        segment = resolve_prefix(segment, decode_table)

        if xx == 0x00:
            # No inline char - segment text is the item as-is
            item = segment
        elif 0x01 <= xx <= 0xEE:
            # Single-byte charID: prepend its character
            ch = decode_table.get(xx, f'[?{xx:02X}]')
            item = ch + segment
        elif 0xF0 <= xx <= 0xFE:
            # Extended char: XX is high byte, first visible char provides low byte
            if segment:
                first_char = segment[0]
                rest = segment[1:]
                low_byte = reverse_table.get(first_char)
                if low_byte is not None and low_byte <= 0xEE:
                    ext_id = extended_char_id(xx, low_byte)
                    ext_char = decode_table.get(ext_id, f'[?ext:{ext_id}]')
                    item = ext_char + rest
                else:
                    # Cannot resolve - show raw
                    item = f'[EXT:{xx:02X}+{first_char}?]' + rest
            else:
                item = f'[EXT:{xx:02X}]'
        elif xx == 0xFF:
            # Drop first char (FF subcommand byte), rest is item name
            if segment:
                item = segment[1:]
            else:
                item = ""
        else:
            item = f'[?{xx:02X}]' + segment

        items.append(item)

    return items


def main():
    decode_table = build_decode_table()
    reverse_table = build_reverse_table(decode_table)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    decoded_path = os.path.join(script_dir, '..', '..', 'output', 'decoded',
                                'bin', 'SCPS_100_26.txt')
    decoded_path = os.path.normpath(decoded_path)

    if not os.path.exists(decoded_path):
        print(f"Error: {decoded_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(decoded_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Match decoded file line format: "  0xOFFSET [LEN] text"
    line_pattern = re.compile(r'^\s+0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$')

    entry_count = 0
    item_count = 0

    for lineno, line in enumerate(lines, 1):
        if '[FF:1A' not in line:
            continue

        m = line_pattern.match(line)
        if not m:
            continue

        offset = m.group(1)
        length = int(m.group(2))
        text = m.group(3)

        items = resolve_items(text, decode_table, reverse_table)
        entry_count += 1

        print(f"\n=== Line {lineno}: 0x{offset} [{length:3d}] ===")
        print(f"  Raw: {text}")
        for j, item in enumerate(items):
            item_clean = item.strip()
            if item_clean:
                print(f"  {j + 1:2d}. {item_clean}")
                item_count += 1

    # Also show entries with [FF:XX YY ZZ] prefix codes but no separators
    print("\n=== Entries with prefix codes only (no separators) ===")
    ff_prefix_pattern = re.compile(r'\[FF:(?!1A)[0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2}\]')
    for lineno, line in enumerate(lines, 1):
        if '[FF:1A' in line:
            continue
        if not ff_prefix_pattern.search(line):
            continue

        m = line_pattern.match(line)
        if not m:
            continue

        offset = m.group(1)
        length = int(m.group(2))
        text = m.group(3)

        resolved = resolve_prefix(text, decode_table)
        if resolved != text:
            print(f"  Line {lineno}: 0x{offset} [{length:3d}] {resolved}")

    print(f"\n=== Summary ===")
    print(f"  Compound entries: {entry_count}")
    print(f"  Total items resolved: {item_count}")


if __name__ == '__main__':
    main()
