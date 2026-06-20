#!/usr/bin/env python3
"""
Patch Arc the Lad 2 game files with Korean translation.

This script:
1. Extracts unique Korean characters from the translation file
2. Builds a mapping from Korean characters to font charIDs
3. Patches COMM.IMG (font texture) with Korean glyphs
4. Patches STG files with encoded Korean text

Usage:
    python patch_korean.py S100
    python patch_korean.py S100 --dry-run
"""

import argparse
import os
import re
import shutil
import struct
from PIL import Image

# === Paths ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)  # python/
BASE_DIR = os.path.dirname(PYTHON_DIR)    # atl2_korean_translation/
GAME_DIR = os.path.dirname(BASE_DIR)      # Arc_The_Lad2/
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "patched")
KOREAN_CHARS_DIR = os.path.join(BASE_DIR, "output", "font", "korean", "chars")
CHARS_MD_PATH = os.path.join(BASE_DIR, "docs", "COMM_IMG_chars.md")

# === COMM.IMG constants ===
ROW_WIDTH = 896       # bytes per scanline
CHAR_W = 12           # cell width in pixels
CHAR_H = 12           # cell height in pixels
GRID_COLS = 21        # cells per row

# === STG chunk constants ===
CHUNK_SIZE = 0xBC800  # 772,096 bytes per chunk
EVENT_SCRIPT_OFFSET = 0xB4000  # event script starts here in each chunk

# Characters to preserve (not replace with Korean)
# These cells contain important UI elements, symbols, and special characters
#
# Cell to charID mapping: charID = cell * 4 + 1 + bitplane (bitplane 0-3)
#
# Preserved cells:
#   - Cells 40-46 (A-Z): charIDs 161-186 — used by game for HP, MP, LV, GP, etc.
#   - Cells 46-52 (a-z): charIDs 187-212 — NOT preserved (game never uses lowercase)
#   - Cells 53-62: 0-9, symbols, punctuation (charIDs 213-252)
#   - Cells 64-67: Special characters (charIDs 257-272)
#   - Cell 63, bitplane 0 only: Special character (charID 253)
#
# Available for Korean (freed slots):
#   - Cell 63, bitplanes 1-3: charIDs 254-256
#   - Cells 46-52 (a-z): charIDs 187-212 (26 extra single-byte slots)
#   - CharID 160 (formerly ッ/space, unused)
PRESERVE_CHAR_IDS = set()

# Latin uppercase A-Z only (charIDs 161-186) — game uses these in HP, MP, LV, etc.
PRESERVE_CHAR_IDS.update(range(161, 187))

# NOTE: Lowercase a-z (charIDs 187-212) are NOT preserved.
# Verified: game never uses standalone lowercase letters in visible text.
# Only 4 occurrences exist in the font test area (0x0D79D8-0x0D79FB).

# Digits 0-9 and symbols (charIDs 213-252)
PRESERVE_CHAR_IDS.update(range(213, 253))

# Cells 64-67: all bitplanes (charIDs 257-272)
PRESERVE_CHAR_IDS.update(range(257, 273))

# Cell 63, bitplane 0 only (charID 253)
PRESERVE_CHAR_IDS.add(253)

# Space character - removed entirely (Korean reads fine without spaces like Japanese)
# Set to None to skip spaces during encoding
SPACE_CHAR_ID = None


def load_decode_table():
    """Parse COMM_IMG_chars.md to build charID -> character mapping."""
    table = {}
    if not os.path.exists(CHARS_MD_PATH):
        raise FileNotFoundError(f"Character table not found: {CHARS_MD_PATH}")

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
            if not label or label.lower() in ("(blank)", "blank"):
                continue
            char_id = 1 + (row * 21 + col) * 4 + bitplane
            # Strip charID suffix like " (123)" and trailing "?"
            clean = re.sub(r'\s*\(\d+\)\s*$', '', label).rstrip("?").strip()
            if clean:
                table[char_id] = clean
    return table


def build_encode_table(decode_table):
    """Build reverse mapping: character -> charID."""
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


def bytes_to_char_id(data, pos):
    """Decode byte(s) at position to charID. Returns (charID, bytes_consumed)."""
    b = data[pos]
    if b == 0x00:
        return None, 1
    if 0xF0 <= b <= 0xFE and pos + 1 < len(data):
        second = data[pos + 1]
        char_id = (b - 0xF0) * 255 + second + 239
        return char_id, 2
    if 0x01 <= b <= 0xEE:
        return b, 1
    return None, 1


def extract_korean_chars(translation_path):
    """Extract unique Korean Hangul characters from translation file."""
    with open(translation_path, "r", encoding="utf-8") as f:
        text = f.read()

    korean_chars = set()
    for ch in text:
        # Korean Hangul Syllables: U+AC00-U+D7A3
        if "\uAC00" <= ch <= "\uD7A3":
            korean_chars.add(ch)

    return sorted(korean_chars)


def build_korean_mapping(korean_chars, decode_table, char_frequency=None,
                         non_stg_frequency=None, stg_frequency=None,
                         packed_list_chars=None,
                         scps_frequency=None, beam_frequency=None):
    """Build mapping from Korean characters to font charIDs.

    Strategy: Replace hiragana (1-80), katakana (81-160), lowercase a-z (187-212),
    then kanji (239+). Preserve Latin uppercase, digits, and common symbols.

    Characters are ordered by priority for single-byte (1-byte) slot assignment:
      1. Packed list chars (can't be truncated, must minimize byte cost)
      2. SCPS_100.26 chars by frequency (fixed-length, most space-constrained)
      3. BEAM.DAT chars by frequency (fixed-length)
      4. Other non-STG chars by frequency (fixed-length)
      5. STG-only chars by frequency (variable-length, less byte-sensitive)

    Args:
        korean_chars: List of Korean characters to map
        decode_table: The character decode table
        char_frequency: Optional dict mapping char -> usage count (flat fallback)
        non_stg_frequency: Optional dict of char frequency in non-STG files (fixed-length)
        stg_frequency: Optional dict of char frequency in STG files (variable-length)
        packed_list_chars: Optional set of chars used in packed item lists (highest priority
            for single-byte slots, since packed lists can't be truncated)
        scps_frequency: Optional dict of char frequency in SCPS_100.26 (top priority)
        beam_frequency: Optional dict of char frequency in BEAM.DAT (second priority)
    """
    # CharIDs that encode with 00 byte (unusable - 00 is null terminator)
    # These are charIDs where (charID - 239) % 255 == 0: 239, 494, 749, ...
    NULL_BYTE_CHARIDS = {239 + 255 * i for i in range(7)}  # 239, 494, 749, 1004, 1259, 1514, 1769

    # Available slots (can be replaced with Korean):
    available_single = []  # charIDs 1-238 that aren't preserved (single-byte)
    available_double = []  # charIDs 239+ (two-byte)

    # Hiragana slots (charIDs 1-80)
    for cid in range(1, 81):
        available_single.append(cid)

    # Katakana slots (charIDs 81-159), excluding charID 160 (empty space)
    for cid in range(81, 160):
        available_single.append(cid)

    # Freed lowercase a-z slots (charIDs 187-212)
    # Game never uses standalone lowercase letters in visible text
    for cid in range(187, 213):
        available_single.append(cid)

    # Kanji slots (charIDs 239+, two-byte encoding)
    # Skip charIDs that encode with 00 byte (null terminator conflict)
    for cid in range(239, 1760):
        if cid not in PRESERVE_CHAR_IDS and cid not in NULL_BYTE_CHARIDS:
            available_double.append(cid)

    total_available = len(available_single) + len(available_double)
    if len(korean_chars) > total_available:
        raise ValueError(f"Not enough font slots: need {len(korean_chars)}, have {total_available}")

    # Build mapping: Korean char -> charID
    mapping = {}

    # Determine character ordering for slot assignment
    # Priority tiers (highest first):
    #   1. Packed list chars (can't be truncated, must minimize byte cost)
    #   2. SCPS_100.26 chars by frequency (fixed-length, most space-constrained)
    #   3. BEAM.DAT chars by frequency (fixed-length)
    #   4. Other non-STG chars by frequency (fixed-length)
    #   5. STG-only chars by frequency (variable-length, less byte-sensitive)
    if scps_frequency is not None and beam_frequency is not None:
        packed_set = packed_list_chars or set()
        other_non_stg = non_stg_frequency or {}
        ordered_chars = sorted(korean_chars, key=lambda c: (
            0 if c in packed_set else 1,   # packed list chars first
            -scps_frequency.get(c, 0),     # SCPS frequency (top priority)
            -beam_frequency.get(c, 0),     # BEAM frequency (second)
            -other_non_stg.get(c, 0),      # other non-STG frequency
            -stg_frequency.get(c, 0)       # STG frequency (lowest)
        ))
    elif non_stg_frequency is not None and stg_frequency is not None:
        packed_set = packed_list_chars or set()
        ordered_chars = sorted(korean_chars, key=lambda c: (
            0 if c in packed_set else 1,   # packed list chars first
            -non_stg_frequency.get(c, 0),
            -stg_frequency.get(c, 0)
        ))
    elif char_frequency:
        ordered_chars = sorted(korean_chars, key=lambda c: -char_frequency.get(c, 0))
    else:
        ordered_chars = korean_chars

    single_idx = 0
    double_idx = 0

    for kr_char in ordered_chars:
        if single_idx < len(available_single):
            mapping[kr_char] = available_single[single_idx]
            single_idx += 1
        else:
            mapping[kr_char] = available_double[double_idx]
            double_idx += 1

    return mapping


def get_pixel(data, x, y):
    """Get 4bpp pixel value at (x, y) in COMM.IMG."""
    byte_offset = y * ROW_WIDTH + x // 2
    byte_val = data[byte_offset]
    if x % 2 == 0:
        return byte_val & 0x0F
    else:
        return (byte_val >> 4) & 0x0F


def set_pixel(data, x, y, value):
    """Set 4bpp pixel value at (x, y) in COMM.IMG."""
    byte_offset = y * ROW_WIDTH + x // 2
    byte_val = data[byte_offset]
    if x % 2 == 0:
        byte_val = (byte_val & 0xF0) | (value & 0x0F)
    else:
        byte_val = (byte_val & 0x0F) | ((value & 0x0F) << 4)
    data[byte_offset] = byte_val


def inject_glyph(data, char_id, glyph_img):
    """Inject a Korean glyph into COMM.IMG data at the given charID position.

    Modifies only the target bitplane, preserving other bitplanes in the cell.
    """
    adjusted = char_id - 1
    cell = adjusted // 4
    bitplane = adjusted % 4
    row = cell // GRID_COLS
    col = cell % GRID_COLS

    x0 = col * CHAR_W
    y0 = row * CHAR_H
    mask = 1 << bitplane
    clear_mask = ~mask & 0x0F

    for dy in range(min(CHAR_H, glyph_img.height)):
        for dx in range(min(CHAR_W, glyph_img.width)):
            px = x0 + dx
            py = y0 + dy

            current = get_pixel(data, px, py)

            # Check if Korean glyph has a pixel at this position
            pixel_val = glyph_img.getpixel((dx, dy))
            if pixel_val > 0:
                current = current | mask
            else:
                current = current & clear_mask

            set_pixel(data, px, py, current)


def clear_glyph(data, char_id):
    """Clear a glyph slot to blank (all pixels off for the target bitplane)."""
    adjusted = char_id - 1
    cell = adjusted // 4
    bitplane = adjusted % 4
    row = cell // GRID_COLS
    col = cell % GRID_COLS

    x0 = col * CHAR_W
    y0 = row * CHAR_H
    clear_mask = ~(1 << bitplane) & 0x0F

    for dy in range(CHAR_H):
        for dx in range(CHAR_W):
            px = x0 + dx
            py = y0 + dy
            current = get_pixel(data, px, py)
            current = current & clear_mask  # Clear this bitplane
            set_pixel(data, px, py, current)


def patch_comm_img(comm_img_path, korean_mapping):
    """Patch COMM.IMG with Korean glyphs based on the mapping."""
    print(f"Patching COMM.IMG: {comm_img_path}")

    with open(comm_img_path, "rb") as f:
        data = bytearray(f.read())

    # Clear charID 160 (0xA0) to blank — used as space for [box:speech] workaround
    clear_glyph(data, 160)

    patched = 0
    missing = []

    for kr_char, char_id in sorted(korean_mapping.items(), key=lambda x: x[1]):
        codepoint = ord(kr_char)
        png_path = os.path.join(KOREAN_CHARS_DIR, f"char_{codepoint:04X}.png")

        if not os.path.exists(png_path):
            missing.append(kr_char)
            continue

        glyph_img = Image.open(png_path).convert("L")
        inject_glyph(data, char_id, glyph_img)
        patched += 1

    with open(comm_img_path, "wb") as f:
        f.write(data)

    print(f"  Patched {patched} Korean glyphs into font")
    if missing:
        print(f"  WARNING: {len(missing)} missing glyph PNGs: {''.join(missing[:20])}...")

    return patched


def parse_translation_file(translation_path):
    """Parse translation file to extract offset -> Korean text mappings.

    Translation file format:
        0x000B4516 [0x8006] [script:16 07]큰 도시네

    Returns: list of (offset, opcode, script_prefix, korean_text)
    """
    entries = []

    with open(translation_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("---"):
                continue

            # Parse: 0xOFFSET [0xOPCODE] [script:XX XX]Korean text
            match = re.match(
                r"0x([0-9A-Fa-f]+)\s+\[0x([0-9A-Fa-f]+)\]\s+\[script:([0-9A-Fa-f ]+)\](.*)",
                line
            )
            if match:
                offset = int(match.group(1), 16)
                opcode = int(match.group(2), 16)
                script_hex = match.group(3).strip()
                script_bytes = bytes.fromhex(script_hex.replace(" ", ""))
                korean_text = match.group(4)

                entries.append({
                    "offset": offset,
                    "opcode": opcode,
                    "script_prefix": script_bytes,
                    "text": korean_text
                })
                continue

            # Parse bare entries: 0xOFFSET [bare]Korean text
            # Used for standalone item/monster names without opcode/script prefix
            bare_match = re.match(
                r"0x([0-9A-Fa-f]+)\s+\[bare\](.*)",
                line
            )
            if bare_match:
                offset = int(bare_match.group(1), 16)
                korean_text = bare_match.group(2)

                entries.append({
                    "offset": offset,
                    "opcode": 0,
                    "script_prefix": b"",
                    "text": korean_text
                })

    return entries


def encode_korean_text(text, korean_mapping, decode_table):
    """Encode Korean text to game byte format.

    Handles:
    - Korean characters via korean_mapping
    - Control codes: [delay:XX], [box:type], \n, etc.
    - Preserved characters (Latin, digits, symbols) via decode_table reverse lookup
    """
    # Normalize special character sequences to single characters
    # This saves bytes and uses the proper font glyphs
    text = text.replace('...', '…')  # Three periods -> ellipsis (charID 229)
    text = text.replace('..', '…')   # Two periods -> ellipsis (rare but handle it)

    result = bytearray()
    encode_table = build_encode_table(decode_table)

    i = 0
    while i < len(text):
        ch = text[i]

        # Newline -> FF 05 01 01
        # Handle both actual newline and literal \n sequence
        if ch == "\n":
            result.extend(b"\xFF\x05\x01\x01")
            i += 1
            continue

        # Literal \n sequence (backslash followed by 'n')
        if ch == "\\" and i + 1 < len(text) and text[i + 1] == "n":
            result.extend(b"\xFF\x05\x01\x01")
            i += 2
            continue

        # Control code tags
        if ch == "[":
            end = text.find("]", i)
            if end != -1:
                tag = text[i+1:end]

                if tag.startswith("delay:"):
                    val = int(tag[6:], 16)
                    result.extend(bytes([0xFF, 0x03, val, 0x01]))
                elif tag == "box:system":
                    result.extend(b"\xFF\x08\x01\x01")
                elif tag == "box:close":
                    result.extend(b"\xFF\x08\x02\x01")
                elif tag == "box:speech":
                    result.extend(b"\xFF\x08\x03\x01")
                    # At string start, insert space (0xA0) to prevent
                    # 01 F0 display bug with Korean two-byte chars.
                    if len(result) == 4:
                        result.append(0xA0)
                elif tag == "box:narration":
                    result.extend(b"\xFF\x08\x05\x01")
                elif tag == "cursor":
                    result.extend(b"\xFF\x08\x07\x01")
                elif tag == "br":
                    # Line break -> FF 05 01 01
                    result.extend(b"\xFF\x05\x01\x01")
                elif tag == "opt":
                    result.append(0xEF)
                elif tag.startswith("FF:"):
                    # Generic FF control: [FF:XX YY ZZ]
                    parts = tag[3:].split()
                    result.append(0xFF)
                    for p in parts:
                        result.append(int(p, 16))
                elif tag.startswith("num:"):
                    val = int(tag[4:], 16)
                    result.extend(bytes([0xFF, 0x07, val, 0x01]))
                elif tag.startswith("item:"):
                    val = int(tag[5:], 16)
                    result.extend(bytes([0xFF, 0x0B, val, 0x01]))
                elif tag.startswith("name:"):
                    val = int(tag[5:], 16)
                    result.extend(bytes([0xFF, 0x0D, val, 0x01]))
                else:
                    # Unknown tag, skip
                    pass

                i = end + 1
                continue

        # Korean character
        if ch in korean_mapping:
            char_id = korean_mapping[ch]
            encoded = char_id_to_bytes(char_id)
            if encoded:
                result.extend(encoded)
            i += 1
            continue

        # Preserved character (Latin, digit, symbol)
        if ch in encode_table:
            char_id = encode_table[ch]
            encoded = char_id_to_bytes(char_id)
            if encoded:
                result.extend(encoded)
            i += 1
            continue

        # Common punctuation mapping
        punct_map = {
            "、": 0xE4, "。": 0xEC, "！": 0xED, "？": 0xEE,
            "…": 0xE5, "・": 250,  # ・ is at charID 250
            "ー": 0xE3, "～": 0xEA,
            "(": 245, ")": 246, "「": 251, "」": 252,
            ",": 247, ".": 248, ":": 249,
            # ASCII equivalents of fullwidth punctuation
            "?": 0xEE, "!": 0xED,
            "~": 0xEA,  # Same as ～
            "-": 0xE7,  # Same as － (fullwidth minus)
            "/": 232,   # ／ at cell 57, bit 3
            "／": 232,  # Fullwidth slash
            '"': 235,   # " character at cell 58, bit 2
            # Space is removed entirely (Korean reads fine without spaces)
            " ": None,
        }
        if ch in punct_map:
            char_id = punct_map[ch]
            if char_id is not None:
                encoded = char_id_to_bytes(char_id)
                if encoded:
                    result.extend(encoded)
            # Skip character (including spaces mapped to None)
            i += 1
            continue

        # Skip unrecognized characters
        # print(f"  Warning: unrecognized char '{ch}' (U+{ord(ch):04X})")
        i += 1

    return bytes(result)


def parse_original_packed_list(data, offset):
    """Parse the original packed list to find item boundaries and separators.

    Scans from offset until null terminator, identifying each item's byte
    range and the separator bytes between items. The separator bytes are
    preserved exactly as-is when patching.

    Returns:
        List of dicts with 'start', 'end' (item content range) and
        'sep_bytes' (raw separator bytes after this item, or None for last).
    """
    items = []
    i = offset
    item_start = i

    while i < len(data):
        b = data[i]
        if b == 0x00:
            # Null terminator - end of last item
            items.append({
                'start': item_start,
                'end': i,
                'sep_bytes': None,
            })
            break
        elif b == 0xFF and i + 1 < len(data) and data[i + 1] in (0x1A, 0x19):
            # Separator found - record item and separator bytes
            # The separator is FF XX 00 (3 bytes) possibly followed by
            # a 0x00 alignment pad. Scan forward to find separator end.
            item_end = i
            sep_start = i
            # Read FF XX
            sep_end = i + 2
            # Read bytes until we hit a non-zero byte or reach the next
            # item. The separator pattern is FF XX followed by one or
            # more 0x00 bytes.
            while sep_end < len(data) and data[sep_end] == 0x00:
                sep_end += 1
                # Stop after at most 2 zero bytes (FF XX 00 00 max)
                if sep_end - (i + 2) >= 2:
                    break

            raw_sep = bytes(data[sep_start:sep_end])
            items.append({
                'start': item_start,
                'end': item_end,
                'sep_bytes': raw_sep,
            })
            i = sep_end
            item_start = i
            continue
        elif b >= 0xF0:
            i += 2  # 2-byte character
        else:
            i += 1

    return items


# Padding byte for packed list items (charID 160 = blank glyph)
PACKED_LIST_PAD_BYTE = 0xA0


def encode_packed_list(text, korean_mapping, decode_table, orig_data=None, base_offset=0):
    """Encode a packed item list, preserving original separator bytes.

    Each Korean item is encoded and padded (with charID 160 = 0xA0) to
    match the original item's byte length exactly. Separator bytes from
    the original binary are preserved verbatim.

    Args:
        text: Korean text with [FF:1A 00 00] or [FF:19 00 00] separators
        korean_mapping: char -> charID mapping
        decode_table: original game char table for reverse lookup
        orig_data: original binary data (for reading separator bytes)
        base_offset: file offset where this packed list starts

    Returns:
        Encoded bytes for the entire packed list (without trailing null)
    """
    # Detect separator tag
    if "[FF:1A 00 00]" in text:
        sep_tag = "[FF:1A 00 00]"
    elif "[FF:19 00 00]" in text:
        sep_tag = "[FF:19 00 00]"
    else:
        sep_tag = "[FF:1A 00 00]"

    korean_items = text.split(sep_tag)

    # Parse original packed list to get item boundaries and separators
    if orig_data is not None:
        orig_items = parse_original_packed_list(orig_data, base_offset)
    else:
        orig_items = []

    if orig_items:
        # Match Korean item count to original item count
        # Extend with empty items if Korean has fewer
        while len(korean_items) < len(orig_items):
            korean_items.append("")
        # Trim to original count if Korean has more
        korean_items = korean_items[:len(orig_items)]
    else:
        # No original data - strip trailing empties as fallback
        while korean_items and not korean_items[-1].strip():
            korean_items.pop()

    if not korean_items:
        return b"\x00"

    result = bytearray()

    for i, item_text in enumerate(korean_items):
        item_text = item_text.strip()
        if not item_text:
            item_bytes = b""
        else:
            item_bytes = encode_korean_text(item_text, korean_mapping, decode_table)

        is_last = (i == len(korean_items) - 1)

        if i < len(orig_items):
            orig_item = orig_items[i]
            orig_len = orig_item['end'] - orig_item['start']

            # Pad or truncate to match original item byte length
            if len(item_bytes) < orig_len:
                item_bytes = item_bytes + bytes([PACKED_LIST_PAD_BYTE] * (orig_len - len(item_bytes)))
            elif len(item_bytes) > orig_len:
                item_bytes = item_bytes[:orig_len]

            result.extend(item_bytes)

            if not is_last and orig_item['sep_bytes'] is not None:
                # Preserve original separator bytes exactly
                result.extend(orig_item['sep_bytes'])
        else:
            # No original item info - just write content
            result.extend(item_bytes)

    return bytes(result)


def find_string_end(data, offset):
    """Find the true null terminator of a game-encoded string.

    Skips over multi-byte sequences where 0x00 may appear as part of a
    control code (e.g. [FF:1A 00 XX] item separators) rather than as a
    null terminator.

    Returns the offset of the null terminator byte.
    """
    pos = offset
    while pos < len(data):
        b = data[pos]
        if b == 0x00:
            return pos  # Real null terminator
        elif b == 0xFF:
            # 4-byte control code: FF XX XX XX
            pos += 4
        elif 0xF0 <= b <= 0xFE:
            # 2-byte extended character
            pos += 2
        else:
            # 1-byte character (0x01-0xEE, 0xEF)
            pos += 1
    return pos  # End of data (no null found)


def safe_truncate(encoded, available):
    """Truncate encoded bytes at a safe boundary.

    Avoids cutting in the middle of multi-byte sequences:
    - FF XX XX XX: 4-byte control codes
    - F0-F8 XX: 2-byte Korean characters (charID >= 239)
    - EF: 1-byte [opt] marker (safe)
    - 01-9F (excluding EF/F0-F8/FF): 1-byte characters (safe)

    Returns truncated bytes that end at a clean sequence boundary.
    """
    if available <= 0:
        return b""
    if len(encoded) <= available:
        return encoded

    # Walk through encoded bytes to find safe cut points
    pos = 0
    last_safe = 0
    while pos < available:
        b = encoded[pos]
        if b == 0xFF:
            # 4-byte control code: FF XX XX XX
            if pos + 4 <= available:
                last_safe = pos + 4
                pos += 4
            else:
                break  # Would cut mid-sequence
        elif 0xF0 <= b <= 0xF8:
            # 2-byte Korean character: FX XX
            if pos + 2 <= available:
                last_safe = pos + 2
                pos += 2
            else:
                break  # Would cut mid-sequence
        else:
            # 1-byte character
            last_safe = pos + 1
            pos += 1

    return encoded[:last_safe]


def patch_stg_file(stg_path, translation_entries, korean_mapping, decode_table, dry_run=False):
    """Patch STG file with Korean translations.

    Uses fixed-length replacement: Korean text is padded if shorter,
    or truncated if longer than the original Japanese text.
    This is the safe approach that doesn't require pointer updates.
    """
    print(f"Patching STG file: {stg_path}")

    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    patched = 0
    truncated = 0
    errors = 0

    for entry in translation_entries:
        offset = entry["offset"]
        script_prefix = entry["script_prefix"]
        korean_text = entry["text"]

        if offset >= len(data):
            print(f"  ERROR: offset 0x{offset:08X} out of bounds")
            errors += 1
            continue

        # Find the null terminator of the original string,
        # skipping 0x00 bytes inside FF control codes
        orig_end = find_string_end(data, offset + len(script_prefix))

        if orig_end >= len(data):
            print(f"  ERROR: no null terminator found at 0x{offset:08X}")
            errors += 1
            continue

        # Original total size: script_prefix + text + null
        orig_total = orig_end - offset + 1

        # Encode Korean text
        encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

        # New total size: script_prefix + encoded + null
        new_total = len(script_prefix) + len(encoded) + 1

        if new_total <= orig_total:
            # Fits - pad with nulls if shorter
            replacement = script_prefix + encoded + b"\x00"
            padded = replacement + b"\x00" * (orig_total - new_total)
            if not dry_run:
                data[offset:offset + orig_total] = padded
            patched += 1
        else:
            # Too long - truncate at safe byte boundary
            available = orig_total - len(script_prefix) - 1
            truncated_encoded = safe_truncate(encoded, available)
            replacement = script_prefix + truncated_encoded + b"\x00"
            padded = replacement + b"\x00" * (orig_total - len(replacement))
            if not dry_run:
                data[offset:offset + orig_total] = padded
            patched += 1
            truncated += 1

    if not dry_run:
        with open(stg_path, "wb") as f:
            f.write(data)

    print(f"  Patched: {patched} dialogues")
    if truncated:
        print(f"  Truncated (too long): {truncated}")
    if errors:
        print(f"  Errors: {errors}")

    return patched, truncated, errors


def patch_stg_system_text(stg_path, korean_mapping, decode_table):
    """Replace Japanese system messages with Korean across ALL chunks in an STG file.

    These messages (item obtained, switch toggles, stairs, warp zones, etc.) are
    duplicated in every chunk of every STG file. The normal STG patcher uses absolute
    offsets and only patches one chunk. This function does a binary search-and-replace
    to fix all occurrences.

    Each message is wrapped in [box:system]...[box:close] = FF 08 01 01 ... FF 08 02 01.
    We search for the full wrapped pattern and replace the inner content with Korean,
    padding with 0x00 to maintain the same byte length.
    """
    # Define (description, japanese_inner_bytes, korean_text) for all system messages.
    # Inner bytes = everything between FF 08 01 01 and FF 08 02 01.
    # Korean text uses control code tags that encode_korean_text() understands.
    SYSTEM_MESSAGES = [
        # 1. スイッチがあります[br]ONにしてみますか？[br][opt]はい[br][opt]いいえ
        ("Switch ON prompt",
         bytes([0x05, 0x3B, 0x66, 0xF0, 0x98, 0xF1, 0xF0, 0xFF, 0x05, 0x01, 0x01,
                0xAF, 0xAE, 0x4B, 0xF0, 0x5F, 0xEE, 0xFF, 0x05, 0x01, 0x01,
                0xEF, 0xCE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x04, 0x0D, 0xF0, 0x70]),
         "스위치 ON?[br][opt]네[br][opt]아니오"),

        # 2. スイッチはONになっています[br]OFFにしますか？[br][opt]はい[br][opt]いいえ
        ("Switch OFF prompt",
         bytes([0x5D, 0x52, 0xA0, 0x61, 0x1A, 0xAF, 0xAE, 0x16, 0x15, 0x50,
                0x13, 0x02, 0x1F, 0x0D, 0xFF, 0x05, 0x01, 0x01, 0xAF, 0xA6,
                0xA6, 0x16, 0x0C, 0x1F, 0x0D, 0x06, 0xEE, 0xFF, 0x05, 0x01,
                0x01, 0xEF, 0x1A, 0x02, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x02,
                0x02, 0x04]),
         "스위치ON. OFF?[br][opt]네[br][opt]아니오"),

        # 3. スイッチはかたくて元に戻りません[FF:04 02 01]
        ("Switch stuck",
         bytes([0x5D, 0x52, 0xA0, 0x61, 0x1A, 0x06, 0x10, 0x08, 0x13, 0xF1,
                0xA8, 0x16, 0xF5, 0x10, 0x28, 0x1F, 0x0E, 0x2E, 0xFF, 0x04,
                0x02, 0x01]),
         "스위치가 안움직인다[FF:04 02 01]"),

        # 4. ポイントがあります[br]切り替えますか？[br][opt]はい[br][opt]いいえ
        ("Point switch prompt",
         bytes([0x97, 0x52, 0x7E, 0x64, 0x2F, 0x01, 0x28, 0x1F, 0x0D, 0xFF,
                0x05, 0x01, 0x01, 0xF3, 0x04, 0x28, 0xF0, 0xCC, 0x04, 0x1F,
                0x0D, 0x06, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x02, 0x02, 0x04]),
         "포인트 전환?[br][opt]네[br][opt]아니오"),

        # 5. スイッチがあります[br]切り替えますか？[br][opt]はい[br][opt]いいえ
        ("Switch toggle prompt",
         bytes([0x5D, 0x52, 0xA0, 0x61, 0x2F, 0x01, 0x28, 0x1F, 0x0D, 0xFF,
                0x05, 0x01, 0x01, 0xF3, 0x04, 0x28, 0xF0, 0xCC, 0x04, 0x1F,
                0x0D, 0x06, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x02, 0x02, 0x04]),
         "스위치 전환?[br][opt]네[br][opt]아니오"),

        # 6. アイテムを見つけました[br]取りますか？[br][opt]はい[br][opt]いいえ
        ("Item found prompt",
         bytes([0x51, 0x52, 0x63, 0x71, 0x2D, 0xF1, 0xA0, 0x12, 0x09, 0x1F,
                0x0C, 0x10, 0xFF, 0x05, 0x01, 0x01, 0xF2, 0x6B, 0x28, 0x1F,
                0x0D, 0x06, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x02, 0x02, 0x04]),
         "아이템 발견! 획득?[br][opt]네[br][opt]아니오"),

        # 7. [item:01]を見つけました[br]取りますか？[br][opt]はい[br][opt]いいえ
        ("Item:01 found prompt",
         bytes([0xFF, 0x0B, 0x01, 0x01, 0x2D, 0xF1, 0xA0, 0x12, 0x09, 0x1F,
                0x0C, 0x10, 0xFF, 0x05, 0x01, 0x01, 0xF2, 0x6B, 0x28, 0x1F,
                0x0D, 0x06, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x02, 0x02, 0x04]),
         "[item:01] 발견! 획득?[br][opt]네[br][opt]아니오"),

        # 8. [name:01]を見つけました[br]取りますか？[br][opt]はい[br][opt]いいえ
        ("Name:01 found prompt",
         bytes([0xFF, 0x0D, 0x01, 0x01, 0x2D, 0xF1, 0xA0, 0x12, 0x09, 0x1F,
                0x0C, 0x10, 0xFF, 0x05, 0x01, 0x01, 0xF2, 0x6B, 0x28, 0x1F,
                0x0D, 0x06, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x02, 0x02, 0x04]),
         "[name:01] 발견! 획득?[br][opt]네[br][opt]아니오"),

        # 9. アイテムBOXがいっぱいです
        ("Item BOX full",
         bytes([0x51, 0x52, 0x63, 0x71, 0xA2, 0xAF, 0xB8, 0x2F, 0x02, 0x50,
                0x43, 0x02, 0x3C, 0x0D]),
         "아이템BOX가득"),

        # 10. アイテムを取りました
        ("Item taken",
         bytes([0x51, 0x52, 0x63, 0x71, 0x2D, 0xF2, 0x6B, 0x28, 0x1F, 0x0C, 0x10]),
         "아이템 획득!"),

        # 11. おれはもうあいている
        ("Already open",
         bytes([0x05, 0x2A, 0x1A, 0x23, 0x03, 0x01, 0x02, 0x13, 0x02, 0x29]),
         "비어있다"),

        # 12. 何も入っていません
        ("Nothing inside",
         bytes([0xF4, 0x0F, 0x23, 0xF4, 0x20, 0x50, 0x13, 0x02, 0x1F, 0x0E, 0x2E]),
         "아무것도 없다"),

        # 13. [opt]全滅しました[opt]
        ("Party wiped",
         bytes([0xEF, 0xF3, 0x1A, 0xF5, 0x0A, 0x0C, 0x1F, 0x0C, 0x10, 0xEF]),
         "[opt]전멸[opt]"),

        # 14. [item:01]を手に入れました
        ("Item:01 obtained",
         bytes([0xFF, 0x0B, 0x01, 0x01, 0x2D, 0xF3, 0xBE, 0x16, 0xF4, 0x20,
                0x2A, 0x1F, 0x0C, 0x10]),
         "[item:01]를 획득했다"),

        # 15. [name:01]を手に入れました
        ("Name:01 obtained",
         bytes([0xFF, 0x0D, 0x01, 0x01, 0x2D, 0xF3, 0xBE, 0x16, 0xF4, 0x20,
                0x2A, 0x1F, 0x0C, 0x10]),
         "[name:01]를 획득했다"),

        # 16. アイテムがいっぱいで入手できません
        ("Items full, can't obtain",
         bytes([0x51, 0x52, 0x63, 0x71, 0x2F, 0x02, 0x50, 0x43, 0x02, 0x3C,
                0xF4, 0x20, 0xF3, 0xBE, 0x3C, 0x07, 0x1F, 0x0E, 0x2E]),
         "아이템 가득! 입수불가"),

        # 17. [item:01]をあきらめますか[br][opt]はい[br][opt]いいえ
        ("Give up item:01?",
         bytes([0xFF, 0x0B, 0x01, 0x01, 0x2D, 0x01, 0x07, 0x27, 0x22, 0x1F,
                0x0D, 0x06, 0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01,
                0x1A, 0x02, 0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01,
                0x02, 0x02, 0x04]),
         "[item:01] 포기?[br][FF:04 02 01]네[br][FF:04 02 01]아니오"),

        # 18. [name:01]をあきらめますか[br][opt]はい[br][opt]いいえ
        ("Give up name:01?",
         bytes([0xFF, 0x0D, 0x01, 0x01, 0x2D, 0x01, 0x07, 0x27, 0x22, 0x1F,
                0x0D, 0x06, 0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01,
                0x1A, 0x02, 0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01,
                0x02, 0x02, 0x04]),
         "[name:01] 포기?[br][FF:04 02 01]네[br][FF:04 02 01]아니오"),

        # 19. [item:01]を入手できません[br]アイテムがいっぱいです[br]捨てますか？[br][opt]はい[br][opt]いいえ
        ("Item:01 can't obtain, discard?",
         bytes([0xFF, 0x0B, 0x01, 0x01, 0x2D, 0xF4, 0x20, 0xF3, 0xBE, 0x3C,
                0x07, 0x1F, 0x0E, 0x2E, 0xFF, 0x05, 0x01, 0x01, 0x51, 0x52,
                0x63, 0x71, 0x2F, 0x02, 0x50, 0x43, 0x02, 0x3C, 0x0D, 0xEC,
                0xF4, 0x0F, 0x06, 0xF2, 0xE7, 0x13, 0x1F, 0x0D, 0x06, 0xEE,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02, 0xFF, 0x05, 0x01,
                0x01, 0xEF, 0x02, 0x02, 0x04]),
         "[item:01] 입수불가[br]BOX가득! 버릴까?[br][opt]네[br][opt]아니오"),

        # 20. [name:01]を入手できません[br]アイテムがいっぱいです[br]捨てますか？[br][opt]はい[br][opt]いいえ
        ("Name:01 can't obtain, discard?",
         bytes([0xFF, 0x0D, 0x01, 0x01, 0x2D, 0xF4, 0x20, 0xF3, 0xBE, 0x3C,
                0x07, 0x1F, 0x0E, 0x2E, 0xFF, 0x05, 0x01, 0x01, 0x51, 0x52,
                0x63, 0x71, 0x2F, 0x02, 0x50, 0x43, 0x02, 0x3C, 0x0D, 0xEC,
                0xF4, 0x0F, 0x06, 0xF2, 0xE7, 0x13, 0x1F, 0x0D, 0x06, 0xEE,
                0xFF, 0x05, 0x01, 0x01, 0xEF, 0x1A, 0x02, 0xFF, 0x05, 0x01,
                0x01, 0xEF, 0x02, 0x02, 0x04]),
         "[name:01] 입수불가[br]BOX가득! 버릴까?[br][opt]네[br][opt]아니오"),

        # 21. 下り階段があります[br][opt]下る[br][opt]やめる
        ("Stairs down",
         bytes([0xF0, 0xB1, 0xF0, 0xA0, 0xF0, 0x98, 0xF1, 0xF0, 0xFF, 0x05,
                0x01, 0x01, 0xEF, 0xF0, 0x6C, 0xF0, 0x88, 0x0C, 0x18, 0xFF,
                0x05, 0x01, 0x01, 0xEF, 0x2F, 0x55, 0x8C, 0x18]),
         "계단[br][opt]내려감[br][opt]취소"),

        # 22. 上り階段があります[br][opt]上る[br][opt]やめる
        ("Stairs up",
         bytes([0xF0, 0xB1, 0xF0, 0xA0, 0xF0, 0x98, 0xF1, 0xF0, 0xFF, 0x05,
                0x01, 0x01, 0xEF, 0xF0, 0x72, 0x0E, 0x0C, 0x18, 0xFF, 0x05,
                0x01, 0x01, 0xEF, 0x2F, 0x55, 0x8C, 0x18]),
         "계단[br][opt]올라감[br][opt]취소"),

        # 23. 出口です。外に出ますか？[br][opt]はい[br][opt]やめる
        ("Exit prompt",
         bytes([0xF1, 0x40, 0x41, 0x02, 0xF0, 0x09, 0x36, 0xF0, 0xB4, 0xF0,
                0x5F, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0xCE, 0xFF, 0x05,
                0x01, 0x01, 0xEF, 0x04, 0x0D, 0xF0, 0x70]),
         "출구. 나갈까?[br][opt]네[br][opt]취소"),

        # 24. ハシゴがあります[br][opt]上る[br][opt]やめる
        ("Ladder up",
         bytes([0x1C, 0x02, 0x08, 0x02, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0xF0,
                0x72, 0x0E, 0x0C, 0x18, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x2F,
                0x55, 0x8C, 0x18]),
         "사다리[br][opt]올라감[br][opt]취소"),

        # 25. ワープゾーンがあります[br][opt]ワープする[br][opt]やめる
        ("Warp zone",
         bytes([0x6A, 0x5C, 0x83, 0x2F, 0x01, 0x28, 0x1F, 0x0D, 0xFF, 0x05,
                0x01, 0x01, 0xEF, 0xF2, 0x55, 0x29, 0xFF, 0x05, 0x01, 0x01,
                0xEF, 0x24, 0x22, 0x29]),
         "워프존[br][opt]워프[br][opt]취소"),

        # 26. どちらにしますか？[br][opt]ふつうのお店[br][opt]でばっぐ用お店
        ("Debug shop prompt",
         bytes([0x0A, 0xF1, 0xB5, 0x3F, 0x11, 0x1A, 0xF0, 0xBE, 0xF0, 0x5C,
                0x0D, 0xF0, 0x5F, 0xEE, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x30,
                0x43, 0xF0, 0x6B, 0xFF, 0x05, 0x01, 0x01, 0xEF, 0x4C, 0x3D,
                0x2F, 0xF0, 0x6B]),
         "어느쪽?[br][opt]일반상점[br][opt]디버그상점"),

        # 27. [item:01]を入手できません[br]アイテムがいっぱいです。何か捨てますか？[br][FF:04 02 01]はい[br][FF:04 02 01]いいえ
        #     (decoder-missed; ~382 occurrences across STG files)
        ("Inventory full (item)",
         bytes([0xFF, 0x0B, 0x01, 0x01, 0x2D, 0xF4, 0x20, 0xF3, 0xBE, 0x3C,
                0x07, 0x1F, 0x0E, 0x2E, 0xFF, 0x05, 0x01, 0x01, 0x51, 0x52,
                0x63, 0x71, 0x2F, 0x02, 0x50, 0x43, 0x02, 0x3C, 0x0D, 0xEC,
                0xF4, 0x0F, 0x06, 0xF2, 0xE7, 0x13, 0x1F, 0x0D, 0x06, 0xEE,
                0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01, 0x02, 0x02,
                0x04]),
         "[item:01]을 입수못함[br]아이템 가득. 버릴까?[br][FF:04 02 01]네[br][FF:04 02 01]아니오"),

        # 28. [name:01]を入手できません[br]... (same message, [name:01] variant; ~382 occurrences)
        ("Inventory full (name)",
         bytes([0xFF, 0x0D, 0x01, 0x01, 0x2D, 0xF4, 0x20, 0xF3, 0xBE, 0x3C,
                0x07, 0x1F, 0x0E, 0x2E, 0xFF, 0x05, 0x01, 0x01, 0x51, 0x52,
                0x63, 0x71, 0x2F, 0x02, 0x50, 0x43, 0x02, 0x3C, 0x0D, 0xEC,
                0xF4, 0x0F, 0x06, 0xF2, 0xE7, 0x13, 0x1F, 0x0D, 0x06, 0xEE,
                0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01, 0x1A, 0x02,
                0xFF, 0x05, 0x01, 0x01, 0xFF, 0x04, 0x02, 0x01, 0x02, 0x02,
                0x04]),
         "[name:01]을 입수못함[br]아이템 가득. 버릴까?[br][FF:04 02 01]네[br][FF:04 02 01]아니오"),
    ]

    # Box wrapper codes
    BOX_OPEN = b"\xFF\x08\x01\x01"
    BOX_CLOSE = b"\xFF\x08\x02\x01"

    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    total_replacements = 0

    for desc, jp_inner, kr_text in SYSTEM_MESSAGES:
        # Build the full search pattern: [box:system] + inner + [box:close]
        search_pattern = BOX_OPEN + jp_inner + BOX_CLOSE

        # Encode Korean text
        kr_encoded = encode_korean_text(kr_text, korean_mapping, decode_table)

        # Build replacement inner: Korean bytes padded with 0x00 to match original length
        jp_inner_len = len(jp_inner)
        kr_inner_len = len(kr_encoded)

        if kr_inner_len > jp_inner_len:
            print(f"  WARNING: '{desc}' Korean ({kr_inner_len}B) > Japanese ({jp_inner_len}B), skipping")
            continue

        # Pad Korean to same length as Japanese inner
        kr_padded = kr_encoded + b"\x00" * (jp_inner_len - kr_inner_len)

        # Build full replacement
        replacement = BOX_OPEN + kr_padded + BOX_CLOSE

        # Search and replace all occurrences
        count = 0
        pos = 0
        while True:
            idx = data.find(search_pattern, pos)
            if idx < 0:
                break
            data[idx:idx + len(search_pattern)] = replacement
            count += 1
            pos = idx + len(replacement)

        if count > 0:
            total_replacements += count

    # Write back
    if total_replacements > 0:
        with open(stg_path, "wb") as f:
            f.write(data)

    stg_name = os.path.basename(stg_path)
    print(f"  System text: {total_replacements} replacements in {stg_name}")
    return total_replacements


def patch_stg_orphan_names(stg_path, korean_mapping, decode_table):
    """Replace Japanese orphan name entries with Korean across all chunks.

    Orphan menu entries (opcode 0x00A9) contain standalone names that the
    normal STG patcher misses. These are character, monster, and location
    names stored as katakana text in text/event/data regions.

    Searches for [japanese_charID_bytes][0x00] and replaces with
    [korean_encoded_bytes][padding][0x00], preserving the same byte length.
    """
    encode_table = build_encode_table(decode_table)

    # (Japanese name, Korean translation)
    ORPHAN_NAMES = [
        # === Location names (SH00 world map) ===
        ("パレンシア", "팔렌시아"),
        ("パレンシアタワー", "팔렌시아타워"),
        ("ダウンタウン", "다운타운"),
        ("ロマリアトンネル", "로마리아터널"),
        ("ラムール", "라무르"),
        ("ホルン", "호른"),
        ("ペイサス", "페이사스"),
        ("ルワガ", "루가"),  # 3B limit: shortened from 루와가
        ("モレア", "모레아"),
        ("アジャール", "아자르"),
        ("ムハド", "무하드"),
        ("ピラミッド", "피라밋드"),
        ("ガザルア", "가잘아"),
        ("ミスロ", "미슬로"),
        ("エルザーク", "엘자크"),
        # These 6 appear with [br] prefix in SH00; searching the base name
        # still matches because the name is at the end followed by 0x00
        ("フォーレス", "포레스"),
        ("グレイシーヌ", "그레이시누"),
        ("ミルマーナ", "밀마나"),
        ("バルバラード", "발바라드"),
        ("アララトス", "아라라토스"),
        ("アリバーシャ", "아리바샤"),
        # === Character / NPC names ===
        ("ガルアーノ", "갈아노"),
        ("ネクダス", "네크다스"),
        ("ジグムント", "지그문트"),
        ("アンデル", "안델"),
        ("ダルシオス", "달시"),  # 5B limit: shortened from 달시오스
        ("ゴーガス", "고가스"),
        ("クェーガー", "쿠에가"),
        ("ガウクロウ", "가우크로우"),
        ("キドウ", "기도"),  # 3B limit: shortened from 키도우
        ("ビシャモン", "비샤몬"),
        ("ベラドンナ", "벨라나"),  # 5B limit: shortened from 벨라돈나
        ("ピエール・ベロニカ", "피에르베로니카"),
        ("リーランド", "리란드"),
        ("バルドル", "발도르"),
        ("ゴルザ", "골자"),
        ("ティアヌス", "티아누스"),
        ("グルナグ", "그루나그"),
        ("バルザック", "발작"),
        ("シャコウ", "샤코우"),
        ("ジャド", "자드"),
        ("ホイスラー", "호이슬러"),
        ("ダリウス", "다리우스"),
        ("キッシュ", "킷슈"),
        ("ギオネス", "기오"),  # 4B limit: shortened from 기오네스
        ("グロヴィス", "그로비스"),
        ("レイガル", "레이갈"),
        ("ジンバラ", "진바라"),
        ("ミラルダ", "미랄다"),
        ("マーリン", "마린"),
        ("リシェーナ", "리셰나"),
        ("ディロス", "디로스"),
        ("メナン", "메난"),
        ("ドラロシュ", "드라로슈"),
        ("バルグリ", "발그리"),
        ("デリンガー", "데린가"),
        ("アミーグロック", "아미그록"),
        ("ドルゴン", "돌곤"),
        ("ゴルゴン", "골곤"),
        ("グラヴィス", "그라비스"),
        ("ザナック", "자낙"),
        ("シュヴァイデル", "슈바이델"),
        ("タスマン", "타스만"),
        ("ガルムヘッド", "갈름헤드"),
        ("シャムス", "샤무스"),
        ("ジャッカル", "자칼"),
        ("アクラ", "아크라"),
        ("ジャッジメント", "저지먼트"),
        ("ドクスン", "독슨"),
        ("ザルバドビット", "잘바드비트"),
        # === Onomatopoeia / short words ===
        # フフフ(3B), ウウッ(3B), セウム(3B), アジュ(3B) skipped: no Korean fits
        # ギギギ removed: 3-byte pattern 80 80 80 matches event script bytecode (0x80 is common),
        # causing 18 false-positive replacements that corrupt script parameters and freeze the game.
        # Handle via offset-based S*_STG.txt entries instead.
    ]

    def encode_jp_name(name):
        """Convert Japanese name string to game charID bytes."""
        result = bytearray()
        for ch in name:
            if ch in encode_table:
                b = char_id_to_bytes(encode_table[ch])
                if b:
                    result.extend(b)
                else:
                    return None
            else:
                return None
        return bytes(result)

    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    CHUNK_SIZE = 0xBC800
    # Search from MIPS scene code to end of text region to cover
    # both text entries and data tables embedded in code sections
    SEARCH_START = 0x77000
    num_chunks = len(data) // CHUNK_SIZE
    total_replacements = 0

    for jp_name, kr_name in ORPHAN_NAMES:
        jp_bytes = encode_jp_name(jp_name)
        if jp_bytes is None:
            continue

        kr_encoded = encode_korean_text(kr_name, korean_mapping, decode_table)

        if len(kr_encoded) > len(jp_bytes):
            print(f"    WARNING: '{jp_name}'->'{kr_name}' Korean ({len(kr_encoded)}B) > Japanese ({len(jp_bytes)}B), skipping")
            continue

        search_pattern = jp_bytes + b"\x00"
        kr_padded = kr_encoded + b"\x00" * (len(jp_bytes) - len(kr_encoded)) + b"\x00"

        count = 0
        for chunk_idx in range(num_chunks):
            chunk_start = chunk_idx * CHUNK_SIZE
            region_start = chunk_start + SEARCH_START
            region_end = chunk_start + CHUNK_SIZE

            if region_end > len(data):
                break

            pos = region_start
            while pos < region_end:
                idx = data.find(search_pattern, pos, region_end)
                if idx < 0:
                    break
                data[idx:idx + len(search_pattern)] = kr_padded
                count += 1
                pos = idx + len(kr_padded)

        if count > 0:
            total_replacements += count

    # === Item names with kanji (raw byte patterns) ===
    # Kanji charIDs may not be in encode_table, so we use raw bytes directly.
    # Format: (japanese_bytes, korean_text)
    ORPHAN_ITEM_BYTES = [
        # Elemental prefix charIDs: DF=地, E0=水, E1=火, E2=風,
        #   F1 C4=光, F5 24=闇
        # Stat charIDs: F2 6C=守, F2 69=弱
        # Common: 19=の, 28=り, F1 6D=薬
        # --- 守りの薬 (Protective Medicine) series ---
        (bytes([0xDF, 0x19, 0xF2, 0x6C, 0x28, 0x19, 0xF1, 0x6D]),
         "대지의수호약"),       # 地の守りの薬
        (bytes([0xE0, 0x19, 0xF2, 0x6C, 0x28, 0x19, 0xF1, 0x6D]),
         "물의수호약"),         # 水の守りの薬
        (bytes([0xE1, 0x19, 0xF2, 0x6C, 0x28, 0x19, 0xF1, 0x6D]),
         "불의수호약"),         # 火の守りの薬
        (bytes([0xE2, 0x19, 0xF2, 0x6C, 0x28, 0x19, 0xF1, 0x6D]),
         "풍의수호약"),         # 風の守りの薬
        (bytes([0xF1, 0xC4, 0x19, 0xF2, 0x6C, 0x28, 0x19, 0xF1, 0x6D]),
         "빛의수호약"),         # 光の守りの薬
        (bytes([0xF5, 0x24, 0x19, 0xF2, 0x6C, 0x28, 0x19, 0xF1, 0x6D]),
         "어둠의수호약"),       # 闇の守りの薬
        # --- 弱りの薬 (Weakening Medicine) series ---
        (bytes([0xDF, 0x19, 0xF2, 0x69, 0x28, 0x19, 0xF1, 0x6D]),
         "대지의약화약"),       # 地の弱りの薬
        (bytes([0xE0, 0x19, 0xF2, 0x69, 0x28, 0x19, 0xF1, 0x6D]),
         "물의약화약"),         # 水の弱りの薬
        (bytes([0xE1, 0x19, 0xF2, 0x69, 0x28, 0x19, 0xF1, 0x6D]),
         "불의약화약"),         # 火の弱りの薬
        (bytes([0xE2, 0x19, 0xF2, 0x69, 0x28, 0x19, 0xF1, 0x6D]),
         "풍의약화약"),         # 風の弱りの薬
        (bytes([0xF1, 0xC4, 0x19, 0xF2, 0x69, 0x28, 0x19, 0xF1, 0x6D]),
         "빛의약화약"),         # 光の弱りの薬
        (bytes([0xF5, 0x24, 0x19, 0xF2, 0x69, 0x28, 0x19, 0xF1, 0x6D]),
         "어둠의약화약"),       # 闇の弱りの薬
    ]

    for jp_bytes, kr_name in ORPHAN_ITEM_BYTES:
        kr_encoded = encode_korean_text(kr_name, korean_mapping, decode_table)

        if len(kr_encoded) > len(jp_bytes):
            print(f"    WARNING: item '{kr_name}' Korean ({len(kr_encoded)}B) "
                  f"> Japanese ({len(jp_bytes)}B), skipping")
            continue

        search_pattern = jp_bytes + b"\x00"
        kr_padded = (kr_encoded
                     + b"\x00" * (len(jp_bytes) - len(kr_encoded))
                     + b"\x00")

        count = 0
        for chunk_idx in range(num_chunks):
            chunk_start = chunk_idx * CHUNK_SIZE
            region_start = chunk_start + SEARCH_START
            region_end = chunk_start + CHUNK_SIZE

            if region_end > len(data):
                break

            pos = region_start
            while pos < region_end:
                idx = data.find(search_pattern, pos, region_end)
                if idx < 0:
                    break
                data[idx:idx + len(search_pattern)] = kr_padded
                count += 1
                pos = idx + len(kr_padded)

        if count > 0:
            total_replacements += count

    if total_replacements > 0:
        with open(stg_path, "wb") as f:
            f.write(data)

    stg_name = os.path.basename(stg_path)
    print(f"  Orphan names: {total_replacements} replacements in {stg_name}")
    return total_replacements


def save_mapping(mapping, output_path):
    """Save the Korean character mapping to a file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Korean character to charID mapping\n")
        f.write("# Format: korean_char<tab>charID<tab>hex_encoding\n\n")
        for kr_char, char_id in sorted(mapping.items(), key=lambda x: x[1]):
            encoded = char_id_to_bytes(char_id)
            hex_str = " ".join(f"{b:02X}" for b in encoded) if encoded else "??"
            f.write(f"{kr_char}\t{char_id}\t{hex_str}\n")
    print(f"Saved mapping to: {output_path}")


def parse_system_translation_file(translation_path):
    """Parse system message translation file (SCPS_100_26_system.txt).

    Format: offset<tab>japanese<tab>korean
    Example: 0x000D3580	空きブロックが足りません	빈 블록이 부족합니다

    Returns: list of (offset, korean_text)
    """
    entries = []

    with open(translation_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue

            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    offset = int(parts[0], 16)
                    korean_text = parts[2]
                    entries.append({
                        "offset": offset,
                        "text": korean_text
                    })
                except ValueError:
                    continue

    return entries


def parse_sdic_translation_file(translation_path):
    """Parse SDIC.BIN translation file.

    Format: offset,korean_text
    Example: 0x0000644C,처음에는 나쁜 사람인 줄 알았는데...

    Returns: list of dict with offset and text
    """
    entries = []

    with open(translation_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split on first comma only (text may contain commas)
            if "," in line:
                offset_str, korean_text = line.split(",", 1)
                try:
                    offset = int(offset_str, 16)
                    entries.append({
                        "offset": offset,
                        "text": korean_text
                    })
                except ValueError:
                    continue

    return entries


def parse_bin_translation_file(translation_path):
    """Parse non-STG translation file in the standard decoded format.

    Format:   0xOFFSET [LENGTH] text
    Example:  0x000D2708 [   7] 엘리멘탈

    Also supports legacy CSV format for backwards compatibility:
    Format: offset,text
    Example: 0x0000644C,처음에는 나쁜 사람인 줄 알았는데...

    Returns: list of dict with offset, text, and optionally orig_length
    """
    entries = []

    with open(translation_path, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                continue

            # Try new format first: 2-space indent + 0xOFFSET [LENGTH] text
            match = re.match(
                r'^\s*0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$',
                line
            )
            if match:
                try:
                    offset = int(match.group(1), 16)
                    orig_length = int(match.group(2))
                    text = match.group(3)
                    entries.append({
                        "offset": offset,
                        "orig_length": orig_length,  # Original Japanese byte length
                        "text": text
                    })
                except ValueError:
                    pass
                continue

            # Fall back to legacy CSV format: offset,text
            if "," in line_stripped:
                offset_str, korean_text = line_stripped.split(",", 1)
                try:
                    offset = int(offset_str, 16)
                    entries.append({
                        "offset": offset,
                        "orig_length": None,  # Unknown in legacy format
                        "text": korean_text
                    })
                except ValueError:
                    continue

    return entries


def validate_translation_lengths(entries, korean_mapping, decode_table, file_name=""):
    """Validate that Korean translations fit within original slot sizes.

    Args:
        entries: List of translation entries with offset, orig_length, text
        korean_mapping: Korean char to charID mapping
        decode_table: Character decode table
        file_name: Name of file for error messages

    Returns: tuple (valid_count, warning_count, warnings_list)
    """
    valid = 0
    warnings = []

    for entry in entries:
        offset = entry["offset"]
        orig_length = entry.get("orig_length")
        text = entry["text"]

        # Skip if no orig_length (legacy format)
        if orig_length is None:
            valid += 1
            continue

        # Encode Korean text to get actual byte length
        encoded = encode_korean_text(text, korean_mapping, decode_table)
        new_length = len(encoded)

        if new_length > orig_length:
            overflow = new_length - orig_length
            warnings.append({
                "offset": offset,
                "orig_length": orig_length,
                "new_length": new_length,
                "overflow": overflow,
                "text": text[:30] + "..." if len(text) > 30 else text
            })
        else:
            valid += 1

    return valid, len(warnings), warnings


def _detect_box_wrapping(data, offset, orig_total):
    """Detect FF 08 box:system wrapping around a text entry.

    Many BEAM.DAT entries are wrapped: [box:open][text][box:close][null].
    The translation text only contains the inner content, so we must
    detect and preserve the box control codes during patching.

    Returns (prefix, suffix) byte strings, both empty if no wrapping found.
    """
    if orig_total < 9:  # Minimum: 4 open + 0 text + 4 close + 1 null
        return b'', b''

    # Check box open at start: FF 08 XX 01 where XX = 01/03/05/07
    if (data[offset] == 0xFF and data[offset + 1] == 0x08 and
            data[offset + 3] == 0x01 and
            data[offset + 2] in (0x01, 0x03, 0x05, 0x07)):
        # Check box close before null: FF 08 02 01
        close_pos = offset + orig_total - 5  # 4 bytes close + 1 null
        if (data[close_pos] == 0xFF and data[close_pos + 1] == 0x08 and
                data[close_pos + 2] == 0x02 and data[close_pos + 3] == 0x01):
            return bytes(data[offset:offset + 4]), bytes(data[close_pos:close_pos + 4])

    return b'', b''


def patch_bin_file(bin_path, translation_entries, korean_mapping, decode_table, dry_run=False):
    """Patch a BIN file (SDIC.BIN, SMITH.BIN, etc.) with Korean translations.

    Uses fixed-length replacement: Korean text is padded if shorter,
    or truncated if longer than the original Japanese text.

    For box-wrapped entries (FF 08 XX 01 ... FF 08 02 01), the box
    control codes are automatically detected and preserved. The Korean
    text only replaces the inner content between box open and box close.
    """
    print(f"Patching BIN file: {bin_path}")

    with open(bin_path, "rb") as f:
        data = bytearray(f.read())

    patched = 0
    truncated = 0
    errors = 0
    box_preserved = 0

    for entry in translation_entries:
        offset = entry["offset"]
        korean_text = entry["text"]

        if offset >= len(data):
            print(f"  ERROR: offset 0x{offset:08X} out of bounds")
            errors += 1
            continue

        # Find the null terminator of the original string,
        # skipping 0x00 bytes inside FF control codes
        orig_end = find_string_end(data, offset)

        if orig_end >= len(data):
            print(f"  ERROR: no null terminator found at 0x{offset:08X}")
            errors += 1
            continue

        # Original total size: text + null
        orig_total = orig_end - offset + 1

        # Detect packed item lists (entries with FF 1A or FF 19 separators)
        is_packed_list = "[FF:1A" in korean_text or "[FF:19" in korean_text

        if is_packed_list:
            # Packed list: preserve original separators and pad items
            encoded = encode_packed_list(korean_text, korean_mapping, decode_table, orig_data=data, base_offset=offset)
        else:
            # Regular string: encode as flat text
            encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

        # Detect box wrapping (FF 08 XX 01 ... FF 08 02 01)
        box_prefix, box_suffix = _detect_box_wrapping(data, offset, orig_total)

        if box_prefix and box_suffix:
            # Box-wrapped entry: preserve box codes, only replace inner text
            inner_space = orig_total - len(box_prefix) - len(box_suffix) - 1
            if len(encoded) <= inner_space:
                inner = encoded + b'\x00' * (inner_space - len(encoded))
            else:
                inner = safe_truncate(encoded, inner_space)
                if len(inner) < inner_space:
                    inner = inner + b'\x00' * (inner_space - len(inner))
                truncated += 1
            replacement = box_prefix + inner + box_suffix + b'\x00'
            if not dry_run:
                data[offset:offset + orig_total] = replacement
            patched += 1
            box_preserved += 1
        else:
            # Non-box entry: standard replacement
            new_total = len(encoded) + 1

            if new_total <= orig_total:
                # Fits - pad with nulls if shorter
                replacement = encoded + b"\x00"
                padded = replacement + b"\x00" * (orig_total - new_total)
                if not dry_run:
                    data[offset:offset + orig_total] = padded
                patched += 1
            else:
                # Too long - truncate at safe byte boundary
                if is_packed_list:
                    print(f"  WARNING: packed list at 0x{offset:08X} too long "
                          f"({new_total}B > {orig_total}B)")
                available = orig_total - 1
                truncated_encoded = safe_truncate(encoded, available)
                replacement = truncated_encoded + b"\x00"
                padded = replacement + b"\x00" * (orig_total - len(replacement))
                if not dry_run:
                    data[offset:offset + orig_total] = padded
                patched += 1
                truncated += 1

    if not dry_run:
        with open(bin_path, "wb") as f:
            f.write(data)

    print(f"  Patched: {patched} entries")
    if box_preserved:
        print(f"  Box-wrapped (preserved): {box_preserved}")
    if truncated:
        print(f"  Truncated (too long): {truncated}")
    if errors:
        print(f"  Errors: {errors}")

    return patched, truncated, errors


# Equipment item name byte patterns in BEAM.DAT
# These are pre-composed item names in equipment data records (outside text regions)
# Japanese bytes are from the game's fixed charmap; Korean text is dynamically encoded
BEAM_EQUIPMENT_PATTERNS = [
    # 疾風のバンダナ → 질풍의반다나
    (b'\xf1\xe9\xe2\x19\x8e\x7e\x89\x65', "질풍의반다나"),
    # 反撃のバンダナ → 반격의반다나
    (b'\xf3\x83\xf1\x51\x19\x8e\x7e\x89\x65', "반격의반다나"),
    # 長老のはちまき → 장로의머리띠
    (b'\xf2\xed\xf4\x6a\x19\x1a\x11\x1f\x07', "장로의머리띠"),
    # 女神のいのり → 여신의기도
    (b'\xf0\x8c\xf0\xc2\x19\x02\x19\x28', "여신의기도"),
    # ロマンシングストーン → 로맨싱스톤
    (b'\x7b\x6f\x7e\x5c\x7e\x81\x5d\x64\xe3\x7e', "로맨싱스톤"),
    # うつせみの衣 → 우츠세미의옷
    (b'\x03\x12\x0e\x20\x19\xf2\xca', "우츠세미의옷"),
]


def patch_beam_equipment(beam_path, korean_mapping, decode_table, dry_run=False):
    """Patch equipment item names in BEAM.DAT data records.

    Equipment data records contain pre-composed item names at fixed chunk
    offsets, repeated across chunks 11-44. These are outside the text regions
    handled by patch_bin_file(), so they need direct binary replacement.
    """
    print(f"  Patching BEAM equipment item names...")

    with open(beam_path, "rb") as f:
        data = bytearray(f.read())

    total_patched = 0

    for jp_bytes, kr_text in BEAM_EQUIPMENT_PATTERNS:
        kr_encoded = encode_korean_text(kr_text, korean_mapping, decode_table)
        # When Korean is longer, extend search pattern with trailing nulls
        # so the replacement has enough room (item names live in null-padded slots)
        search_pattern = jp_bytes
        if len(kr_encoded) > len(jp_bytes):
            extra = len(kr_encoded) - len(jp_bytes)
            search_pattern = jp_bytes + b'\x00' * extra
        # Pad replacement to match search pattern length
        kr_padded = kr_encoded + b'\x00' * (len(search_pattern) - len(kr_encoded))

        # Find and replace all occurrences
        count = 0
        pos = 0
        while True:
            idx = data.find(search_pattern, pos)
            if idx == -1:
                break
            if not dry_run:
                data[idx:idx + len(search_pattern)] = kr_padded
            count += 1
            pos = idx + len(search_pattern)

        if count:
            print(f"    {kr_text}: {count} occurrences patched")
        total_patched += count

    if not dry_run and total_patched > 0:
        with open(beam_path, "wb") as f:
            f.write(data)

    print(f"  Equipment items patched: {total_patched}")
    return total_patched


def patch_exe_file(exe_path, translation_entries, korean_mapping, decode_table, dry_run=False):
    """Patch SCPS_100.26 executable with Korean system messages.

    Uses fixed-length replacement: Korean text is padded if shorter,
    or truncated if longer than the original Japanese text.
    """
    print(f"Patching EXE file: {exe_path}")

    with open(exe_path, "rb") as f:
        data = bytearray(f.read())

    patched = 0
    truncated = 0
    errors = 0

    for entry in translation_entries:
        offset = entry["offset"]
        korean_text = entry["text"]

        if offset >= len(data):
            print(f"  ERROR: offset 0x{offset:08X} out of bounds")
            errors += 1
            continue

        # Find the null terminator of the original string,
        # skipping 0x00 bytes inside FF control codes
        orig_end = find_string_end(data, offset)

        if orig_end >= len(data):
            print(f"  ERROR: no null terminator found at 0x{offset:08X}")
            errors += 1
            continue

        # Original total size: text + null
        orig_total = orig_end - offset + 1

        # Detect packed item lists (entries with FF 1A or FF 19 separators)
        is_packed_list = "[FF:1A" in korean_text or "[FF:19" in korean_text

        if is_packed_list:
            # Packed list: encode with proper separators and alignment
            encoded = encode_packed_list(korean_text, korean_mapping, decode_table, orig_data=data, base_offset=offset)
        else:
            # Regular string: encode as flat text
            encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

        # New total size: encoded + null
        new_total = len(encoded) + 1

        if new_total <= orig_total:
            # Fits - pad with nulls if shorter
            replacement = encoded + b"\x00"
            padded = replacement + b"\x00" * (orig_total - new_total)
            if not dry_run:
                data[offset:offset + orig_total] = padded
            patched += 1
        else:
            # Too long - truncate at safe byte boundary
            if is_packed_list:
                # For packed lists, truncation is a critical error
                print(f"  WARNING: packed list at 0x{offset:08X} too long "
                      f"({new_total}B > {orig_total}B)")
            available = orig_total - 1
            truncated_encoded = safe_truncate(encoded, available)
            replacement = truncated_encoded + b"\x00"
            padded = replacement + b"\x00" * (orig_total - len(replacement))
            if not dry_run:
                data[offset:offset + orig_total] = padded
            patched += 1
            truncated += 1

    if not dry_run:
        with open(exe_path, "wb") as f:
            f.write(data)

    print(f"  Patched: {patched} system messages")
    if truncated:
        print(f"  Truncated (too long): {truncated}")
    if errors:
        print(f"  Errors: {errors}")

    return patched, truncated, errors


def main():
    parser = argparse.ArgumentParser(description="Patch Arc the Lad 2 with Korean translation")
    parser.add_argument("stage", nargs="?", help="Stage name (e.g., S100)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--system", action="store_true", help="Patch SCPS_100.26 system messages")
    args = parser.parse_args()

    print(f"=== Arc the Lad 2 Korean Patcher ===")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Common setup
    comm_src = os.path.join(GAME_DIR, "COMM.IMG")
    comm_dst = os.path.join(OUTPUT_DIR, "COMM.IMG")

    # Load character table
    print("Loading character table...")
    decode_table = load_decode_table()
    print(f"  Loaded {len(decode_table)} characters")

    # Collect ALL translation files to build unified charmap with per-source frequency
    # Priority: SCPS > BEAM > other BIN > STG (fixed-length binaries need single-byte most)
    trans_dir = os.path.join(BASE_DIR, "translated", "ko")

    # Map file basenames to frequency category
    FREQ_CATEGORY = {
        "SCPS_100_26.txt": "scps",
        "BEAM_DAT.txt": "beam",
        "SDIC_BIN.txt": "other", "YGUILD_BIN.txt": "other", "SMITH_BIN.txt": "other",
    }

    print("Extracting Korean characters from ALL translations...")
    all_korean_chars = set()
    scps_frequency = {}
    beam_frequency = {}
    other_non_stg_frequency = {}
    stg_frequency = {}

    trans_files_found = []
    for filename in sorted(os.listdir(trans_dir)):
        filepath = os.path.join(trans_dir, filename)
        if not filename.endswith(".txt") or not os.path.isfile(filepath):
            continue
        # Skip backup/old/correction/pattern files
        if any(x in filename.lower() for x in ["_old", "backup", "correction", "pattern", "unique"]):
            continue

        chars = extract_korean_chars(filepath)
        if not chars:
            continue
        all_korean_chars.update(chars)
        trans_files_found.append(filename)

        # Determine frequency category
        if filename in FREQ_CATEGORY:
            cat = FREQ_CATEGORY[filename]
        elif filename.endswith("_STG.txt"):
            cat = "stg"
        else:
            continue  # Unknown file, skip frequency counting

        freq_dict = {"scps": scps_frequency, "beam": beam_frequency,
                     "other": other_non_stg_frequency, "stg": stg_frequency}[cat]
        with open(filepath, "r", encoding="utf-8") as f:
            for ch in f.read():
                if "\uAC00" <= ch <= "\uD7A3":
                    freq_dict[ch] = freq_dict.get(ch, 0) + 1

        print(f"  {filename}: {len(chars)} unique chars [{cat}]")

    if not all_korean_chars:
        print("ERROR: No Korean characters found in any translation files.")
        return 1

    # Extract characters used in packed item lists (highest priority for single-byte)
    packed_list_chars = set()
    for packed_file in ["SCPS_100_26.txt", "BEAM_DAT.txt"]:
        packed_path = os.path.join(trans_dir, packed_file)
        if os.path.exists(packed_path):
            with open(packed_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "[FF:1A" not in line and "[FF:19" not in line:
                        continue
                    m = re.match(r'\s*0x[0-9A-Fa-f]+\s+\[\s*\d+\]\s+(.+)', line)
                    if m:
                        text = re.sub(r'\[FF:[0-9A-Fa-f]+ [0-9A-Fa-f]+ [0-9A-Fa-f]+\]', '', m.group(1))
                        for ch in text:
                            if "\uAC00" <= ch <= "\uD7A3":
                                packed_list_chars.add(ch)

    korean_chars = sorted(all_korean_chars)
    non_stg_all = set(scps_frequency) | set(beam_frequency) | set(other_non_stg_frequency)
    print(f"  Total unique Korean characters: {len(korean_chars)}")
    print(f"  SCPS chars: {len(set(scps_frequency))} (top priority for single-byte)")
    print(f"  BEAM-only chars: {len(set(beam_frequency) - set(scps_frequency))} (second priority)")
    print(f"  STG-only chars: {len(set(c for c in all_korean_chars if c not in non_stg_all))}")
    if packed_list_chars:
        print(f"  Packed list chars: {len(packed_list_chars)} (highest priority)")

    print("Building character mapping...")
    korean_mapping = build_korean_mapping(
        korean_chars, decode_table,
        non_stg_frequency=other_non_stg_frequency, stg_frequency=stg_frequency,
        packed_list_chars=packed_list_chars,
        scps_frequency=scps_frequency, beam_frequency=beam_frequency
    )
    print(f"  Mapped {len(korean_mapping)} Korean characters to font slots")

    # Always copy fresh COMM.IMG (don't patch over previously patched file)
    print(f"Copying {comm_src} -> {comm_dst}")
    shutil.copy2(comm_src, comm_dst)

    # Patch COMM.IMG with Korean glyphs
    print()
    patch_comm_img(comm_dst, korean_mapping)

    # Patch stage file if specified
    if args.stage:
        stage = args.stage.upper()
        translation_path = os.path.join(BASE_DIR, "translated", "ko", f"{stage}_STG.txt")
        stg_src = os.path.join(GAME_DIR, f"{stage}.STG")
        stg_dst = os.path.join(OUTPUT_DIR, f"{stage}.STG")
        mapping_path = os.path.join(OUTPUT_DIR, f"{stage}_charmap.txt")

        print()
        print(f"Stage: {stage}")
        print(f"Translation: {translation_path}")

        if not os.path.exists(translation_path):
            print(f"ERROR: Translation file not found: {translation_path}")
            return 1

        # Always copy fresh STG file (don't patch over previously patched file)
        print(f"Copying {stg_src} -> {stg_dst}")
        shutil.copy2(stg_src, stg_dst)

        # Save mapping
        save_mapping(korean_mapping, mapping_path)

        # Parse translation file
        print()
        print("Parsing translation file...")
        entries = parse_translation_file(translation_path)
        print(f"  Found {len(entries)} translation entries")

        # Patch STG file
        print()
        patch_stg_file(stg_dst, entries, korean_mapping, decode_table, args.dry_run)

    # Patch SCPS_100.26 if --system specified
    if args.system:
        system_translation = os.path.join(BASE_DIR, "translated", "ko", "SCPS_100_26_system.txt")
        exe_src = os.path.join(GAME_DIR, "SCPS_100.26")
        exe_dst = os.path.join(OUTPUT_DIR, "SCPS_100.26")

        print()
        print(f"System messages: {system_translation}")

        if not os.path.exists(system_translation):
            print(f"ERROR: System translation file not found: {system_translation}")
            return 1

        # Always copy fresh EXE file (don't patch over previously patched file)
        print(f"Copying {exe_src} -> {exe_dst}")
        shutil.copy2(exe_src, exe_dst)

        # Parse system translation file
        print()
        print("Parsing system translation file...")
        sys_entries = parse_system_translation_file(system_translation)
        print(f"  Found {len(sys_entries)} system message entries")

        # Patch EXE file
        print()
        patch_exe_file(exe_dst, sys_entries, korean_mapping, decode_table, args.dry_run)

    print()
    print("=== Done ===")
    print(f"Output directory: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    exit(main())
