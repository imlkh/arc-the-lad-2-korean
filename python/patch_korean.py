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
BASE_DIR = os.path.join(SCRIPT_DIR, "..")
GAME_DIR = os.path.join(BASE_DIR, "..")
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
# Latin A-Z (charIDs 161-186), a-z (187-212), 0-9 (213-222)
# Symbols (223-238), special chars
PRESERVE_CHAR_IDS = set(range(161, 239))  # Latin, digits, basic symbols

# Also preserve these specific charIDs (UI elements, arrows, etc.)
PRESERVE_CHAR_IDS.update([
    # Element icons (223-226): kept in single-byte range via original encoding
    # Symbols: ー、…＋－／＊～"。！？
])


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
            clean = label.rstrip("?").strip()
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


def build_korean_mapping(korean_chars, decode_table):
    """Build mapping from Korean characters to font charIDs.

    Strategy: Replace hiragana (1-80), katakana (81-160), then kanji (239+).
    Preserve Latin letters, digits, and common symbols.
    """
    # CharIDs available for Korean (replace Japanese chars)
    # Hiragana: 1-80 (80 slots)
    # Katakana: 81-160 (80 slots) - but charID 81 is actually row 0 cell 20 bit0 = ア
    # Actually: cells 0-19 = hiragana (charIDs 1-80), cell 20 = first katakana
    # Let me recalculate based on the character table:
    # Row 0: hiragana あ-っ (charIDs 1-80)
    # Row 1: katakana オ-ッ + AB CD EF GH (charIDs 81-168 approximately)

    # Available slots (can be replaced with Korean):
    available = []

    # Hiragana slots (charIDs 1-80)
    for cid in range(1, 81):
        available.append(cid)

    # Katakana slots (charIDs 81-160)
    for cid in range(81, 161):
        available.append(cid)

    # Kanji slots (charIDs 239+, two-byte encoding)
    # These are cells 59+ (after symbols row)
    # We'll use as many as needed
    for cid in range(239, 1760):
        if cid not in PRESERVE_CHAR_IDS:
            available.append(cid)

    if len(korean_chars) > len(available):
        raise ValueError(f"Not enough font slots: need {len(korean_chars)}, have {len(available)}")

    # Build mapping: Korean char -> charID
    mapping = {}
    for i, kr_char in enumerate(korean_chars):
        mapping[kr_char] = available[i]

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


def patch_comm_img(comm_img_path, korean_mapping):
    """Patch COMM.IMG with Korean glyphs based on the mapping."""
    print(f"Patching COMM.IMG: {comm_img_path}")

    with open(comm_img_path, "rb") as f:
        data = bytearray(f.read())

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

    return entries


def encode_korean_text(text, korean_mapping, decode_table):
    """Encode Korean text to game byte format.

    Handles:
    - Korean characters via korean_mapping
    - Control codes: [delay:XX], [box:type], \n, etc.
    - Preserved characters (Latin, digits, symbols) via decode_table reverse lookup
    """
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
                elif tag == "box:narration":
                    result.extend(b"\xFF\x08\x05\x01")
                elif tag == "cursor":
                    result.extend(b"\xFF\x08\x07\x01")
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
            # Space - just skip (no space glyph in this font)
            " ": None,
        }
        if ch in punct_map:
            char_id = punct_map[ch]
            if char_id is not None:
                encoded = char_id_to_bytes(char_id)
                if encoded:
                    result.extend(encoded)
            i += 1
            continue

        # Skip unrecognized characters
        # print(f"  Warning: unrecognized char '{ch}' (U+{ord(ch):04X})")
        i += 1

    return bytes(result)


def find_template_after_dialogue(data, text_end_offset):
    """Find the 48-byte template block after a dialogue's null terminator.

    Template signature: starts with 23 01 F0 8B
    Returns template offset or None if not found.
    """
    # Search within 4 bytes after the null terminator
    search_start = text_end_offset + 1
    search_end = min(search_start + 4, len(data) - 4)

    for pos in range(search_start, search_end):
        if data[pos:pos+4] == b'\x23\x01\xF0\x8B':
            return pos
    return None


def patch_stg_file(stg_path, translation_entries, korean_mapping, decode_table, dry_run=False):
    """Patch STG file with Korean translations.

    Supports variable-length text replacement by:
    1. Processing dialogues chunk by chunk
    2. Tracking cumulative offset changes
    3. Updating script prefix values and template pointers
    """
    print(f"Patching STG file: {stg_path}")

    with open(stg_path, "rb") as f:
        data = bytearray(f.read())

    # Group entries by chunk
    entries_by_chunk = {}
    for entry in translation_entries:
        chunk_idx = entry["offset"] // CHUNK_SIZE
        if chunk_idx not in entries_by_chunk:
            entries_by_chunk[chunk_idx] = []
        entries_by_chunk[chunk_idx].append(entry)

    patched = 0
    extended = 0
    errors = 0

    for chunk_idx in sorted(entries_by_chunk.keys()):
        chunk_entries = sorted(entries_by_chunk[chunk_idx], key=lambda e: e["offset"])
        chunk_base = chunk_idx * CHUNK_SIZE
        chunk_end = chunk_base + CHUNK_SIZE

        # Track cumulative delta for this chunk
        cumulative_delta = 0

        for entry in chunk_entries:
            orig_offset = entry["offset"]
            script_prefix = entry["script_prefix"]
            korean_text = entry["text"]

            # Adjust offset by cumulative delta
            offset = orig_offset + cumulative_delta

            if offset >= len(data) or offset < chunk_base:
                print(f"  ERROR: offset 0x{orig_offset:08X} out of bounds")
                errors += 1
                continue

            # Find the null terminator of the original string
            text_start = offset + len(script_prefix)
            text_end = text_start
            while text_end < len(data) and data[text_end] != 0x00:
                text_end += 1

            if text_end >= len(data):
                print(f"  ERROR: no null terminator at 0x{orig_offset:08X}")
                errors += 1
                continue

            # Original total size: script_prefix + text + null
            orig_total = text_end - offset + 1

            # Encode Korean text
            encoded = encode_korean_text(korean_text, korean_mapping, decode_table)

            # New total size: script_prefix + encoded + null
            new_total = len(script_prefix) + len(encoded) + 1
            delta = new_total - orig_total

            if delta > 0:
                # Text is longer - need to shift subsequent bytes
                # Check if we have room in the chunk
                event_script_end = chunk_base + 0xBC7FF
                current_end = chunk_end

                # Find actual end of event script data (last non-zero before chunk end)
                for i in range(chunk_end - 1, chunk_base + EVENT_SCRIPT_OFFSET, -1):
                    if data[i] != 0x00:
                        current_end = i + 1
                        break

                # Check if extension would overflow
                if current_end + delta > chunk_end:
                    # Would overflow - fall back to truncation
                    available = orig_total - len(script_prefix) - 1
                    encoded = encoded[:available]
                    new_total = len(script_prefix) + len(encoded) + 1
                    delta = 0

            # Build replacement
            replacement = script_prefix + encoded + b"\x00"

            if delta != 0:
                # Variable length replacement - shift bytes within chunk
                shift_start = offset + orig_total
                shift_end = chunk_end + cumulative_delta

                if delta > 0:
                    # Extending: shift bytes toward end of chunk
                    # Move from end to start to avoid overwriting
                    for i in range(shift_end - 1, shift_start - 1, -1):
                        if i + delta < len(data):
                            data[i + delta] = data[i]
                    # Clear the gap
                    for i in range(shift_start, shift_start + delta):
                        if i < len(data):
                            data[i] = 0x00
                    extended += 1
                else:
                    # Shortening: shift bytes toward start of chunk
                    abs_delta = -delta
                    for i in range(shift_start, shift_end):
                        if i - abs_delta >= 0 and i < len(data):
                            data[i - abs_delta] = data[i]
                    # Clear the end
                    for i in range(shift_end - abs_delta, shift_end):
                        if i < len(data):
                            data[i] = 0x00

                # Update script prefix values in subsequent templates
                update_start = offset + new_total
                update_end = chunk_end + cumulative_delta + delta

                # Find and update template pointers
                pos = update_start
                while pos < min(update_end, len(data) - 48):
                    # Look for template signature
                    if data[pos:pos+4] == b'\x23\x01\xF0\x8B':
                        # Found a template - update pointer fields
                        # Ptr_A at +14, Ptr_B at +30
                        for ptr_offset in [14, 30]:
                            if pos + ptr_offset + 2 <= len(data):
                                old_val = struct.unpack('<H', data[pos+ptr_offset:pos+ptr_offset+2])[0]
                                new_val = old_val + delta
                                if new_val > 0:  # Sanity check
                                    data[pos+ptr_offset:pos+ptr_offset+2] = struct.pack('<H', new_val)
                        pos += 48
                    else:
                        pos += 1

                cumulative_delta += delta

            # Write the replacement text
            if not dry_run:
                data[offset:offset + new_total] = replacement
                if new_total < orig_total and delta == 0:
                    # Pad with nulls if shorter and not shifting
                    data[offset + new_total:offset + orig_total] = b"\x00" * (orig_total - new_total)

            patched += 1

    if not dry_run:
        with open(stg_path, "wb") as f:
            f.write(data)

    print(f"  Patched: {patched} dialogues")
    if extended:
        print(f"  Extended (variable length): {extended}")
    if errors:
        print(f"  Errors: {errors}")

    return patched, extended, errors


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


def main():
    parser = argparse.ArgumentParser(description="Patch Arc the Lad 2 with Korean translation")
    parser.add_argument("stage", help="Stage name (e.g., S100)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    args = parser.parse_args()

    stage = args.stage.upper()

    # File paths
    translation_path = os.path.join(BASE_DIR, "translated", "ko", f"{stage}_STG.txt")
    stg_src = os.path.join(GAME_DIR, f"{stage}.STG")
    stg_dst = os.path.join(OUTPUT_DIR, f"{stage}.STG")
    comm_src = os.path.join(GAME_DIR, "COMM.IMG")
    comm_dst = os.path.join(OUTPUT_DIR, "COMM.IMG")
    mapping_path = os.path.join(OUTPUT_DIR, f"{stage}_charmap.txt")

    print(f"=== Arc the Lad 2 Korean Patcher ===")
    print(f"Stage: {stage}")
    print(f"Translation: {translation_path}")
    print()

    # Check files exist
    if not os.path.exists(translation_path):
        print(f"ERROR: Translation file not found: {translation_path}")
        return 1

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Copy source files if not already done
    if not os.path.exists(stg_dst):
        print(f"Copying {stg_src} -> {stg_dst}")
        shutil.copy2(stg_src, stg_dst)

    if not os.path.exists(comm_dst):
        print(f"Copying {comm_src} -> {comm_dst}")
        shutil.copy2(comm_src, comm_dst)

    # Load character table
    print("Loading character table...")
    decode_table = load_decode_table()
    print(f"  Loaded {len(decode_table)} characters")

    # Extract Korean characters and build mapping
    print("Extracting Korean characters from translation...")
    korean_chars = extract_korean_chars(translation_path)
    print(f"  Found {len(korean_chars)} unique Korean characters")

    print("Building character mapping...")
    korean_mapping = build_korean_mapping(korean_chars, decode_table)
    print(f"  Mapped {len(korean_mapping)} Korean characters to font slots")

    # Save mapping
    save_mapping(korean_mapping, mapping_path)

    # Patch COMM.IMG with Korean glyphs
    print()
    patch_comm_img(comm_dst, korean_mapping)

    # Parse translation file
    print()
    print("Parsing translation file...")
    entries = parse_translation_file(translation_path)
    print(f"  Found {len(entries)} translation entries")

    # Patch STG file
    print()
    patch_stg_file(stg_dst, entries, korean_mapping, decode_table, args.dry_run)

    print()
    print("=== Done ===")
    print(f"Output files:")
    print(f"  Font:  {comm_dst}")
    print(f"  Stage: {stg_dst}")
    print(f"  Map:   {mapping_path}")

    return 0


if __name__ == "__main__":
    exit(main())
