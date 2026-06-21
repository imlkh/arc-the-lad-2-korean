"""Tests for the residual-Japanese scanner.

The scanner finds displayable text frames (opcode A9 00) that are BYTE-IDENTICAL
between the original game and the patched output AND decode to real Japanese -- i.e.
lines the translation pipeline missed (like the SG00 やめろぉ orphan).

The "byte-identical to original" discriminator is what distinguishes a genuine
miss from Korean text: Korean always differs from the original; a miss does not.
"""
import os
import sys
import json

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "decode"))
sys.path.insert(0, HERE)
from scan_residual_japanese import scan_data  # noqa: E402

BASE = os.path.abspath(os.path.join(HERE, "..", ".."))
JP_TABLE = {
    x["char_id"]: x["char"]
    for x in json.load(open(os.path.join(
        BASE, "output", "font", "analysis", "jp_char_positions.json")))
}

# A9 00 orphan frame for やめろぉ:  A9 00 [ptr 51 06] [24 22 2B 4C] FF 03 00
FRAME_JP = bytes([0xA9, 0x00, 0x51, 0x06, 0x24, 0x22, 0x2B, 0x4C, 0xFF, 0x03, 0x00])
# Same frame, translated to Korean 그만둬 (2F 55 F1 9E)
FRAME_KR = bytes([0xA9, 0x00, 0x51, 0x06, 0x2F, 0x55, 0xF1, 0x9E, 0xFF, 0x03, 0x00])

CHUNK = 0x100
MIN_WITHIN = 0x80
FRAME_OFF = 0x80


def _buffer(frame):
    buf = bytearray(CHUNK)
    buf[FRAME_OFF:FRAME_OFF + len(frame)] = frame
    return bytes(buf)


def test_untranslated_frame_is_reported():
    orig = _buffer(FRAME_JP)
    patched = _buffer(FRAME_JP)  # unchanged -> a miss
    hits = scan_data(orig, patched, JP_TABLE,
                     chunk_size=CHUNK, min_within=MIN_WITHIN)
    offsets = [h["offset"] for h in hits]
    assert FRAME_OFF in offsets, f"expected miss at 0x{FRAME_OFF:X}, got {hits}"
    text = next(h["text"] for h in hits if h["offset"] == FRAME_OFF)
    assert "やめろ" in text, f"unexpected decoded text: {text!r}"


def test_translated_frame_is_not_reported():
    orig = _buffer(FRAME_JP)
    patched = _buffer(FRAME_KR)  # changed -> translated, not a miss
    hits = scan_data(orig, patched, JP_TABLE,
                     chunk_size=CHUNK, min_within=MIN_WITHIN)
    assert hits == [], f"translated frame should not be reported, got {hits}"


def _scan_one(text_bytes):
    """Scan a single A9 00 frame carrying text_bytes; return hits."""
    frame = bytes([0xA9, 0x00, 0x51, 0x06]) + text_bytes + bytes([0xFF, 0x03, 0x00])
    buf = bytearray(CHUNK)
    buf[FRAME_OFF:FRAME_OFF + len(frame)] = frame
    buf = bytes(buf)
    return scan_data(buf, buf, JP_TABLE, chunk_size=CHUNK, min_within=MIN_WITHIN)


def test_xa_mips_lead_is_rejected():
    # 22 01 2c 8c 35 = めあわデじ : 'X あ ...' MIPS opcode lead -> garbage.
    hits = _scan_one(bytes([0x22, 0x01, 0x2C, 0x8C, 0x35]))
    assert hits == [], f"Xあ MIPS lead should be rejected, got {hits}"


def test_single_katakana_soup_is_not_high():
    # 80 03 02 07 02 13 = ギういきいて : one katakana (ギ) + hiragana opcode soup.
    hits = _scan_one(bytes([0x80, 0x03, 0x02, 0x07, 0x02, 0x13]))
    assert not any(h["confidence"] == "high" for h in hits), \
        f"single-katakana soup must not be HIGH, got {hits}"


def test_real_katakana_name_is_high():
    # 90 e3 5c e3 = ブーシー : a real katakana name.
    hits = _scan_one(bytes([0x90, 0xE3, 0x5C, 0xE3]))
    assert any(h["confidence"] == "high" for h in hits), \
        f"katakana name should be HIGH, got {hits}"


if __name__ == "__main__":
    test_untranslated_frame_is_reported()
    test_translated_frame_is_not_reported()
    test_xa_mips_lead_is_rejected()
    test_single_katakana_soup_is_not_high()
    test_real_katakana_name_is_high()
    print("PASS: all residual-Japanese scanner tests")
