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

    The (Blank) character at cell 59, bit2 (charID 239) is treated as a space.
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
            char_id = 1 + (row * 21 + col) * 4 + bitplane
            # Strip charID suffix like " (123)" from new format
            label_clean = re.sub(r'\s*\(\d+\)\s*$', '', label).strip()
            # Treat (Blank) as space character (cell 59, bit2 = charID 239)
            if label_clean.lower() in ("(blank)", "blank"):
                table[char_id] = " "  # Map blank to space
                continue
            if not label_clean:
                continue
            # Strip trailing ? from uncertain characters
            clean = label_clean.rstrip("?").strip()
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
                parts.append("[br]")
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

TEMPLATE_SIG_23 = b'\x23\x01\xF0\x8B'  # Primary signature
TEMPLATE_SIG_45 = b'\x45\x01\xF0\x8B'  # Secondary signature (always at +16)
TEMPLATE_SIZE = 48
SCRIPT_OPCODE_28 = b'\x28\x01'
SCRIPT_BLOCK_SIZE = 10
STG_CHUNK_SIZE = 0xBC800  # 772,096 bytes per chunk
STG_TEXT_REGION_OFFSET = 0xB4000  # Text region starts at +0xB4000 within each chunk
STG_TEXT_REGION_SIZE = 0x8800  # ~34,816 bytes text region per chunk
STG_EVENT_SCRIPT_OFFSET = 0xB0000  # Event script region starts at +0xB0000 within each chunk
STG_EVENT_SCRIPT_SIZE = 0x4000  # 16,384 bytes event script region per chunk
STG_PADDING_OFFSET = 0xA0000  # Padding region starts at +0xA0000 within each chunk
STG_PADDING_SIZE = 0x10000  # 65,536 bytes padding region per chunk (0xA0000-0xB0000)

# Valid speaker opcodes found in templates
VALID_SPEAKER_OPCODES = {
    0x8005,  # Player
    0x8006,  # NPC
    0x8009,  # Party member
    0x800A,  # Shopkeeper
    0x800D,  # Named NPC
    0x800E,  # Quest NPC
    0x8016,  # Narrator
    0x8018,  # Tutorial
    0xFFFE,  # System (most common ~74%)
    0x0006,  # Alternate NPC code
}


def _is_garbage_text(text):
    """Rule-based filter to detect garbage text (binary data misinterpreted).

    Returns True if the text is garbage, False if it looks valid.

    Rules:
    1. Has unknown charID [?XXXX] - charID > 1764 means beyond font table (441 cells × 4)
    2. Has invalid FF control code - valid opcodes are 01,03,04,05,06,07,08,09,0A,0B,0D
    3. Has lowercase ASCII embedded in Japanese - game text uses uppercase only (HP, MP, BGM)
    4. Very short text (<=6 chars) with uppercase ASCII mixed in - likely binary garbage
    """
    # Rule 1: Unknown charID markers indicate binary data beyond font table
    # Font has 441 cells × 4 bitplanes = 1764 max charID
    # Any [?XXXX] means the two-byte sequence produced an invalid charID > 1764
    if re.search(r'\[\?\d+\]', text):
        return True

    # Rule 2: Invalid FF control codes
    # Valid FF opcodes found in game text:
    #   01 (highlight), 03 (delay), 04 (menu marker), 05 (newline),
    #   06 (button icon), 07 (number), 08 (box), 09 (emphasis),
    #   0A (currency format), 0B (item), 0D (name), 0F (unknown effect)
    # Anything else like [FF:B2 0F 2F] is binary garbage misinterpreted as control code
    VALID_FF_OPCODES = (0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0D, 0x0F)
    for match in re.finditer(r'\[FF:([0-9A-Fa-f]{2}) [0-9A-Fa-f]{2} [0-9A-Fa-f]{2}\]', text):
        opcode = int(match.group(1), 16)
        if opcode not in VALID_FF_OPCODES:
            return True

    # Strip tags to analyze actual text content
    stripped = text
    for tag in ("[box:system]", "[box:close]", "[box:speech]",
                "[box:narration]", "[cursor]", "[br]", "[opt]"):
        stripped = stripped.replace(tag, "")
    stripped = re.sub(r"\[script:.*?\]", "", stripped)
    stripped = re.sub(r"\[.*?\]", "", stripped)

    # Rule 3: Lowercase ASCII letters embedded in Japanese text
    # Real game text uses uppercase only (HP, MP, BGM, R1, C級, etc.)
    # Lowercase mixed with Japanese indicates binary garbage
    for i, ch in enumerate(stripped):
        if ch.islower() and ch.isascii():
            # Check if surrounded by Japanese characters
            before = stripped[max(0, i-2):i]
            after = stripped[i+1:i+3]
            jp_before = any('ぁ' <= c <= 'ん' or 'ァ' <= c <= 'ン' or '\u4e00' <= c <= '\u9fff' for c in before)
            jp_after = any('ぁ' <= c <= 'ん' or 'ァ' <= c <= 'ン' or '\u4e00' <= c <= '\u9fff' for c in after)
            if jp_before or jp_after:
                return True

    # Rule 4: Uppercase ASCII mixed with kana = garbage
    # e.g., "ぴデいギB", "デあギJ", "BじI", "ゾァびJダIゥゾ"
    # But "HP回復", "BGMセレクト" are valid (kanji or consecutive uppercase tokens)
    if len(stripped) <= 6:
        has_upper = any(c.isupper() and c.isascii() for c in stripped)
        has_kana = any('ぁ' <= c <= 'ん' or 'ァ' <= c <= 'ン' for c in stripped)
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in stripped)
        # Short text with uppercase + kana but no kanji = garbage
        # Valid short terms like "HP回復" have kanji
        if has_upper and has_kana and not has_kanji:
            return True
    elif len(stripped) <= 12:
        # For medium text, catch isolated uppercase letters mixed with kana
        # "ゾァびJダIゥゾ" has J,I isolated between kana = garbage
        # "BGMセレクト" has B,G,M consecutive = valid game term
        has_upper = any(c.isupper() and c.isascii() for c in stripped)
        has_kana = any('ぁ' <= c <= 'ん' or 'ァ' <= c <= 'ン' for c in stripped)
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in stripped)
        if has_upper and has_kana and not has_kanji:
            isolated_upper = 0
            for i, c in enumerate(stripped):
                if c.isupper() and c.isascii():
                    prev_upper = (i > 0 and stripped[i-1].isupper()
                                  and stripped[i-1].isascii())
                    next_upper = (i < len(stripped) - 1
                                  and stripped[i+1].isupper()
                                  and stripped[i+1].isascii())
                    if not prev_upper and not next_upper:
                        isolated_upper += 1
            if isolated_upper >= 2:
                return True

    # Rule 5: Short mixed hiragana/katakana without repetition = garbage
    # e.g., "みギづ", "げいう" from binary data
    # But "ふふふ", "ねぇねぇ" are valid (have repetition)
    # Also allow "エルクか", "シュウと" - character name (3+ katakana) + particle
    if len(stripped) <= 4:
        has_hira = any('ぁ' <= c <= 'ん' for c in stripped)
        has_kata = any('ァ' <= c <= 'ン' for c in stripped)
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in stripped)
        has_punct = any(c in '、。？！…ー' for c in stripped)

        # Skip if has kanji or punctuation (likely valid)
        if not has_kanji and not has_punct:
            # Allow if it's a character name pattern: 3+ katakana followed by hiragana particle
            # e.g., "エルクか" (Is it Elc?), "シュウと" (with Shu), "ゴメスと" (with Gomes)
            # Count consecutive katakana at the start
            kata_prefix_len = 0
            for c in stripped:
                if 'ァ' <= c <= 'ン' or c == 'ー':  # Include prolonged sound mark
                    kata_prefix_len += 1
                else:
                    break

            # 3+ katakana prefix + hiragana ending = likely character name
            if kata_prefix_len >= 3 and len(stripped) > kata_prefix_len:
                suffix = stripped[kata_prefix_len:]
                if all('ぁ' <= c <= 'ん' for c in suffix):
                    return False  # Likely valid: name + particle

            # Check for repetition (common in valid onomatopoeia)
            has_repetition = False
            for i in range(1, len(stripped)):
                if stripped[i] == stripped[i-1]:
                    has_repetition = True
                    break

            # Mixed hira+kata without repetition = garbage
            if has_hira and has_kata and not has_repetition:
                return True

    # Rule 6: Repeating 2-character pair at regular intervals = opcode data
    # Script opcodes (e.g., 23 01 XX 8C = store) repeat at fixed intervals,
    # producing the same character pair (e.g., "もあ") at positions 0, 6, 12.
    # Real Japanese text never has a distinct pair repeating 3+ times at
    # regular intervals of 4+ characters.
    if 8 <= len(stripped) <= 30:
        for i in range(min(8, len(stripped) - 1)):
            pair = stripped[i:i+2]
            if pair[0] == pair[1]:
                continue
            positions = [j for j in range(len(stripped) - 1)
                         if stripped[j:j+2] == pair]
            if len(positions) >= 3:
                intervals = [positions[k+1] - positions[k]
                             for k in range(len(positions) - 1)]
                if len(set(intervals)) == 1 and intervals[0] >= 4:
                    return True

    # Rule 7: MIPS opcode garbage — multiple distinct "Xあ/Xデ/Xギ" bigrams
    # VM opcodes produce three characteristic patterns when decoded as text:
    #   XX 01 → "Xあ" (STORE, CALL, SET, COMPARE opcodes)
    #   XX 8C → "Xデ" (memory reference operands)
    #   XX 80 → "Xギ" (register operands)
    # If 2+ different characters precede any of these markers, it's opcodes.
    # Texts with kanji or punctuation are excluded (always valid).
    if 3 <= len(stripped) <= 30:
        has_kanji_r7 = any('\u4e00' <= c <= '\u9fff' for c in stripped)
        has_punct_r7 = any(c in '！？…。、' for c in stripped)
        if not has_kanji_r7 and not has_punct_r7:
            for marker in ('あぁ', 'デ', 'ギ'):
                predecessors = set()
                for i in range(1, len(stripped)):
                    if stripped[i] in marker and stripped[i-1] not in marker:
                        predecessors.add(stripped[i-1])
                if len(predecessors) >= 2:
                    return True

    return False


def _find_templates(data):
    """Find all 48-byte event script template blocks in STG data.

    Template structure (48 bytes):
      Bytes 0-15:  Primary block (0x23 signature)
        [0:4]   Signature: 0x8BF00123
        [4:6]   Speaker opcode
        [6:8]   Ptr_A: Text region pointer
        [8:10]  Ptr_B: Text data region pointer
        [10:12] Ptr_C: Flags (0x0004 for primary)
        [12:14] Unknown (usually 0x8000)
        [14:16] Line index (used for dialogue prefix lookup)

      Bytes 16-31: Secondary block (0x45 signature, always paired)
        Same structure, Ptr_C = 0x0000

      Bytes 32-39: Box control
        [32:34] 0x0063 (box command)
        [34:36] Speaker opcode (mirrors main)
        [36:38] Timing offset
        [38:40] 0x002D (box type)

      Bytes 40-47: Display parameters
        [40:42] Box height (0x0030 = 48 pixels)
        [42:44] Box Y position (0x0062 = 98 pixels)
        [44:46] Dialog flags (0x8002)
        [46:48] Animation ID (variable)

    Returns list of (offset, context_opcode, ptr_a, ptr_b, ptr_c) tuples.
    Note: ptr_a here is the line index at bytes 14:16, used for dialogue lookup.
    """
    templates = []
    pos = 0
    while True:
        idx = data.find(TEMPLATE_SIG_23, pos)
        if idx == -1:
            break
        if idx + TEMPLATE_SIZE <= len(data):
            # Validate: check for paired 0x45 signature at +16
            if data[idx + 16:idx + 20] != TEMPLATE_SIG_45:
                pos = idx + 1
                continue

            # Extract speaker opcode
            opcode = int.from_bytes(data[idx + 4:idx + 6], 'little')

            # Extract line index (used for dialogue prefix lookup)
            # Note: This is at bytes 14:16, not the ptr_a at 6:8
            ptr_a = int.from_bytes(data[idx + 14:idx + 16], 'little')
            ptr_b = int.from_bytes(data[idx + 30:idx + 32], 'little')
            ptr_c = int.from_bytes(data[idx + 36:idx + 38], 'little')

            # Template validated by paired signature check above
            templates.append((idx, opcode, ptr_a, ptr_b, ptr_c))

        pos = idx + 1
    return templates


def _get_chunk_text_regions(file_size):
    """Calculate text region boundaries for each chunk in an STG file.

    Returns list of (text_start, text_end, chunk_index) tuples.
    """
    regions = []
    num_chunks = file_size // STG_CHUNK_SIZE
    for i in range(num_chunks):
        chunk_start = i * STG_CHUNK_SIZE
        text_start = chunk_start + STG_TEXT_REGION_OFFSET
        text_end = min(chunk_start + STG_CHUNK_SIZE, file_size)
        if text_start < file_size:
            regions.append((text_start, text_end, i))
    return regions


def _get_chunk_event_script_regions(file_size):
    """Calculate event script region boundaries for each chunk in an STG file.

    The event script region (0xB0000-0xB4000) can contain embedded dialogue text
    that is not covered by the main text region scanning.

    Returns list of (event_start, event_end, chunk_index) tuples.
    """
    regions = []
    num_chunks = file_size // STG_CHUNK_SIZE
    for i in range(num_chunks):
        chunk_start = i * STG_CHUNK_SIZE
        event_start = chunk_start + STG_EVENT_SCRIPT_OFFSET
        event_end = chunk_start + STG_EVENT_SCRIPT_OFFSET + STG_EVENT_SCRIPT_SIZE
        if event_end <= file_size:
            regions.append((event_start, event_end, i))
    return regions


def _get_chunk_padding_regions(file_size):
    """Calculate padding region boundaries for each chunk in an STG file.

    The padding region (0xA0000-0xB0000) can contain embedded dialogue text
    in some chunks (e.g., Chunk 4 in S100.STG).

    Returns list of (padding_start, padding_end, chunk_index) tuples.
    """
    regions = []
    num_chunks = file_size // STG_CHUNK_SIZE
    for i in range(num_chunks):
        chunk_start = i * STG_CHUNK_SIZE
        padding_start = chunk_start + STG_PADDING_OFFSET
        padding_end = chunk_start + STG_PADDING_OFFSET + STG_PADDING_SIZE
        if padding_end <= file_size:
            regions.append((padding_start, padding_end, i))
    return regions


def _scan_text_region_for_dialogues(data, region_start, region_end,
                                    templates_in_region, decode_table,
                                    use_heuristics=True):
    """Scan a chunk's text region for dialogues, handling gaps before first template.

    This handles cases where dialogues appear before the first template in a chunk,
    which can be missed when only doing template-to-template gap scanning.

    Args:
        data: Binary file data
        region_start: Start offset of text region
        region_end: End offset of text region
        templates_in_region: List of templates within this region
        decode_table: Character decode table
        use_heuristics: Whether to use heuristic scanning for gaps

    Returns list of (offset, consumed, text, context_opcode) tuples.
    """
    dialogues = []

    if not templates_in_region:
        # No templates in region - scan the entire text region heuristically
        if use_heuristics:
            scan_pos = region_start
            script_ranges = _find_script_ranges(data, region_start, region_end)
            while scan_pos < region_end - 3:
                if data[scan_pos] == 0x00:
                    candidate = scan_pos + 1
                    if candidate + 2 < region_end:
                        text, consumed = decode_string(data, candidate,
                                                       decode_table, prefix=2)
                        stripped = text
                        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
                            stripped = stripped.replace(tag, "")
                        stripped = re.sub(r"\[script:.*?\]", "", stripped)
                        stripped = re.sub(r"\[.*?\]", "", stripped)
                        text_start = candidate + 2
                        text_end = candidate + consumed
                        if (len(stripped) >= MIN_TEXT_RUN
                                and not _overlaps_script(text_start, text_end,
                                                         script_ranges)
                                and not _is_garbage_text(text)):
                            # Use 0x0000 as unknown context opcode
                            dialogues.append((candidate, consumed, text, 0x0000))
                            scan_pos = candidate + consumed
                            continue
                scan_pos += 1
        return dialogues

    # Sort templates by offset
    sorted_templates = sorted(templates_in_region, key=lambda t: t[0])
    first_template = sorted_templates[0]

    # Check if there's a gap between text region start and first template
    if first_template[0] > region_start:
        gap_start = region_start
        gap_end = first_template[0]

        # Compute expected prefix from first template's ptr_a
        expected_val = first_template[2] - 0x10  # ptr_a - 0x10
        if expected_val >= 0:
            expected_bytes = expected_val.to_bytes(2, 'little')

            result = _find_dialogue_in_gap(data, gap_start, gap_end,
                                           expected_bytes, decode_table,
                                           use_heuristics=use_heuristics)
            if result is not None:
                offset, prefix_val, text, consumed = result
                dialogues.append((offset, consumed, text, first_template[1]))

    return dialogues


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
                          decode_table, use_heuristics=False):
    """Search for a dialogue string in the gap between two templates.

    Uses pointer-based extraction: the expected_prefix_bytes are computed
    from the next template's Ptr_A field (Ptr_A - 0x10), which deterministically
    locates where the dialogue's 2-byte script prefix should be.

    When use_heuristics=False (default), only pointer-validated dialogues are
    returned, eliminating false positives from binary data.

    Returns list of (dialogue_offset, script_prefix_value, text, bytes_consumed).
    Empty list if no dialogue found.
    """
    # Trim trailing script opcode blocks (scan backward in 10-byte steps).
    while (gap_end - gap_start >= SCRIPT_BLOCK_SIZE
           and _is_script_opcode_28(data, gap_end - SCRIPT_BLOCK_SIZE)):
        gap_end -= SCRIPT_BLOCK_SIZE

    gap_size = gap_end - gap_start

    # Bare gap: only prefix bytes or nothing, no actual dialogue
    if gap_size <= 2:
        return []

    # Build exclusion zones for any remaining 28 01 script opcode blocks
    # that sit in the middle of the gap (context-transition script data
    # that precedes real dialogue strings).
    script_ranges = _find_script_ranges(data, gap_start, gap_end)

    results = []
    found_offsets_in_gap = set()

    # Primary: search for the expected 2-byte prefix in the gap
    # This is the deterministic pointer-based approach
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
                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
            stripped = stripped.replace(tag, "")
        stripped = re.sub(r"\[script:.*?\]", "", stripped)
        stripped = re.sub(r"\[.*?\]", "", stripped)
        # Reject if text bytes overlap with a preamble block
        text_start = abs_offset + 2  # after 2-byte script prefix
        text_end = abs_offset + consumed

        # Validate dialogue boundaries:
        # 1. Must have actual text content
        # 2. Must not overlap with script opcode blocks
        # 3. Must end within the gap (text_end <= gap_end)
        if (len(stripped) >= 1
                and not _overlaps_script(text_start, text_end, script_ranges)
                and text_end <= gap_end + TEMPLATE_SIZE):  # Allow ending at next template
            # Skip garbage filter for pointer-validated dialogues
            # The pointer validation itself ensures this is a real dialogue
            prefix_val = int.from_bytes(expected_prefix_bytes, 'little')
            results.append((abs_offset, prefix_val, text, consumed))
            found_offsets_in_gap.add(abs_offset)
            break
        # Try the next occurrence of the prefix in the gap
        search_from = prefix_pos + 1

    # Secondary: try alternative prefix values
    # 1. ptr_a - 0x1A (one SCRIPT_BLOCK_SIZE further back than standard 0x10)
    #    Covers ~33 entries where the dialogue prefix is 10 less than expected
    # 2. Try decoding from gap_start directly regardless of prefix value
    #    Covers ~242 entries with fixed 03 01 prefix (unindexed dialogues)
    alt_expected_val = int.from_bytes(expected_prefix_bytes, 'little') - SCRIPT_BLOCK_SIZE
    if not results and alt_expected_val >= 0:
        alt_bytes = alt_expected_val.to_bytes(2, 'little')
        if alt_bytes != expected_prefix_bytes:
            search_from = 0
            while search_from < len(gap_data):
                prefix_pos = gap_data.find(alt_bytes, search_from)
                if prefix_pos == -1:
                    break
                abs_offset = gap_start + prefix_pos
                text, consumed = decode_string(data, abs_offset, decode_table, prefix=2)
                stripped = text
                for tag in ("[box:system]", "[box:close]", "[box:speech]",
                            "[box:narration]", "[cursor]", "[br]", "[opt]"):
                    stripped = stripped.replace(tag, "")
                stripped = re.sub(r"\[script:.*?\]", "", stripped)
                stripped = re.sub(r"\[.*?\]", "", stripped)
                text_start = abs_offset + 2
                text_end = abs_offset + consumed
                if (len(stripped) >= 1
                        and not _overlaps_script(text_start, text_end, script_ranges)
                        and text_end <= gap_end + TEMPLATE_SIZE):
                    prefix_val = int.from_bytes(alt_bytes, 'little')
                    results.append((abs_offset, prefix_val, text, consumed))
                    found_offsets_in_gap.add(abs_offset)
                    break
                search_from = prefix_pos + 1

    # Try decoding from gap_start directly (handles fixed-prefix dialogues
    # like 03 01 where the prefix doesn't match any expected value)
    if not results and gap_end - gap_start >= 4:
        text, consumed = decode_string(data, gap_start, decode_table, prefix=2)
        if text:
            stripped = text
            for tag in ("[box:system]", "[box:close]", "[box:speech]",
                        "[box:narration]", "[cursor]", "[br]", "[opt]"):
                stripped = stripped.replace(tag, "")
            stripped = re.sub(r"\[script:.*?\]", "", stripped)
            stripped = re.sub(r"\[.*?\]", "", stripped)
            text_start = gap_start + 2
            text_end = gap_start + consumed
            if (len(stripped) >= 1
                    and not _overlaps_script(text_start, text_end, script_ranges)
                    and text_end <= gap_end + TEMPLATE_SIZE
                    and not _is_garbage_text(text)):
                prefix_val = int.from_bytes(data[gap_start:gap_start + 2], 'little')
                results.append((gap_start, prefix_val, text, consumed))
                found_offsets_in_gap.add(gap_start)

    # Continuation: try to decode sequential dialogues after the last found one
    # Some gaps contain multiple null-terminated dialogues in sequence
    if results and use_heuristics:
        continuation_pos = max(r[0] + r[3] for r in results)
        while continuation_pos + 4 < gap_end:
            text, consumed = decode_string(data, continuation_pos, decode_table,
                                           prefix=2)
            if not text or consumed <= 3:
                break
            stripped = text
            for tag in ("[box:system]", "[box:close]", "[box:speech]",
                        "[box:narration]", "[cursor]", "[br]", "[opt]"):
                stripped = stripped.replace(tag, "")
            stripped = re.sub(r"\[script:.*?\]", "", stripped)
            stripped = re.sub(r"\[.*?\]", "", stripped)
            text_start = continuation_pos + 2
            text_end = continuation_pos + consumed
            has_kanji = any('\u4e00' <= c <= '\u9fff' for c in stripped)
            if (len(stripped) >= 5 and has_kanji
                    and not _overlaps_script(text_start, text_end, script_ranges)
                    and not _is_garbage_text(text)):
                prefix_val = int.from_bytes(
                    data[continuation_pos:continuation_pos + 2], 'little')
                results.append((continuation_pos, prefix_val, text, consumed))
                found_offsets_in_gap.add(continuation_pos)
                continuation_pos += consumed
            else:
                break

    # Fallback: scan for null-terminated strings (only when nothing found)
    if not results and use_heuristics:
        scan_pos = gap_start
        while scan_pos < gap_end - 3:
            if data[scan_pos] == 0x00:
                candidate = scan_pos + 1
                if candidate + 2 < gap_end:
                    text, consumed = decode_string(data, candidate, decode_table,
                                                   prefix=2)
                    stripped = text
                    for tag in ("[box:system]", "[box:close]", "[box:speech]",
                                "[box:narration]", "[cursor]", "[br]", "[opt]"):
                        stripped = stripped.replace(tag, "")
                    stripped = re.sub(r"\[script:.*?\]", "", stripped)
                    stripped = re.sub(r"\[.*?\]", "", stripped)
                    text_start = candidate + 2
                    text_end = candidate + consumed
                    if (len(stripped) >= MIN_TEXT_RUN
                            and not _overlaps_script(text_start, text_end,
                                                       script_ranges)
                            and not _is_garbage_text(text)):
                        prefix_val = int.from_bytes(data[candidate:candidate + 2],
                                                    'little')
                        results.append((candidate, prefix_val, text, consumed))
                        found_offsets_in_gap.add(candidate)
                        scan_pos = candidate + consumed
                        continue
            scan_pos += 1

    return results


def scan_stg(data, decode_table, use_heuristics=True, filter_garbage=True):
    """Template-driven dialogue extraction for STG files.

    Uses pointer-based extraction where dialogue locations are determined
    by template Ptr_A fields (Ptr_A - 0x10 = dialogue prefix offset).

    For multi-chunk STG files, this function also scans each chunk's text
    region independently to catch dialogues that appear before the first
    template in a chunk (which can be missed in template-to-template scanning
    when gaps cross chunk boundaries).

    Args:
        data: Binary STG file data
        decode_table: Character ID to character mapping
        use_heuristics: If True (default), also use heuristic fallback scanning
                       to find dialogues in gaps where pointer-based method fails.
                       If False, use only pointer-validated dialogues.
        filter_garbage: If True (default), filter out garbage text from results.

    Returns (dialogues, templates, stats) where:
      dialogues = [(offset, consumed, text, context_opcode), ...]
      templates = [(offset, opcode, ptr_a, ptr_b, ptr_c), ...]
      stats = {'total_templates': N, 'found': N, 'missed': N, 'bare': N,
               'garbage_filtered': N, 'chunk_boundary_found': N}
    """
    templates = _find_templates(data)
    dialogues = []
    stats = {'total_templates': len(templates), 'found': 0, 'missed': 0,
             'bare': 0, 'garbage_filtered': 0, 'chunk_boundary_found': 0}

    if not templates:
        return dialogues, templates, stats

    # Build a set of dialogue offsets to avoid duplicates
    found_offsets = set()

    # --- Chunk-based scanning for dialogues before first template in each chunk ---
    # This handles cases where large template gaps cross chunk boundaries
    chunk_regions = _get_chunk_text_regions(len(data))

    for region_start, region_end, chunk_idx in chunk_regions:
        # Find templates within this chunk's text region
        templates_in_region = [t for t in templates
                               if region_start <= t[0] < region_end]

        if not templates_in_region:
            continue

        # Sort by offset
        sorted_templates = sorted(templates_in_region, key=lambda t: t[0])
        first_in_chunk = sorted_templates[0]

        # Check if first template in this chunk is not the global first template
        # and has a gap from the text region start
        if first_in_chunk[0] > region_start:
            gap_start = region_start
            gap_end = first_in_chunk[0]

            # Compute expected prefix from first template's ptr_a
            expected_val = first_in_chunk[2] - 0x10  # ptr_a - 0x10
            if expected_val >= 0:
                expected_bytes = expected_val.to_bytes(2, 'little')

                gap_results = _find_dialogue_in_gap(data, gap_start, gap_end,
                                                    expected_bytes, decode_table,
                                                    use_heuristics=use_heuristics)
                for offset, prefix_val, text, consumed in gap_results:
                    if offset not in found_offsets:
                        dialogues.append((offset, consumed, text, first_in_chunk[1]))
                        found_offsets.add(offset)
                        stats['chunk_boundary_found'] += 1

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
        if abs_offset not in found_offsets:
            text, consumed = decode_string(data, abs_offset, decode_table, prefix=2)
            stripped = text
            for tag in ("[box:system]", "[box:close]", "[box:speech]",
                        "[box:narration]", "[cursor]", "[br]", "[opt]"):
                stripped = stripped.replace(tag, "")
            stripped = re.sub(r"\[script:.*?\]", "", stripped)
            stripped = re.sub(r"\[.*?\]", "", stripped)
            if len(stripped) >= 1:
                dialogues.append((abs_offset, consumed, text, first_tmpl[1]))
                found_offsets.add(abs_offset)
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

        gap_results = _find_dialogue_in_gap(data, gap_start, gap_end,
                                             expected_bytes, decode_table,
                                             use_heuristics=use_heuristics)
        if gap_results:
            for offset, prefix_val, text, consumed in gap_results:
                if offset not in found_offsets:
                    dialogues.append((offset, consumed, text, tmpl_cur[1]))
                    found_offsets.add(offset)
                    stats['found'] += 1
        elif gap_end - gap_start <= 2:
            stats['bare'] += 1
        else:
            stats['missed'] += 1

    # --- Scan for orphan menu texts (A9 00 texts with [opt] not captured by templates) ---
    # These are standalone menu options that don't have associated templates
    # Only capture REAL menus with [br][opt] pattern (each option on its own line)
    # Filter out: tables using [opt] for column spacing, dialogue pauses
    stats['orphan_menus_found'] = 0
    for region_start, region_end, chunk_idx in chunk_regions:
        pos = region_start
        while pos < region_end - 4:
            # Look for A9 00 marker
            if data[pos:pos + 2] == b'\xA9\x00':
                if pos + 2 not in found_offsets:
                    # Decode and check if it's a menu text
                    text, consumed = decode_string(data, pos + 2, decode_table, prefix=2)
                    # Real menus have [br][opt] pattern (option on new line)
                    # Skip: tables with [opt][opt] or 漢[opt]字, dialogue pauses
                    if text and '[br][opt]' in text:
                        # Validate it's a real menu (strip tags and check content)
                        stripped = text
                        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
                            stripped = stripped.replace(tag, "")
                        stripped = re.sub(r"\[script:.*?\]", "", stripped)
                        stripped = re.sub(r"\[.*?\]", "", stripped)

                        # Menu text should have meaningful content
                        if len(stripped) >= 2 and not _is_garbage_text(text):
                            # Use A9 (0x00A9) as the context opcode for orphan menus
                            dialogues.append((pos + 2, consumed, text, 0x00A9))
                            found_offsets.add(pos + 2)
                            stats['orphan_menus_found'] += 1
                            pos = pos + 2 + consumed
                            continue
            pos += 1

    # --- Scan for bare dialogues (A9 00 texts with kanji but no [opt] or template) ---
    # These are standalone dialogues in the text region that don't have templates
    # Examples: location names, battle messages, scene announcements
    # Must have kanji to filter out binary garbage
    stats['bare_dialogues_found'] = 0
    for region_start, region_end, chunk_idx in chunk_regions:
        pos = region_start
        while pos < region_end - 4:
            # Look for A9 00 marker
            if data[pos:pos + 2] == b'\xA9\x00':
                if pos + 2 not in found_offsets:
                    # Decode the text
                    text, consumed = decode_string(data, pos + 2, decode_table, prefix=2)
                    if text and consumed > 4:
                        # Strip tags to check content
                        stripped = text
                        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
                            stripped = stripped.replace(tag, "")
                        stripped = re.sub(r"\[script:.*?\]", "", stripped)
                        stripped = re.sub(r"\[.*?\]", "", stripped)

                        # Must have kanji (real Japanese text) - strict filter
                        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in stripped)

                        # Bare dialogue should have meaningful kanji content
                        if (has_kanji and len(stripped) >= 3
                                and not _is_garbage_text(text)):
                            # Use 0x00B4 as context opcode for bare dialogues in text region
                            dialogues.append((pos + 2, consumed, text, 0x00B4))
                            found_offsets.add(pos + 2)
                            stats['bare_dialogues_found'] += 1
                            pos = pos + 2 + consumed
                            continue
            pos += 1

    # --- Scan Event Script region (0xB0000-0xB4000) for dialogues ---
    # This region contains embedded dialogue text that is not covered by template scanning.
    # Includes story dialogues, item messages, and system prompts.
    # IMPORTANT: This region has more binary data, so we use stricter validation:
    # - Must have [box:] tag (dialogue structure), or
    # - Must have kanji (real Japanese text), or
    # - Must be a menu with [br][opt] pattern
    stats['event_script_dialogues_found'] = 0
    event_script_regions = _get_chunk_event_script_regions(len(data))
    for region_start, region_end, chunk_idx in event_script_regions:
        pos = region_start
        while pos < region_end - 4:
            # Look for A9 00 marker (dialogue stream marker)
            if data[pos:pos + 2] == b'\xA9\x00':
                if pos + 2 not in found_offsets:
                    # Decode the text
                    text, consumed = decode_string(data, pos + 2, decode_table, prefix=2)
                    if text:
                        # Strip tags to check content
                        stripped = text
                        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
                            stripped = stripped.replace(tag, "")
                        stripped = re.sub(r"\[script:.*?\]", "", stripped)
                        stripped = re.sub(r"\[.*?\]", "", stripped)

                        # Validation for Event Script region:
                        # Require structural indicator OR recognized text pattern.
                        # Rule 7 in garbage filter catches MIPS opcode garbage.
                        has_box_tag = '[box:' in text
                        has_kanji = any('\u4e00' <= c <= '\u9fff'
                                        for c in stripped)
                        is_menu = '[br][opt]' in text
                        has_punct = any(c in '！？…。' for c in stripped)
                        kana_count = sum(1 for c in stripped
                                         if 'ぁ' <= c <= 'ん'
                                         or 'ァ' <= c <= 'ン')
                        is_pure_kana = (has_punct and kana_count >= 2
                                        and all(
                            'ぁ' <= c <= 'ん' or 'ァ' <= c <= 'ン'
                            or c in 'ー！？…。、「」'
                            for c in stripped))
                        # Long pure hiragana = valid dialogue
                        # (e.g., なにもはいっていないようだ)
                        is_long_hiragana = (len(stripped) >= 13 and all(
                            'ぁ' <= c <= 'ん' or c == 'ー'
                            for c in stripped))

                        if (len(stripped) >= 2 and not _is_garbage_text(text)
                                and (has_box_tag or has_kanji or is_menu
                                     or is_pure_kana or is_long_hiragana)):
                            # Use 0x00B0 as context opcode for Event Script region dialogues
                            dialogues.append((pos + 2, consumed, text, 0x00B0))
                            found_offsets.add(pos + 2)
                            stats['event_script_dialogues_found'] += 1
                            pos = pos + 2 + consumed
                            continue
            pos += 1

    # --- Scan Padding region (0xA0000-0xB0000) for embedded dialogues ---
    # Some chunks (e.g., Chunk 4 in S100.STG) have dialogues in the padding region.
    # Uses the same strict validation as Event Script region.
    stats['padding_dialogues_found'] = 0
    padding_regions = _get_chunk_padding_regions(len(data))
    for region_start, region_end, chunk_idx in padding_regions:
        pos = region_start
        while pos < region_end - 4:
            # Look for A9 00 marker (dialogue stream marker)
            if data[pos:pos + 2] == b'\xA9\x00':
                if pos + 2 not in found_offsets:
                    # Decode the text
                    text, consumed = decode_string(data, pos + 2, decode_table, prefix=2)
                    if text:
                        # Strip tags to check content
                        stripped = text
                        for tag in ("[box:system]", "[box:close]", "[box:speech]",
                                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
                            stripped = stripped.replace(tag, "")
                        stripped = re.sub(r"\[script:.*?\]", "", stripped)
                        stripped = re.sub(r"\[.*?\]", "", stripped)

                        # Validation (same as Event Script region):
                        has_box_tag = '[box:' in text
                        has_kanji = any('\u4e00' <= c <= '\u9fff'
                                        for c in stripped)
                        is_menu = '[br][opt]' in text
                        has_punct = any(c in '！？…。' for c in stripped)
                        kana_count = sum(1 for c in stripped
                                         if 'ぁ' <= c <= 'ん'
                                         or 'ァ' <= c <= 'ン')
                        is_pure_kana = (has_punct and kana_count >= 2
                                        and all(
                            'ぁ' <= c <= 'ん' or 'ァ' <= c <= 'ン'
                            or c in 'ー！？…。、「」'
                            for c in stripped))
                        is_long_hiragana = (len(stripped) >= 13 and all(
                            'ぁ' <= c <= 'ん' or c == 'ー'
                            for c in stripped))

                        if (len(stripped) >= 2 and not _is_garbage_text(text)
                                and (has_box_tag or has_kanji or is_menu
                                     or is_pure_kana or is_long_hiragana)):
                            # Use 0x00A0 as context opcode for Padding region dialogues
                            dialogues.append((pos + 2, consumed, text, 0x00A0))
                            found_offsets.add(pos + 2)
                            stats['padding_dialogues_found'] += 1
                            pos = pos + 2 + consumed
                            continue
            pos += 1

    # --- Fix partial decodes ---
    # When a dialogue has [script:00 XX] prefix and decode_table[XX] != first_char,
    # the second prefix byte XX is actually a text character that was consumed as
    # part of the prefix. Fix by shifting the offset back by 1, so the null
    # terminator of the preceding dialogue becomes the first prefix byte, and the
    # original 0x00 becomes the second prefix byte.  The text then correctly
    # starts with character XX.
    stats['partial_decode_fixed'] = 0
    fixed_dialogues = []
    for offset, consumed, text, opcode in dialogues:
        m = re.match(r'\[script:00 ([0-9A-F]{2})\]', text)
        if m:
            second_byte = int(m.group(1), 16)
            text_after_script = re.sub(r'\[script:[0-9A-F ]+\]', '', text, count=1)
            # Strip box/control tags to get the first real text character
            first_text = text_after_script
            for tag in ("[box:system]", "[box:close]", "[box:speech]",
                        "[box:narration]", "[cursor]"):
                first_text = first_text.replace(tag, "")
            first_text = re.sub(r'\[.*?\]', '', first_text)
            if first_text:
                first_char = first_text[0]
                expected_char = decode_table.get(second_byte)
                # Characters that never/rarely start Japanese words.
                # When the text starts with one of these, the [script:00 XX]
                # prefix almost certainly consumed a text character (XX) as
                # the second prefix byte.
                _NON_STARTERS = set(
                    'んンっッぁぃぅぇぉゃゅょァィゥェォャュョ、。ー')
                if (first_char in _NON_STARTERS
                        and expected_char is not None
                        and expected_char != first_char
                        and offset > 0
                        and data[offset - 1] == 0x00):
                    new_offset = offset - 1
                    new_text, new_consumed = decode_string(
                        data, new_offset, decode_table, prefix=2)
                    if new_text and new_consumed > consumed:
                        fixed_dialogues.append(
                            (new_offset, new_consumed, new_text, opcode))
                        stats['partial_decode_fixed'] += 1
                        continue
        fixed_dialogues.append((offset, consumed, text, opcode))
    dialogues = fixed_dialogues

    # Sort dialogues by offset
    dialogues.sort(key=lambda d: d[0])

    # Filter garbage if requested
    if filter_garbage:
        clean_dialogues = []
        for d in dialogues:
            if not _is_garbage_text(d[2]):
                clean_dialogues.append(d)
            else:
                stats['garbage_filtered'] += 1
        dialogues = clean_dialogues

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
                            "[box:narration]", "[cursor]", "[br]", "[opt]"):
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
        # character count (6) for standalone strings to reduce false positives.
        # Exception: allow shorter strings if they match known menu words.
        min_standalone = 6
        MENU_WORDS = (
            'はい', 'いいえ', 'やめる', 'もどる', 'つぎへ', 'すすむ',
            'セーブ', 'ロード', 'カード', 'データ', 'メニュー', 'タイトル',
            'アイテム', 'ステータス', 'オプション', 'ゲーム', 'スタート',
            # Title menu options
            'はじめから', 'つづきから', 'このままつづける', 'おわる',
        )
        if (clean and scan_pos < length and data[scan_pos] == 0x00
                and valid_chars >= 2):  # At least 2 chars for menu words
            if pos not in seen_offsets:
                text, consumed = decode_string(data, pos, decode_table, prefix=prefix)
                # Check if it meets min_standalone OR is a menu word
                is_menu = any(text == w or text.startswith(w) for w in MENU_WORDS)
                if valid_chars >= min_standalone or is_menu:
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
                    "[box:narration]", "[cursor]", "[br]", "[opt]"):
            stripped = stripped.replace(tag, "")
        stripped = re.sub(r"\[.*?\]", "", stripped)

        if not stripped:
            continue

        # Allow common menu words without kanji requirement
        MENU_WORDS = (
            'はい', 'いいえ', 'やめる', 'もどる', 'つぎへ', 'すすむ',
            'セーブ', 'ロード', 'カード', 'データ', 'メニュー', 'タイトル',
            'アイテム', 'ステータス', 'オプション', 'ゲーム', 'スタート',
            # Title menu options
            'はじめから', 'つづきから', 'このままつづける', 'おわる',
        )
        is_menu_word = any(stripped == w or stripped.startswith(w) for w in MENU_WORDS)

        # Count kanji characters
        kanji_count = sum(1 for ch in stripped if '\u4e00' <= ch <= '\u9fff')
        if kanji_count < min_kanji and not is_menu_word:
            continue

        if strict and not is_menu_word:
            # In strict mode, require proper Japanese sentence structure:
            # 1. Must end with a common verb ending, particle, or punctuation
            # (Menu words are exempt from this check)

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


def scan_text_regions(data, decode_table, text_regions):
    """Scan known text data regions with minimal filtering.

    For executable files like SCPS_100.26, the main text data is stored in
    specific regions that can be identified by analysis. Inside these regions,
    we use minimal filtering (just require valid charIDs) since we know the
    data is actual game text, not MIPS code.

    Args:
        data: Binary file data
        decode_table: Character ID to character mapping
        text_regions: List of (start, end) tuples defining known text regions

    Returns:
        List of (offset, consumed, text) tuples for all valid strings.
    """
    results = []
    seen_offsets = set()

    for region_start, region_end in text_regions:
        pos = region_start

        while pos < region_end:
            # Skip null bytes
            while pos < region_end and data[pos] == 0x00:
                pos += 1
            if pos >= region_end:
                break

            # Try to decode string at this position
            text, consumed = decode_string(data, pos, decode_table)

            if text and consumed > 0:
                # Strip control codes for validation
                stripped = text
                for tag in ("[box:system]", "[box:close]", "[box:speech]",
                            "[box:narration]", "[cursor]", "[br]", "[opt]"):
                    stripped = stripped.replace(tag, "")
                stripped = re.sub(r"\[.*?\]", "", stripped)

                # Only reject if:
                # 1. Empty after stripping control codes
                # 2. Contains unknown charIDs [?XXXX]
                has_unknown = bool(re.search(r"\[\?\d+\]", text))

                if stripped and not has_unknown:
                    if pos not in seen_offsets:
                        results.append((pos, consumed, text))
                        seen_offsets.add(pos)

                pos += consumed
            else:
                pos += 1

    results.sort(key=lambda r: r[0])
    return results


def scan_executable(data, decode_table, text_regions):
    """Scan an executable file using region-aware filtering.

    For executables like SCPS_100.26, we only scan known text data regions
    where game text is stored. This avoids false positives from MIPS code
    bytes that happen to look like valid Japanese text.

    Args:
        data: Binary file data
        decode_table: Character ID to character mapping
        text_regions: List of (start, end) tuples for known text data regions

    Returns:
        List of (offset, consumed, text) tuples.
    """
    # Only scan known text regions (minimal filtering)
    # Code regions are not scanned to avoid false positives
    return scan_text_regions(data, decode_table, text_regions)


# Known text regions for SCPS_100.26 (main executable)
SCPS_TEXT_REGIONS = [
    (0x0D2690, 0x0D26F0),  # Character names - Table 1 (15 playable characters)
    (0x0D2700, 0x0D7A00),  # Main text data (system messages, items, etc.)
]

# Known text regions for BEAM.DAT (battle/event effects with embedded text)
# BEAM.DAT has character name tables duplicated across multiple effect entries
BEAM_TEXT_REGIONS = [
    (0x0216C720, 0x0216C780),  # Character names - Table 1
    (0x0216C86C, 0x0216D000),  # Monster names
    (0x0216D5D0, 0x0216D800),  # Save/load messages
    (0x0216ECC0, 0x0216ED20),  # Character names - Table 2
    (0x02170800, 0x02171000),  # Location names
]


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
    parser.add_argument("--strict", action="store_true",
                        help="Strict pointer-based extraction only (with --stg); "
                             "disables heuristic fallback scanning")
    parser.add_argument("--no-filter", action="store_true",
                        help="Disable garbage text filtering (with --stg)")
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
            display = text
            print(f"  0x{offset:08X} [{consumed:4d}] {display}")
        return

    # Mode 2b: STG template-driven extraction
    if args.stg:
        dialogues, templates, stats = scan_stg(data, decode_table,
                                               use_heuristics=not args.strict,
                                               filter_garbage=not args.no_filter)
        basename = os.path.basename(args.file)

        if not templates:
            print(f"No templates found in {basename}")
            return

        # Filter by --find if specified
        if args.find:
            dialogues = [d for d in dialogues if args.find in d[2]]

        garbage_info = ""
        if stats.get('garbage_filtered', 0) > 0:
            garbage_info = f", {stats['garbage_filtered']} garbage filtered"
        chunk_info = ""
        if stats.get('chunk_boundary_found', 0) > 0:
            chunk_info = f", {stats['chunk_boundary_found']} chunk-boundary"
        orphan_info = ""
        if stats.get('orphan_menus_found', 0) > 0:
            orphan_info = f", {stats['orphan_menus_found']} orphan menus"
        event_script_info = ""
        if stats.get('event_script_dialogues_found', 0) > 0:
            event_script_info = f", {stats['event_script_dialogues_found']} event-script"
        padding_info = ""
        if stats.get('padding_dialogues_found', 0) > 0:
            padding_info = f", {stats['padding_dialogues_found']} padding"
        print(f"Found {len(dialogues)} dialogues across "
              f"{stats['total_templates']} templates in {basename} "
              f"({stats['bare']} bare gaps, {stats['missed']} missed{chunk_info}{garbage_info}{orphan_info}{event_script_info}{padding_info})")
        print()

        prev_opcode = None
        for offset, consumed, text, context_opcode in dialogues:
            # Show context change separator
            if prev_opcode is not None and context_opcode != prev_opcode:
                print(f"  --- context: 0x{prev_opcode:04X} -> "
                      f"0x{context_opcode:04X} ---")
            prev_opcode = context_opcode

            display = text
            print(f"  0x{offset:08X} [0x{context_opcode:04X}] {display}")
        return

    # Mode 3: Find
    if args.find:
        encode_table = build_encode_table(decode_table)
        results = find_text(data, args.find, decode_table, encode_table, prefix=args.prefix)
        print(f"Found {len(results)} matches for \"{args.find}\" in {args.file}")
        print()
        for offset, consumed, text in results:
            display = text
            print(f"  0x{offset:08X} [{consumed:4d}] {display}")
        return


if __name__ == "__main__":
    main()
