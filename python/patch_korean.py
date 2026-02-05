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


def build_korean_mapping(korean_chars, decode_table, priority_chars=None):
    """Build mapping from Korean characters to font charIDs.

    Strategy: Replace hiragana (1-80), katakana (81-160), then kanji (239+).
    Preserve Latin letters, digits, and common symbols.

    Args:
        korean_chars: List of Korean characters to map
        decode_table: The character decode table
        priority_chars: Optional set of characters to prioritize for single-byte slots
    """
    # Available slots (can be replaced with Korean):
    available_single = []  # charIDs 1-160 (single-byte)
    available_double = []  # charIDs 239+ (two-byte)

    # Hiragana slots (charIDs 1-80)
    for cid in range(1, 81):
        available_single.append(cid)

    # Katakana slots (charIDs 81-160)
    for cid in range(81, 161):
        available_single.append(cid)

    # Kanji slots (charIDs 239+, two-byte encoding)
    for cid in range(239, 1760):
        if cid not in PRESERVE_CHAR_IDS:
            available_double.append(cid)

    total_available = len(available_single) + len(available_double)
    if len(korean_chars) > total_available:
        raise ValueError(f"Not enough font slots: need {len(korean_chars)}, have {total_available}")

    # Build mapping: Korean char -> charID
    mapping = {}

    # If priority chars specified, assign them to single-byte slots first
    if priority_chars:
        priority_list = [ch for ch in korean_chars if ch in priority_chars]
        other_list = [ch for ch in korean_chars if ch not in priority_chars]
        ordered_chars = priority_list + other_list
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
            # Space - skip (charID 239 encodes to F0 00 which conflicts with null terminator)
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

        # Find the null terminator of the original string
        orig_end = offset + len(script_prefix)
        while orig_end < len(data) and data[orig_end] != 0x00:
            orig_end += 1

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
            # Too long - truncate encoded text to fit
            available = orig_total - len(script_prefix) - 1
            truncated_encoded = encoded[:available]
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

        # Find the null terminator of the original string
        orig_end = offset
        while orig_end < len(data) and data[orig_end] != 0x00:
            orig_end += 1

        if orig_end >= len(data):
            print(f"  ERROR: no null terminator found at 0x{offset:08X}")
            errors += 1
            continue

        # Original total size: text + null
        orig_total = orig_end - offset + 1

        # Encode Korean text
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
            # Too long - truncate encoded text to fit
            available = orig_total - 1
            truncated_encoded = encoded[:available]
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

    # Collect all translation files to extract Korean characters
    all_translation_paths = []

    if args.system:
        system_translation = os.path.join(BASE_DIR, "translated", "ko", "SCPS_100_26_system.txt")
        if os.path.exists(system_translation):
            all_translation_paths.append(system_translation)

    if args.stage:
        stage = args.stage.upper()
        stage_translation = os.path.join(BASE_DIR, "translated", "ko", f"{stage}_STG.txt")
        if os.path.exists(stage_translation):
            all_translation_paths.append(stage_translation)

    if not all_translation_paths:
        print("ERROR: No translation files found. Specify a stage name or --system.")
        return 1

    # Extract Korean characters from all translation files
    print("Extracting Korean characters from translations...")
    all_korean_chars = set()
    priority_chars = set()  # Characters from system messages get single-byte priority

    for trans_path in all_translation_paths:
        chars = extract_korean_chars(trans_path)
        all_korean_chars.update(chars)
        # System message characters get priority for single-byte encoding
        if "SCPS_100_26" in trans_path:
            priority_chars.update(chars)
        print(f"  {os.path.basename(trans_path)}: {len(chars)} unique chars")

    korean_chars = sorted(all_korean_chars)
    print(f"  Total unique Korean characters: {len(korean_chars)}")
    if priority_chars:
        print(f"  Priority (system) characters: {len(priority_chars)}")

    print("Building character mapping...")
    korean_mapping = build_korean_mapping(korean_chars, decode_table, priority_chars)
    print(f"  Mapped {len(korean_mapping)} Korean characters to font slots")

    # Copy COMM.IMG if not already done
    if not os.path.exists(comm_dst):
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

        # Copy STG file if not already done
        if not os.path.exists(stg_dst):
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

        # Copy EXE file if not already done
        if not os.path.exists(exe_dst):
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
