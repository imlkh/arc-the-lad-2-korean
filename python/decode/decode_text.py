#!/usr/bin/env python3
"""
Decode Arc the Lad 2 dialogue text from binary game files.

Usage:
    python decode_text.py <file> <offset>          # decode one string at offset
    python decode_text.py <file> --scan            # find and decode all text strings
    python decode_text.py <file> --find "ますか"    # find strings containing a pattern
    python decode_text.py <file> --scan --prefix 2  # STG files: skip 2-byte event script prefix
    python decode_text.py <file> --stg             # STG template-driven dialogue extraction
    python decode_text.py <file> --stg --find "エルク"  # STG extraction filtered by text
"""

import argparse
import os
import re
import sys

# === Constants ===
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARS_MD_PATH = os.path.join(_SCRIPT_DIR, "..", "..", "docs", "COMM_IMG_chars.md")

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


def decode_string(data, offset, decode_table, prefix=0):
    """Decode a null-terminated text string starting at offset.

    If prefix > 0, the first `prefix` bytes are emitted as a [script:XX XX]
    tag instead of being decoded as characters (event script control bytes).

    Returns (decoded_text, bytes_consumed).
    """
    parts = []
    pos = offset
    length = len(data)

    # Emit event script prefix bytes as a hex tag
    if prefix > 0 and pos + prefix <= length:
        prefix_bytes = data[pos:pos + prefix]
        hex_str = " ".join(f"{b:02X}" for b in prefix_bytes)
        parts.append(f"[script:{hex_str}]")
        pos += prefix

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


# === STG Template-Driven Extraction ===

TEMPLATE_SIG = b'\x23\x01\xF0\x8B'
TEMPLATE_SIZE = 48
SCRIPT_OPCODE_28 = b'\x28\x01'
SCRIPT_BLOCK_SIZE = 10


def _find_templates(data):
    """Find all 48-byte event script template blocks in STG data.

    Returns list of (offset, context_opcode, ptr_a, ptr_b, ptr_c) tuples.
    """
    templates = []
    pos = 0
    while True:
        idx = data.find(TEMPLATE_SIG, pos)
        if idx == -1:
            break
        if idx + TEMPLATE_SIZE <= len(data):
            opcode = int.from_bytes(data[idx + 4:idx + 6], 'little')
            ptr_a = int.from_bytes(data[idx + 14:idx + 16], 'little')
            ptr_b = int.from_bytes(data[idx + 30:idx + 32], 'little')
            ptr_c = int.from_bytes(data[idx + 36:idx + 38], 'little')
            templates.append((idx, opcode, ptr_a, ptr_b, ptr_c))
        pos = idx + 1
    return templates


def _is_script_opcode_28(data, pos):
    """Check if a ``28 01`` at *pos* is an event script opcode (not text).

    The opcode ``28 01`` appears in 10-byte event script blocks with various
    2-byte parameters (07 00, AA 00, FF 00, F1 0B, etc.).  All variants
    share a fixed structural signature:

        +0   28 01       Opcode
        +2   XX YY       Parameter (varies)
        +4   ZZ 00       Flags -- byte +5 is always 0x00
        +6   WW HH       Context group -- byte +7 (HH) is >= 0x80
                          (0x80-0x82 for normal groups, 0xFF for broadcast)

    These bytes happen to map to valid character IDs (0x28=り, 0x01=あ, ...),
    so without this check the decoder would misinterpret them as dialogue.
    """
    if pos + 8 > len(data):
        return False
    return (data[pos:pos + 2] == SCRIPT_OPCODE_28
            and data[pos + 5] == 0x00
            and data[pos + 7] >= 0x80)


def _find_script_ranges(data, start, end):
    """Find all ``28 01`` script opcode regions in data[start:end].

    Scans for the 2-byte opcode ``28 01`` and validates each hit against the
    10-byte block structural signature (see ``_is_script_opcode_28``).
    Blocks appear in chains of 2-12+ at context transitions; single blocks
    can also occur.

    Returns a sorted list of (range_start, range_end) tuples covering all
    script-opcode bytes.  Adjacent/overlapping ranges are merged.
    """
    positions = []
    pos = start
    while pos <= end - 8:
        idx = data.find(SCRIPT_OPCODE_28, pos, end)
        if idx == -1 or idx + 8 > end:
            break
        if _is_script_opcode_28(data, idx):
            positions.append(idx)
        pos = idx + 2  # advance past this match
    if not positions:
        return []

    # Build ranges: each validated 28 01 marks a 10-byte block
    ranges = []
    for p in positions:
        block_end = min(p + SCRIPT_BLOCK_SIZE, end)
        if ranges and p <= ranges[-1][1]:
            # Merge with previous range
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], block_end))
        else:
            ranges.append((p, block_end))
    return ranges


def _overlaps_script(start, end, script_ranges):
    """Check if byte range [start, end) overlaps any preamble range."""
    for ps, pe in script_ranges:
        if start < pe and end > ps:
            return True
        if ps >= end:
            break
    return False


def _find_dialogue_in_gap(data, gap_start, gap_end, expected_prefix_bytes,
                          decode_table):
    """Search for a dialogue string in the gap between two templates.

    Returns (dialogue_offset, script_prefix_value, text, bytes_consumed)
    or None if no dialogue found.
    """
    # Trim trailing script opcode blocks (scan backward in 10-byte steps).
    while (gap_end - gap_start >= SCRIPT_BLOCK_SIZE
           and _is_script_opcode_28(data, gap_end - SCRIPT_BLOCK_SIZE)):
        gap_end -= SCRIPT_BLOCK_SIZE

    gap_size = gap_end - gap_start

    # Bare gap: only prefix bytes or nothing, no actual dialogue
    if gap_size <= 2:
        return None

    # Build exclusion zones for any remaining 28 01 script opcode blocks
    # that sit in the middle of the gap (context-transition script data
    # that precedes real dialogue strings).
    script_ranges = _find_script_ranges(data, gap_start, gap_end)

    # Primary: search for the expected 2-byte prefix in the gap
    gap_data = data[gap_start:gap_end]
    search_from = 0
    while search_from < len(gap_data):
        prefix_pos = gap_data.find(expected_prefix_bytes, search_from)
        if prefix_pos == -1:
            break
        abs_offset = gap_start + prefix_pos
        text, consumed = decode_string(data, abs_offset, decode_table, prefix=2)
        # Validate there's actual text content
        stripped = text
        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                    "[box:narration]", "[cursor]", "\n", "[opt]"):
            stripped = stripped.replace(tag, "")
        stripped = re.sub(r"\[script:.*?\]", "", stripped)
        stripped = re.sub(r"\[.*?\]", "", stripped)
        # Reject if text bytes overlap with a preamble block
        text_start = abs_offset + 2  # after 2-byte script prefix
        text_end = abs_offset + consumed
        if (len(stripped) >= 1
                and not _overlaps_script(text_start, text_end,
                                           script_ranges)):
            prefix_val = int.from_bytes(expected_prefix_bytes, 'little')
            return (abs_offset, prefix_val, text, consumed)
        # Try the next occurrence of the prefix in the gap
        search_from = prefix_pos + 1

    # Fallback: walk forward looking for a null byte (end of previous string),
    # then try decoding from there + 1 with 2-byte prefix
    scan_pos = gap_start
    while scan_pos < gap_end - 3:
        if data[scan_pos] == 0x00:
            candidate = scan_pos + 1
            if candidate + 2 < gap_end:
                text, consumed = decode_string(data, candidate, decode_table,
                                               prefix=2)
                stripped = text
                for tag in ("[box:system]", "[box:close]", "[box:speech]",
                            "[box:narration]", "[cursor]", "\n", "[opt]"):
                    stripped = stripped.replace(tag, "")
                stripped = re.sub(r"\[script:.*?\]", "", stripped)
                stripped = re.sub(r"\[.*?\]", "", stripped)
                text_start = candidate + 2
                text_end = candidate + consumed
                if (len(stripped) >= MIN_TEXT_RUN
                        and not _overlaps_script(text_start, text_end,
                                                   script_ranges)):
                    prefix_val = int.from_bytes(data[candidate:candidate + 2],
                                                'little')
                    return (candidate, prefix_val, text, consumed)
        scan_pos += 1

    return None


def scan_stg(data, decode_table):
    """Template-driven dialogue extraction for STG files.

    Returns (dialogues, templates, stats) where:
      dialogues = [(offset, consumed, text, context_opcode), ...]
      templates = [(offset, opcode, ptr_a, ptr_b, ptr_c), ...]
      stats = {'total_templates': N, 'found': N, 'missed': N, 'bare': N}
    """
    templates = _find_templates(data)
    dialogues = []
    stats = {'total_templates': len(templates), 'found': 0, 'missed': 0,
             'bare': 0}

    if not templates:
        return dialogues, templates, stats

    # --- First dialogue: search backward from first template ---
    first_tmpl = templates[0]
    expected_prefix_val = first_tmpl[2] - 0x10  # ptr_a - 0x10
    expected_prefix_bytes = expected_prefix_val.to_bytes(2, 'little')
    search_start = max(0, first_tmpl[0] - 4096)
    search_end = first_tmpl[0]

    gap_data = data[search_start:search_end]
    prefix_pos = gap_data.find(expected_prefix_bytes)
    if prefix_pos != -1:
        abs_offset = search_start + prefix_pos
        text, consumed = decode_string(data, abs_offset, decode_table, prefix=2)
        stripped = text
        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                    "[box:narration]", "[cursor]", "\n", "[opt]"):
            stripped = stripped.replace(tag, "")
        stripped = re.sub(r"\[script:.*?\]", "", stripped)
        stripped = re.sub(r"\[.*?\]", "", stripped)
        if len(stripped) >= 1:
            dialogues.append((abs_offset, consumed, text, first_tmpl[1]))
            stats['found'] += 1

    # --- Loop through consecutive template pairs ---
    for i in range(len(templates) - 1):
        tmpl_cur = templates[i]
        tmpl_next = templates[i + 1]

        gap_start = tmpl_cur[0] + TEMPLATE_SIZE
        gap_end = tmpl_next[0]

        # Compute expected prefix from next template's ptr_a
        expected_val = tmpl_next[2] - 0x10  # ptr_a - 0x10
        if expected_val < 0:
            expected_val = 0
        expected_bytes = expected_val.to_bytes(2, 'little')

        result = _find_dialogue_in_gap(data, gap_start, gap_end,
                                       expected_bytes, decode_table)
        if result is not None:
            offset, prefix_val, text, consumed = result
            dialogues.append((offset, consumed, text, tmpl_cur[1]))
            stats['found'] += 1
        elif gap_end - gap_start <= 2:
            stats['bare'] += 1
        else:
            stats['missed'] += 1

    return dialogues, templates, stats


def scan_file(data, decode_table, prefix=0, ff08_only=False):
    """Find all text strings in a binary file.

    Strategy:
    1. Look for FF 08 XX 01 dialogue box markers and decode from there
    2. Find standalone null-terminated runs of valid charIDs

    If ff08_only=True, only Pass 1 (FF 08 markers) is run.  This is much
    faster for large files (e.g. BEAM.DAT) where the byte-by-byte Pass 2
    scan would be prohibitively slow and produce mostly false positives.
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
                text, consumed = decode_string(data, start, decode_table, prefix=prefix)
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

    if ff08_only:
        results.sort(key=lambda r: r[0])
        return results

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
                text, consumed = decode_string(data, pos, decode_table, prefix=prefix)
                results.append((pos, consumed, text))
                seen_offsets.add(pos)
                pos = pos + consumed
                continue

        pos += 1

    results.sort(key=lambda r: r[0])
    return results


def filter_real_text(results, min_kanji=2, strict=False):
    """Filter scan_file results to remove false positives from machine code.

    Requires at least ``min_kanji`` CJK Unified Ideographs (U+4E00-U+9FFF) in
    the decoded text.  MIPS machine code bytes frequently map to valid
    character IDs, producing long runs of plausible-looking but meaningless
    kana — and occasionally a single kanji.  Requiring >= 2 kanji eliminates
    virtually all false positives while retaining real game text (dialogue,
    menus, item/spell descriptions), which almost always contains multiple
    kanji.

    Args:
        results: list of (offset, consumed, text) tuples from scan_file
        min_kanji: minimum number of kanji characters required (default 2)
        strict: if True, require proper Japanese sentence endings and reject
                strings with random character patterns (use for executable
                files with lots of code bytes)

    Returns:
        Filtered list of (offset, consumed, text) tuples.
    """
    # Common Japanese sentence endings (verbs, adjectives, particles)
    SENTENCE_ENDINGS = (
        # Polite verb forms
        'ます', 'ました', 'ません', 'ませんか', 'ましょう', 'ですか',
        # Plain verb forms
        'です', 'だった', 'である', 'でした', 'ている', 'ていた',
        'する', 'した', 'される', 'された', 'できる', 'できない',
        'ない', 'なかった', 'ある', 'あった', 'いる', 'いた',
        'なる', 'なった', 'くる', 'きた', 'いく', 'いった',
        # Requests/commands
        'ください', 'くれ', 'ろ', 'よう', 'てくれ',
        # Sentence-final particles
        'か', 'ね', 'よ', 'わ', 'ぞ', 'な', 'さ',
        # Noun endings (common game text patterns)
        '無し', '中', '済み',
    )
    # Japanese punctuation that often ends sentences
    END_PUNCTUATION = ('。', '！', '？', '…')

    filtered = []
    for offset, consumed, text in results:
        # Strip control tags to get the actual displayed text
        stripped = text
        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                    "[box:narration]", "[cursor]", "\n", "[opt]"):
            stripped = stripped.replace(tag, "")
        stripped = re.sub(r"\[.*?\]", "", stripped)

        if not stripped:
            continue

        # Count kanji characters
        kanji_count = sum(1 for ch in stripped if '\u4e00' <= ch <= '\u9fff')
        if kanji_count < min_kanji:
            continue

        if strict:
            # In strict mode, require proper Japanese sentence structure:
            # 1. Must end with a common verb ending, particle, or punctuation

            has_valid_ending = (
                any(stripped.endswith(e) for e in SENTENCE_ENDINGS) or
                any(stripped.endswith(p) for p in END_PUNCTUATION)
            )

            if not has_valid_ending:
                continue

            # Reject strings with excessive repetition (code patterns)
            # Check for 3+ consecutive identical characters
            if re.search(r'(.)\1{2,}', stripped):
                continue

            # Check for repeating 2-3 char patterns (like "たギ" repeated)
            if re.search(r'(.{2,3})\1{2,}', stripped):
                continue

            # Reject strings with too much katakana mixed with hiragana randomly
            # Real Japanese has katakana for loanwords (clustered), not scattered
            hiragana = sum(1 for ch in stripped if 'ぁ' <= ch <= 'ん')
            katakana = sum(1 for ch in stripped if 'ァ' <= ch <= 'ン')
            total_kana = hiragana + katakana
            # If there's significant kana but it's roughly 50/50 hiragana/katakana,
            # it's likely garbage (real text is usually hiragana-dominant or
            # has katakana in clusters for loanwords)
            if total_kana > 10 and katakana > 0 and hiragana > 0:
                ratio = min(hiragana, katakana) / max(hiragana, katakana)
                if ratio > 0.4:  # Too balanced = likely garbage
                    continue

            # Reject strings with excessive "ギ" (charID 0x07, very common in MIPS code)
            # Real Japanese rarely has more than 2-3 ギ in a sentence
            if stripped.count('ギ') > 3:
                continue

            # Reject strings with Latin letters mixed into Japanese
            # (e.g., "GOあギえで" or "e地うく")
            has_latin = bool(re.search(r'[A-Za-z]', stripped))
            if has_latin and kanji_count < 4:
                continue

        filtered.append((offset, consumed, text))

    return filtered


def find_text(data, search_str, decode_table, encode_table, prefix=0):
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

        text, consumed = decode_string(data, start, decode_table, prefix=prefix)
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
    parser.add_argument("--stg", action="store_true",
                        help="Template-driven dialogue extraction for STG files")
    parser.add_argument("--find", metavar="TEXT",
                        help="Find strings containing the given text")
    parser.add_argument("--prefix", type=int, default=0, metavar="N",
                        help="Treat first N bytes of each string as event script "
                             "control bytes (shown as [script:XX ...] tag)")
    args = parser.parse_args()

    if args.scan and args.stg:
        parser.error("--scan and --stg are mutually exclusive")

    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    if not args.scan and not args.stg and not args.find and args.offset is None:
        parser.error("Provide an offset, --scan, --stg, or --find")

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

        text, consumed = decode_string(data, offset, decode_table, prefix=args.prefix)
        print(f"Offset: 0x{offset:08X} ({consumed} bytes)")
        print(hex_dump(data, offset, consumed))
        print(f"Text: {text}")
        return

    # Mode 2: Scan
    if args.scan:
        results = scan_file(data, decode_table, prefix=args.prefix)
        print(f"Found {len(results)} text strings in {args.file}")
        print()
        for offset, consumed, text in results:
            # Show compact single-line form for short strings
            display = text.replace("\n", "\\n")
            print(f"  0x{offset:08X} [{consumed:4d}] {display}")
        return

    # Mode 2b: STG template-driven extraction
    if args.stg:
        dialogues, templates, stats = scan_stg(data, decode_table)
        basename = os.path.basename(args.file)

        if not templates:
            print(f"No templates found in {basename}")
            return

        # Filter by --find if specified
        if args.find:
            dialogues = [d for d in dialogues if args.find in d[2]]

        print(f"Found {stats['found']} dialogues across "
              f"{stats['total_templates']} templates in {basename} "
              f"({stats['bare']} bare gaps, {stats['missed']} missed)")
        print()

        prev_opcode = None
        for offset, consumed, text, context_opcode in dialogues:
            # Show context change separator
            if prev_opcode is not None and context_opcode != prev_opcode:
                print(f"  --- context: 0x{prev_opcode:04X} -> "
                      f"0x{context_opcode:04X} ---")
            prev_opcode = context_opcode

            display = text.replace("\n", "\\n")
            print(f"  0x{offset:08X} [0x{context_opcode:04X}] {display}")
        return

    # Mode 3: Find
    if args.find:
        encode_table = build_encode_table(decode_table)
        results = find_text(data, args.find, decode_table, encode_table, prefix=args.prefix)
        print(f"Found {len(results)} matches for \"{args.find}\" in {args.file}")
        print()
        for offset, consumed, text in results:
            display = text.replace("\n", "\\n")
            print(f"  0x{offset:08X} [{consumed:4d}] {display}")
        return


if __name__ == "__main__":
    main()
