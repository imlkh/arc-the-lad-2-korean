"""Regression test: SG00 orphan-menu entry やめろぉ must be translated.

Bug: A lone orphan-menu entry (opcode 0xA9) in SG00.STG contains the
untranslated Japanese exclamation やめろぉ (bytes 24 22 2B 4C), terminated
by control code FF 03 (not 0x00), so the decoder and the MISSED_BARE
patcher both miss it. It renders as "크장신디" through the Korean font.

The entry is context-anchored as:  A9 00 51 06 [24 22 2B 4C] FF 03
The fix replaces the text bytes with Korean, preserving the FF 03 suffix.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from patch_korean import load_decode_table, patch_stg_system_text  # noqa: E402

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHARMAP = os.path.join(BASE_DIR, "output", "patched", "unified_charmap.txt")

# The orphan entry as it appears in SG00.STG.
PREFIX = bytes([0xA9, 0x00, 0x51, 0x06])
JP_TEXT = bytes([0x24, 0x22, 0x2B, 0x4C])   # やめろぉ
SUFFIX = bytes([0xFF, 0x03])


def load_korean_mapping():
    """Reconstruct char -> charID from the committed unified charmap."""
    mapping = {}
    with open(CHARMAP, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                mapping[parts[0]] = int(parts[1])
    return mapping


def main():
    decode_table = load_decode_table()
    korean_mapping = load_korean_mapping()

    # Build a buffer that mimics the surrounding STG bytes.
    filler = bytes([0x26, 0x00, 0x14, 0x80])
    entry = PREFIX + JP_TEXT + SUFFIX
    blob = filler + entry + filler

    with tempfile.NamedTemporaryFile(suffix=".STG", delete=False) as tf:
        tf.write(blob)
        tmp = tf.name

    try:
        patch_stg_system_text(tmp, korean_mapping, decode_table)
        result = open(tmp, "rb").read()
    finally:
        os.unlink(tmp)

    # 1. Raw Japanese exclamation must be gone (anchored, to avoid coincidence).
    assert PREFIX + JP_TEXT + SUFFIX not in result, \
        "FAIL: raw やめろぉ orphan entry still present"

    # 2. The FF 03 suffix and A9 prefix must be preserved (length unchanged).
    assert PREFIX in result and SUFFIX in result, \
        "FAIL: prefix/suffix corrupted"
    assert len(result) == len(blob), \
        f"FAIL: length changed {len(blob)} -> {len(result)}"

    # 3. The slot occupied by the text must now be Korean (그만둬), not raw JP.
    idx = result.find(PREFIX) + len(PREFIX)
    new_text = result[idx:idx + len(JP_TEXT)]
    assert new_text != JP_TEXT, "FAIL: text bytes unchanged"
    print("PASS: orphan やめろぉ replaced ->",
          " ".join("%02X" % b for b in new_text))


if __name__ == "__main__":
    main()
