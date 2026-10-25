"""Regression test: "<노이즈 텍스트>" placeholder entries must never be patched.

Bug: decoder false positives (event-script bytes that look like text) are
marked "<노이즈 텍스트>" in the translation files. The patcher encoded the
placeholder and wrote it over script bytecode (S700 chunk 7 at 0xBB744 etc.),
crashing the game on entering the first Downtown house.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from patch_korean import parse_translation_file, realign_entry  # noqa: E402


def test_noise_placeholder_entries_are_skipped():
    content = (
        "# S700.STG\n"
        "  0x005E2F44 [0x800A] [script:FF FF]<노이즈 텍스트>\n"
        "  0x005E3BE2 [0x00B4] [script:F6 0A]다운타운 민가\n"
        "  0x00001234 [bare]<노이즈 텍스트>\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        entries = parse_translation_file(path)
    finally:
        os.unlink(path)
    assert [e["offset"] for e in entries] == [0x005E3BE2]
    assert entries[0]["text"] == "다운타운 민가"


def test_realign_entry_anchored_on_marker():
    # S700 chunk 7: decoder offset points at A9 00, real operand is AE 01.
    data = bytes([0, 0, 0xA9, 0x00, 0xAE, 0x01, 0xFF, 0x08, 0x01, 0x01, 0x5D, 0x00])
    off, prefix = realign_entry(data, 2, b"\xA9\x00", "[box:system]x")
    assert (off, prefix) == (4, b"\xAE\x01")


def test_realign_entry_box_code_taken_as_prefix():
    # Table string with no A9 00 marker: "prefix" FF 08 is the box code.
    data = bytes([0x01, 0x00, 0xFF, 0x08, 0x01, 0x01, 0x5D, 0x00])
    off, prefix = realign_entry(data, 2, b"\xFF\x08", "[box:system]x")
    assert (off, prefix) == (2, b"")


def test_realign_entry_leaves_normal_entries():
    data = bytes([0xA9, 0x00, 0x16, 0x07, 0x5D, 0x00])
    assert realign_entry(data, 2, b"\x16\x07", "x") == (2, b"\x16\x07")


if __name__ == "__main__":
    test_noise_placeholder_entries_are_skipped()
    test_realign_entry_anchored_on_marker()
    test_realign_entry_box_code_taken_as_prefix()
    test_realign_entry_leaves_normal_entries()
    print("OK")
